#!/usr/bin/python2.7

import os
import re
import sys
import datetime
import multiselect
import time

from PySide2 import QtWidgets, QtCore, QtGui, QtUiTools

import af
import cgruconfig

config = cgruconfig.Config()
match = re.match(r"^(\d+)\.(\d+)\.(\d+)", config.Vars['CGRU_VERSION'])

versionOK = False
if match:
    if int(match.group(1)) >= 2:
        if int(match .group(2)) >= 3:
            versionOK = True

if versionOK is not True:
    print("Wrong version of CGRU")
    sys.exit()

cmd = af.Cmd()
startTime = time.time()


class status(object):
    '''
    dummy class for descriping status
    '''
    def __init__(self, st):
        self.st = st

    def getText(self):
        '''
        Return status text
        '''
        text = "Unknown"
        if self.st & 513 == 513:
            text = "Ready (Paused)"
        elif self.st & 1 == 1:
            text = "Ready"
        elif bool(self.st & 2):
            text = "Running"
        elif bool(self.st & 4):
            text = "Waiting on dependences"
        elif bool(self.st & 8):
            text = "Waiting on time"
        elif bool(self.st & 16):
            text = "Done"
        elif bool(self.st & 32):
            text = "Error"
        return text

    def isPaused(self):
        return bool(self.st & 512)


class backgroundUpdate(QtCore.QThread):
    jobsUpdated = QtCore.Signal(object)
    jobsDeleted = QtCore.Signal(object)
    resourcesUpdated = QtCore.Signal(object)
    rendersUpdated = QtCore.Signal(object)

    def __init__(self, interval=2):
        print(time.time() - startTime)
        QtCore.QThread.__init__(self)
        self.interval = interval
        self.monitorId = cmd.monitorRegister()
        self.stop = False
        cmd.monitorChangeUid(self.monitorId, 0)
        cmd.monitorSubscribe(self.monitorId, "jobs")
        # cmd.monitorSubscribe(self.monitorId, "renders")
        print(time.time() - startTime)

    def unregister(self):
        cmd.monitorUnregister(self.monitorId)

    def run(self):
        while self.stop is not True:
            result = cmd.monitorEvents(self.monitorId)
            events = result.get("events")
            if events is not None:
                print(events)
                if "jobs_change" in events:
                    jobsChanged = events.get("jobs_change")
                    self.jobsUpdated.emit(jobsChanged)
                if "renders_change" in events:
                    rendersChanged = events.get("renders_change")
                    self.rendersUpdated.emit(rendersChanged)
                if "jobs_del" in events:
                    jobsDeleted = events.get("jobs_del")
                    self.jobsDeleted.emit(jobsDeleted)
            resources = cmd.renderGetResources()
            self.resourcesUpdated.emit(resources)
            self.sleep(self.interval)
        self.unregister()


class afGui(QtWidgets.QMainWindow):
    projectList = []
    userList = []
    jobList = {}
    renderList = {}
    threads = []

    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        # super(QtWidgets.QMainWindow, self).__init__()

        loader = QtUiTools.QUiLoader()
        self.mainWindow = loader.load("afGui.ui")

        self.mainWindow.jobTree
        self.mainWindow.taskList
        self.mainWindow.rendersTree
        self.mainWindow.jobsToolbar
        self.mainWindow.refreshJobTreeButton

        self.mainWindow.setWindowIcon(QtGui.QIcon('afanasy.png'))
        self.mainWindow.jobTree.setItemDelegate(self.progressDelegate())

        # fd = open("darkorange.stylesheet")
        # self.mainWindow.setStyleSheet(fd.read())
        # fd.close()

        self.userFilterMenu = multiselect.Multiselect('User(s)')
        self.mainWindow.jobsToolbar.insertWidget(self.mainWindow.jobsToolbar.count() - 1, self.userFilterMenu)
        self.userFilterMenu.triggered.connect(self.selectUserFilter)

        self.projectFilterMenu = multiselect.Multiselect('Project(s)')
        self.mainWindow.jobsToolbar.insertWidget(self.mainWindow.jobsToolbar.count() - 1, self.projectFilterMenu)
        self.projectFilterMenu.triggered.connect(self.selectProjectFilter)

        self.cmd = af.Cmd()
        self.mainWindow.jobTree.clear()
        self.mainWindow.jobTree.setSortingEnabled(False)
        self.mainWindow.jobTree.resizeColumnToContents(0)
        self.updateJobList()
        self.mainWindow.jobTree.setSortingEnabled(True)
        self.mainWindow.jobTree.setColumnWidth(0, 200)
        self.mainWindow.jobTree.sortItems(0, QtCore.Qt.AscendingOrder)

        self.mainWindow.refreshJobTreeButton.clicked.connect(self.refreshButton)
        self.mainWindow.jobTree.itemSelectionChanged.connect(self.selectItem)

        self.mainWindow.jobTree.customContextMenuRequested.connect(self.openJobMenu)
        self.mainWindow.taskList.customContextMenuRequested.connect(self.openTaskMenu)

        self.mainWindow.rendersTree.clear()
        self.updateRendersList()

        self.clearJobDetails()
        self.clearBlockDetails()

        self.mainWindow.taskList.clear()

        self.mainWindow.show()

        refresher = backgroundUpdate()
        refresher.jobsUpdated.connect(self.updateJobList)
        refresher.jobsDeleted.connect(self.deleteJobs)
        refresher.rendersUpdated.connect(self.updateRendersList)
        refresher.resourcesUpdated.connect(self.updateResources)
        # refresher.setTerminationEnabled(True)
        self.threads.append(refresher)

        refresher.start()
        self.app.exec_()
        for thread in self.threads:
            print('thing')
            thread.stop = True
            thread.wait()

    def openTaskMenu(self, position):
        menu = QtWidgets.QMenu()

        skipTaskAction = menu.addAction("Skip")
        skipTaskAction.triggered.connect(self.skipTaskActionEvent)
        restartTaskAction = menu.addAction("Restart")
        restartTaskAction.triggered.connect(self.restartTaskActionEvent)

        menu.exec_(self.mainWindow.taskList.mapToGlobal(position))

    def openJobMenu(self, position):
        menu = QtWidgets.QMenu()

        # selectedJobItems = self.mainWindow.jobTree.selectedItems()

        if type(self.mainWindow.jobTree.currentItem()) == self.jobItem:
            startJobAction = menu.addAction("Start")
            startJobAction.triggered.connect(self.startJobActionEvent)
            pauseJobAction = menu.addAction("Pause")
            pauseJobAction.triggered.connect(self.pauseJobActionEvent)
            stopJobAction = menu.addAction("Stop")
            stopJobAction.triggered.connect(self.stopJobActionEvent)
            deleteJobAction = menu.addAction("Delete")
            deleteJobAction.triggered.connect(self.deleteJobActionEvent)
        if type(self.mainWindow.jobTree.currentItem()) == self.blockItem:
            skipBlockAction = menu.addAction("Skip")
            skipBlockAction.triggered.connect(self.skipBlockActionEvent)
            restartBlockAction = menu.addAction("Restart")
            restartBlockAction.triggered.connect(self.restartBlockActionEvent)

        # imagesMenu = menu.addMenu("Images")

        menu.exec_(self.mainWindow.jobTree.mapToGlobal(position))

    def startJobActionEvent(self):
        selectedJobItems = self.mainWindow.jobTree.selectedItems()
        for jobItem in selectedJobItems:
            self.cmd.setJobState(jobItem.jobId, "start")

    def pauseJobActionEvent(self):
        selectedJobItems = self.mainWindow.jobTree.selectedItems()
        for jobItem in selectedJobItems:
            self.cmd.setJobState(jobItem.jobId, "pause")

    def stopJobActionEvent(self):
        selectedJobItems = self.mainWindow.jobTree.selectedItems()
        for jobItem in selectedJobItems:
            self.cmd.setJobState(jobItem.jobId, "stop")

    def deleteJobActionEvent(self):
        selectedJobItems = self.mainWindow.jobTree.selectedItems()
        for jobItem in selectedJobItems:
            jobId = jobItem.data(0, QtCore.Qt.UserRole)
            self.cmd.deleteJobById(jobId)
            jobItem.parent().removeChild(jobItem)

    def skipBlockActionEvent(self):
        selectedBlockItems = self.mainWindow.jobTree.selectedItems()
        for blockItem in selectedBlockItems:
            blockItem.skip()

    def restartBlockActionEvent(self):
        selectedBlockItems = self.mainWindow.jobTree.selectedItems()
        for blockItem in selectedBlockItems:
            blockItem.restart()

    def skipTaskActionEvent(self):
        selectedBlock = self.mainWindow.jobTree.currentItem()
        taskIds = []
        selectedTaskItems = self.mainWindow.taskList.selectedItems()
        for taskItem in selectedTaskItems:
            taskIds.append(taskItem.data(0, QtCore.Qt.UserRole))
        selectedBlock.skip(taskIds)

    def restartTaskActionEvent(self):
        selectedBlock = self.mainWindow.jobTree.currentItem()
        taskIds = []
        selectedTaskItems = self.mainWindow.taskList.selectedItems()
        for taskItem in selectedTaskItems:
            taskIds.append(taskItem.data(0, QtCore.Qt.UserRole))
        selectedBlock.restart(taskIds)

    class progressDelegate(QtWidgets.QStyledItemDelegate):
        def __init__(self, parent=None):
            super(afGui.progressDelegate, self).__init__(parent)

        def paint(self, painter, option, index):
            if index.column() == 3:
                if index.data() is not None:
                    progress = float(index.data())
                    progressBarOption = QtWidgets.QStyleOptionProgressBar()
                    progressBarOption.rect = option.rect
                    progressBarOption.minimum = 0
                    progressBarOption.maximum = 100
                    progressBarOption.progress = progress
                    progressBarOption.text = "%d%%" % (progress)
                    progressBarOption.textVisible = True
                    QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ProgressBar, progressBarOption, painter)
            else:
                QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)

    class projectItem(QtWidgets.QTreeWidgetItem):
        def __init__(self, projectName):
            super(afGui.projectItem, self).__init__()
            self.setText(0, "%s" % (projectName))
            self.setData(0, QtCore.Qt.UserRole, projectName)
            self.setFlags(QtCore.Qt.ItemIsEnabled)

    class jobItem(QtWidgets.QTreeWidgetItem):
        def __init__(self, job):
            super(afGui.jobItem, self).__init__()
            self.projectName = job.get('project', '')
            self.jobId = job['id']
            self.parentWidget = None
            self.setText(0, "%s (%d)" % (job['name'], len(job['blocks'])))
            self.setText(1, job['user_name'])
            self.setState(job['state'].strip())
            self.setProgress(job.get('p_percentage', 0))

            dt = datetime.datetime.fromtimestamp(job['time_creation'])
            self.setText(8, dt.strftime("%Y-%m-%d %H:%M"))

            self.setTimeStarted(job.get('time_started', None))
            self.setTimeDone(job.get('time_done', None))
            self.setData(0, QtCore.Qt.UserRole, job['id'])

        def getUserName(self):
            return self.text(1)

        def setProgress(self, progress):
            self.setText(3, str(progress))

        def setState(self, state):
            self.setText(2, state)

        def setTimeDone(self, timeDone):
            if timeDone is None:
                self.setText(10, "Not Done")
            else:
                dt = datetime.datetime.fromtimestamp(timeDone)
                self.setText(10, dt.strftime("%Y-%m-%d %H:%M"))

        def setTimeStarted(self, timeStarted):
            if timeStarted is None:
                self.setText(9, "Not Started")
            else:
                dt = datetime.datetime.fromtimestamp(timeStarted)
                self.setText(9, dt.strftime("%Y-%m-%d %H:%M"))

    class blockItem(jobItem):
        def __init__(self, block, job):
            super(afGui.blockItem, self).__init__(job)
            self.setText(0, block['name'])
            self.setText(1, job['user_name'])
            self.block = block
            self.jobId = job['id']
            self.setState(block['state'].strip())
            self.setProgress(block.get('p_percentage', 0))

            self.setText(4, str(block['capacity']))
            self.setText(5, str(block['frame_first']))
            self.setText(6, str(block['frame_last']))
            self.setText(7, "%d/%d" % (block['frame_last'] - block['frame_first'] + 1, block['frames_inc']))

            self.setData(1, QtCore.Qt.UserRole, block['block_num'])
            # blockProgress = jobProgress['progress'][block['block_num']]

        def skip(self, taskIds=[]):
            cmd.setBlockState(self.jobId, self.block['block_num'], 'skip', taskIds, True)

        def restart(self, taskIds=[]):
            cmd.setBlockState(self.jobId, self.block['block_num'], 'restart', taskIds, True)

    class renderWidget(QtWidgets.QTreeWidgetItem):
        renderId = None
        totalCapacity = 0

        def __init__(self, renderId, renderName):
            super(afGui.renderWidget, self).__init__()
            self.renderId = renderId
            self.setText(0, renderName)

        def setCapacity(self, capacity):
            self.totalCapacity = capacity

        def updateState(self, state):
            self.setText(1, state)

        def updateCapacity(self, used):
            self.setText(2, "%d/%d" % (used, self.totalCapacity))

        def getId(self):
            return self.renderId

        def updateCPU(self, cpu):
            self.setText(3, "%d%%" % cpu)

        def updateMemory(self, memUsed, memTotal):
            self.setText(4, "%d/%d" % (memUsed, memTotal))

        def updateSwap(self, swapUsed, swapTotal):
            self.setText(5, "%d/%d" % (swapUsed, swapTotal))

        def updateUsers(self, users):
            self.setText(9, ",".join(users))

    def refreshButton(self):
        self.updateJobList()
        print("Refresh")

    def updateJobList(self, ids=None):
        if ids is None:
            self.jobList = {}
            self.mainWindow.jobTree.clear()
        newJobList = self.cmd.getJobList(True, ids)
        if newJobList:
            for job in newJobList:
                if job['user_name'] not in ['afadmin']:
                    if job['user_name'] not in self.userList:
                        self.userList.append(job['user_name'])
                    blocksProgress = 0
                    for block in job['blocks']:
                        blocksProgress += block.get('p_percentage', 0)
                    job['p_percentage'] = blocksProgress / len(job['blocks'])
                    jobItem = self.jobItem(job)
                    oldJob = self.jobList.get(job['id'])
                    # jobProgress = self.cmd.getJobProgress(job['id'], True)
                    for block in job['blocks']:
                        blockItem = self.blockItem(block, job)
                        jobItem.addChild(blockItem)
                    projectItem = None
                    isExpanded = False
                    isSelected = False
                    if oldJob:
                        projectItem = oldJob.parent()
                        isExpanded = oldJob.isExpanded()
                        isSelected = oldJob.isSelected()
                        if isSelected is True:
                            self.mainWindow.jobTree.selectionModel().clear()
                        projectItem.removeChild(oldJob)
                    for i in range(0, self.mainWindow.jobTree.topLevelItemCount()):
                        topItem = self.mainWindow.jobTree.topLevelItem(i)
                        if topItem.text(0) == jobItem.projectName:
                            projectItem = topItem
                            break
                    # search = self.mainWindow.jobTree.findItems("Project: %s" % (jobItem.projectName), 0, column=0)
                    # print(search)
                    # if len(search) == 1:
                    #    projectItem = search[0]
                    if projectItem is None:
                        projectItem = self.projectItem(jobItem.projectName)
                        self.mainWindow.jobTree.addTopLevelItem(projectItem)
                        projectItem.setFirstColumnSpanned(True)
                        self.projectList.append(jobItem.projectName)
                    projectItem.addChild(jobItem)
                    jobItem.setExpanded(isExpanded)
                    jobItem.setSelected(isSelected)
                    self.jobList[job['id']] = jobItem
        self.projectFilterMenu.updateChoices(self.projectList)
        self.userFilterMenu.updateChoices(self.userList)
        self.filterJobs()

    def deleteJobs(self, ids):
        for jobId in ids:
            jobItem = self.jobList.get(jobId)
            jobItem.parent().removeChild(jobItem)

    def selectItem(self):
        selectedItems = self.mainWindow.jobTree.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            jobId = selectedItem.data(0, QtCore.Qt.UserRole)
            self.mainWindow.taskList.clear()
            if type(selectedItem) == afGui.blockItem:
                ''' Block '''
                jobItem = selectedItem.parent()
                jobId = jobItem.data(0, QtCore.Qt.UserRole)
                blockNum = selectedItem.data(1, QtCore.Qt.UserRole)
                self.updateJobDetails(jobId)
                self.updateBlockDetails(jobId, blockNum)
            elif type(selectedItem) == afGui.jobItem:
                ''' Job '''
                self.updateJobDetails(jobId)
                self.clearBlockDetails()
            else:
                ''' Project '''
                self.clearBlockDetails()
                self.clearJobDetails()
        else:
            self.clearJobDetails()
            self.clearBlockDetails()

    def clearBlockDetails(self):
        self.mainWindow.blockNameValue.setText('')
        self.mainWindow.blockStatusValue.setText('')
        self.mainWindow.blockTasksValue.setText('')
        self.mainWindow.blockErrorsValue.setText('')
        self.mainWindow.blockDependMaskValue.setText('')
        self.mainWindow.blockProgressValue.setValue(0)

    def updateBlockDetails(self, jobId, blockNum):
        jobDetails = self.cmd.getJobInfo(jobId, True)[0]
        blockDetails = jobDetails['blocks'][blockNum]
        # print(blockDetails)
        ff = blockDetails['frame_first']
        fpt = blockDetails['frames_per_task']
        increment = blockDetails['frames_inc']
        jobProgress = cmd.getJobProgress(jobId, True)
        i = 0
        for item in jobProgress['progress'][blockNum]:
            taskItem = QtWidgets.QTreeWidgetItem(self.mainWindow.taskList)
            taskItem.setText(0, "Task %d" % (i + ff))
            taskItem.setText(1, item['state'])
            taskItem.setData(0, QtCore.Qt.UserRole, i)
            timeDone = item.get('tdn')
            timeStarted = item.get('tst')
            if timeDone and timeStarted:
                duration = timeDone - timeStarted
                taskItem.setText(2, str(datetime.timedelta(seconds=duration)))
            i += 1
        self.mainWindow.taskList.resizeColumnToContents(0)
        self.mainWindow.taskList.resizeColumnToContents(1)
        self.mainWindow.taskList.resizeColumnToContents(2)
        blockStatus = status(blockDetails['st'])
        self.mainWindow.blockNameValue.setText(blockDetails['name'])
        self.mainWindow.blockStatusValue.setText(blockDetails['state'])
        self.mainWindow.blockTasksValue.setText(str(blockDetails['tasks_num']))
        self.mainWindow.blockErrorsValue.setText('')
        self.mainWindow.blockDependMaskValue.setText('')
        self.mainWindow.blockProgressValue.setValue(blockDetails.get('p_percentage', 0))

    def clearJobDetails(self):
        self.mainWindow.jobNameValue.setText('')
        self.mainWindow.jobStatusValue.setText('')
        self.mainWindow.jobTasksValue.setText('')
        self.mainWindow.jobErrorsValue.setText('')
        self.mainWindow.jobDependMaskValue.setText('')
        self.mainWindow.jobMaximumRunningValue.setText('')
        self.mainWindow.jobMaximumRunningPerHostValue.setText('')

    def updateJobDetails(self, jobId):
        jobDetails = self.cmd.getJobInfo(jobId, True)[0]
        jobStatus = status(jobDetails['st'])
        # pprint.pprint(jobDetails)
        self.mainWindow.jobNameValue.setText(jobDetails['name'])
        self.mainWindow.jobStatusValue.setText(jobDetails['state'])
        tasks = 0
        for block in jobDetails['blocks']:
            tasks += block['tasks_num']
        self.mainWindow.jobTasksValue.setText("%d/%d" % (len(jobDetails['blocks']), tasks))
        self.mainWindow.jobErrorsValue.setText("%d" % (0))
        self.mainWindow.jobDependMaskValue.setText(jobDetails.get('depend_mask', ''))
        self.mainWindow.jobMaximumRunningValue.setText("%d" % jobDetails.get('max_running_tasks', -1))
        self.mainWindow.jobMaximumRunningPerHostValue.setText("%d" % jobDetails.get('max_running_tasks_per_host', -1))
        # print(jobDetails)

    def updateRendersList(self, rids=None):
        rendersList = []
        if rids is not None:
            for rid in rids:
                rendersList.extend(cmd.renderGetId(rid)['renders'])
        else:
            rendersList = cmd.renderGetList()
        if rendersList:
            for render in rendersList:
                renderItem = self.renderList.get(render['id'], self.renderWidget(render['id'], render['name']))
                if renderItem:
                    renderItem.updateState(render['state'])
                    renderItem.setCapacity(render['host']['capacity'])
                    renderItem.updateCapacity(render['capacity_used'])
                    self.renderList[render['id']] = renderItem
                    self.mainWindow.rendersTree.addTopLevelItem(renderItem)

    def updateResources(self, resources):
        for render in resources:
            # print(render)
            renderItem = self.renderList.get(render['id'])
            if renderItem:
                if 'host_resources' in render:
                    renderItem.updateCPU(render['host_resources']['cpu_user'])
                    renderItem.updateMemory(render['host_resources']['mem_total_mb'] - render['host_resources']['mem_free_mb'], render['host_resources']['mem_total_mb'])
                    renderItem.updateUsers(render['host_resources']['logged_in_users'])
                else:
                    renderItem.updateCPU(0)

    def selectProjectFilter(self, action):
        self.filterJobs()

    def selectUserFilter(self, action):
        self.filterJobs()

    def filterJobs(self):
        projects = self.projectFilterMenu.getCheckedChoices()
        users = self.userFilterMenu.getCheckedChoices()
        for i in range(0, self.mainWindow.jobTree.topLevelItemCount()):
            projectItem = self.mainWindow.jobTree.topLevelItem(i)
            projectName = projectItem.text(0)
            if projectName in projects or projects == []:
                projectItem.setHidden(False)
                for j in range(0, projectItem.childCount()):
                    jobItem = projectItem.child(j)
                    if jobItem.getUserName() in users or users == []:
                        jobItem.setHidden(False)
                    else:
                        jobItem.setHidden(True)
            else:
                projectItem.setHidden(True)


if __name__ == "__main__":
    afGui()
