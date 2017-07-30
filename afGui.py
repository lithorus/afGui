#!/usr/bin/python

import os, sys, datetime
import pprint

os.environ['QT_PREFERRED_BINDING'] = os.pathsep.join(['PySide', 'PyQt4'])

from Qt import QtWidgets, QtCore, QtGui, load_ui  # @UnresolvedImport

#cgruPath = '/opt/projects/cgru'

#os.environ['CGRU_LOCATION'] = cgruPath

#sys.path.append(os.path.join(cgruPath, 'lib', 'python'))
#sys.path.append(os.path.join(cgruPath, 'afanasy', 'python'))

import af

cmd = af.Cmd()

class status:
    """Missing DocString

    :param st:
    :return:
    """
    def __init__(self, st):
        self.st = st

    def getText(self):
        if self.st & 513 == 513:
            return "Ready (Paused)"
        elif self.st & 1 == 1:
            return "Ready"
        elif bool(self.st & 2):
            return "Running"
        elif bool(self.st & 4):
            return "Wainting dependences"
        elif bool(self.st & 8):
            return "Wainting time"
        elif bool(self.st & 16):
            return "Done"
        elif bool(self.st & 32):
            return "Error"
        return "Unknown"

    def isPaused(self):
        return bool(self.st & 512)



class backgroundUpdate(QtCore.QThread):
    jobsUpdated = QtCore.Signal(object)
    def __init__(self, interval=2):
        QtCore.QThread.__init__(self)
        self.interval = interval
        self.monitorId = cmd.monitorRegister()
        cmd.monitorSubscribe(self.monitorId, "jobs")
        cmd.monitorSubscribe(self.monitorId, "renders")

    def run(self):
        while True:
            result = cmd.monitorEvents(self.monitorId)
            events = result.get("events")
            if events is not None:
                print(events)
                jobsChanged = events.get("jobs_change")
                if jobsChanged is not None:
                    self.jobsUpdated.emit(jobsChanged)
            self.sleep(self.interval)

class afGui(QtWidgets.QMainWindow):
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        
        self.mainWindow = load_ui(fname="afGui.ui")
        self.mainWindow.setWindowIcon(QtGui.QIcon('afanasy.png'))
        self.mainWindow.jobTree.setItemDelegate(self.progressDelegate())
        
        self.cmd = af.Cmd()
        self.mainWindow.jobTree.clear()
        self.jobList = {}
        self.updateJobList()
        self.mainWindow.jobTree.setColumnWidth(0, 200)
        #self.mainWindow.jobTree.resizeColumnToContents(0)
        
        self.mainWindow.refreshJobTreeButton.clicked.connect(self.refreshButton)
        self.mainWindow.jobTree.itemSelectionChanged.connect(self.selectItem)
        
        self.mainWindow.jobTree.customContextMenuRequested.connect(self.openJobMenu)
        
        self.renderList = {}
        self.updateRendersList()
        
        self.clearJobDetails()
        self.clearBlockDetails()
        
        self.mainWindow.show()
        self.threads = []
        refresher = backgroundUpdate()
        refresher.jobsUpdated.connect(self.updateJobList)
        self.threads.append(refresher)
        refresher.start()
        
        self.app.exec_()
        
    def openJobMenu(self, position):
        menu = QtGui.QMenu()
        
        selectedJobItems = self.mainWindow.jobTree.selectedItems()
        
        startJobAction = menu.addAction("Start")
        startJobAction.triggered.connect(self.startJobActionEvent)
        pauseJobAction = menu.addAction("Pause")
        pauseJobAction.triggered.connect(self.pauseJobActionEvent)
        stopJobAction = menu.addAction("Stop")
        stopJobAction.triggered.connect(self.stopJobActionEvent)
        deleteJobAction = menu.addAction("Delete")
        deleteJobAction.triggered.connect(self.deleteJobActionEvent)
        #imagesMenu = menu.addMenu("Images")
        
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
    
    class progressDelegate(QtWidgets.QStyledItemDelegate):
        def __init__(self, parent=None):
            super(afGui.progressDelegate, self).__init__(parent)
        
        def paint(self, painter, option, index):
            if index.column() == 3:
                if index.data() != None:
                    progress = int(index.data())
                    progressBarOption = QtWidgets.QStyleOptionProgressBar()
                    progressBarOption.rect = option.rect
                    progressBarOption.minimum = 0
                    progressBarOption.maximum = 100
                    progressBarOption.progress = progress
                    progressBarOption.text = "%d%%" % (progress)
                    progressBarOption.textVisible = True
                    QtWidgets.QApplication.style().drawControl(QtGui.QStyle.CE_ProgressBar, progressBarOption, painter)
            else:
                QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)
    
    class projectItem(QtWidgets.QTreeWidgetItem):
        def __init__(self, projectName):
            super(afGui.projectItem, self).__init__()
            self.setText(0, "%s" % (projectName))
            self.setData(0, QtCore.Qt.UserRole, projectName)
    
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
        
        def setProgress(self, progress):
            self.setText(3, str(progress))
        
        def setState(self, state):
            self.setText(2, state)
        
        def setTimeDone(self, timeDone):
            if timeDone == None:
                self.setText(10, "Not Done")
            else:
                dt = datetime.datetime.fromtimestamp(timeDone)
                self.setText(10, dt.strftime("%Y-%m-%d %H:%M"))
        
        def setTimeStarted(self, timeStarted):
            if timeStarted == None:
                self.setText(9, "Not Started")
            else:
                dt = datetime.datetime.fromtimestamp(timeStarted)
                self.setText(9, dt.strftime("%Y-%m-%d %H:%M"))
    
    class blockItem(jobItem):
        def __init__(self, block, job):
            super(afGui.blockItem, self).__init__(job)
            self.setText(0, block['name'])
            self.setText(1, job['user_name'])
            
            self.setState(block['state'].strip())
            self.setProgress(block.get('p_percentage', 0))
            
            self.setText(4, str(block['capacity']))
            self.setText(5, str(block['frame_first']))
            self.setText(6, str(block['frame_last']))
            self.setText(7, "%d/%d" % (block['frame_last']-block['frame_first']+1, block['frames_inc']))
            
            self.setData(1, QtCore.Qt.UserRole, block['block_num'])
            #blockProgress = jobProgress['progress'][block['block_num']]
    
    class renderWidget(QtGui.QTreeWidgetItem):
        def __init__(self):
            super(afGui.renderWidget, self).__init__()
            pass
    
    def refreshButton(self):
        self.updateJobList()
        print("Refresh")
    
    def updateJobList(self, ids=None):
        if ids is None:
            self.jobList = {}
            self.mainWindow.jobTree.clear()
        newJobList = self.cmd.getJobList(True, ids)
        
        for job in newJobList:
            if job['user_name'] not in ['afadmin']:
                blocksProgress = 0
                for block in job['blocks']:
                    blocksProgress += block.get('p_percentage', 0)
                job['p_percentage'] = blocksProgress/len(job['blocks'])
                jobItem = self.jobItem(job)
                oldJob = self.jobList.get(job['id'])
                #jobProgress = self.cmd.getJobProgress(job['id'], True)
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
                    if isSelected == True:
                        self.mainWindow.jobTree.selectionModel().clear()
                    projectItem.removeChild(oldJob)
                search = self.mainWindow.jobTree.findItems("Project: %s" % (jobItem.projectName), 0, column=0)
                if len(search) == 1:
                    projectItem = search[0]
                else:
                    projectItem = self.projectItem(jobItem.projectName)
                    self.mainWindow.jobTree.addTopLevelItem(projectItem)
                projectItem.addChild(jobItem)
                jobItem.setExpanded(isExpanded)
                jobItem.setSelected(isSelected)
                self.jobList[job['id']] = jobItem
    
    def selectItem(self):
        selectedItems = self.mainWindow.jobTree.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            jobId = selectedItem.data(0, QtCore.Qt.UserRole)
            
            if type(selectedItem) == afGui.blockItem:
                ### Block ###
                jobItem = selectedItem.parent()
                jobId = jobItem.data(0, QtCore.Qt.UserRole)
                blockNum = selectedItem.data(1, QtCore.Qt.UserRole)
                self.updateJobDetails(jobId)
                self.updateBlockDetails(jobId, blockNum)
            elif type(selectedItem) == afGui.jobItem:
                self.updateJobDetails(jobId)
                self.clearBlockDetails()
            else:
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
        #pprint.pprint(jobDetails)
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
        #print(jobDetails)
    
    def updateRendersList(self, rid=None):
        self.mainWindow.rendersTree.clear()
        rendersList = cmd.renderGetList()
        print(cmd.renderGetId(rid))
        print(cmd.renderGetId(rid, "resources"))
        for render in rendersList:
            renderItem = self.renderList.get(render['id'], self.renderWidget())
            renderItem.setText(0, render['name'])
            renderItem.setText(1, render['state'])
            renderItem.setText(2, "%d/%d" % (render['capacity_used'], render['host']['capacity']))
            self.renderList[render['id']] = renderItem
            self.mainWindow.rendersTree.addTopLevelItem(renderItem)
        pass
    
afGui()

