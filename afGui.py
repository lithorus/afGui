#!/usr/bin/python

import os, sys, datetime
import pprint

os.environ['QT_PREFERRED_BINDING'] = os.pathsep.join(['PySide', 'PyQt4'])

from Qt import QtWidgets, QtCore, QtGui, load_ui  # @UnresolvedImport

cgruPath = '/opt/projects/cgru'

os.environ['CGRU_LOCATION'] = cgruPath

sys.path.append(os.path.join(cgruPath, 'lib', 'python'))
sys.path.append(os.path.join(cgruPath, 'afanasy', 'python'))

import af

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


class afGui(QtWidgets.QMainWindow):
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.mainWindow = load_ui(fname="afGui.ui")
        self.mainWindow.jobTree.setItemDelegate(self.progressDelegate())
        
        self.cmd = af.Cmd()
        
        self.updateJobList()
        
        self.mainWindow.refreshJobTreeButton.clicked.connect(self.updateJobList)
        self.mainWindow.jobTree.itemSelectionChanged.connect(self.selectJob)
        
        self.clearJobDetails()
        self.clearBlockDetails()
        
        self.mainWindow.show()
        self.app.exec_()
        
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
    
    class jobItem(QtWidgets.QTreeWidgetItem):
        def __init__(self, job):
            super(afGui.jobItem, self).__init__()
            self.setText(0, "%s (%d)" % (job['name'], len(job['blocks'])))
            self.setText(1, job['user_name'])
            self.setText(2, job['state'])
            
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
            
            self.setState(block['state'])
            self.setProgress(block.get('p_percentage', 0))
            
            self.setText(4, str(block['capacity']))
            self.setText(5, str(block['frame_first']))
            self.setText(6, str(block['frame_last']))
            self.setText(7, "%d/%d" % (block['frame_last']-block['frame_first']+1, block['frames_inc']))
            
            self.setData(1, QtCore.Qt.UserRole, block['block_num'])
            #blockProgress = jobProgress['progress'][block['block_num']]
    
    def updateJobList(self):
        self.mainWindow.jobTree.clear()
        jobList = self.cmd.getJobList(True)
        print("2")
        pprint.pprint(jobList)
        for job in jobList:
            if job['user_name'] != 'afadmin':
                jobItem = self.jobItem(job)
                #jobProgress = self.cmd.getJobProgress(job['id'], True)
                for block in job['blocks']:
                    blockItem = self.blockItem(block, job)
                    jobItem.addChild(blockItem)
                self.mainWindow.jobTree.addTopLevelItem(jobItem)
        
    
    def selectJob(self):
        selectedItems = self.mainWindow.jobTree.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            jobId = selectedItem.data(0, QtCore.Qt.UserRole)
            
            if type(selectedItem) == afGui.blockItem:
                ### Block ###
                jobItem = selectedItem.parent()
                jobId = jobItem.data(0, QtCore.Qt.UserRole)
                blockNum = selectedItem.data(1, QtCore.Qt.UserRole)
                self.updateJobInfo(jobId)
                self.updateBlockDetails(jobId, blockNum)
            else:
                self.updateJobInfo(jobId)
                self.clearBlockDetails()
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
        self.mainWindow.blockStatusValue.setText(blockStatus.getText())
        self.mainWindow.blockTasksValue.setText('')
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
    
    def updateJobInfo(self, jobId):
        jobDetails = self.cmd.getJobInfo(jobId, True)[0]
        jobStatus = status(jobDetails['st'])
        #pprint.pprint(jobDetails)
        self.mainWindow.jobNameValue.setText(jobDetails['name'])
        self.mainWindow.jobStatusValue.setText(jobStatus.getText())
        tasks = 0
        for block in jobDetails['blocks']:
            tasks += block['tasks_num']
        self.mainWindow.jobTasksValue.setText("%d/%d" % (len(jobDetails['blocks']), tasks))
        self.mainWindow.jobErrorsValue.setText("%d" % (0))
        self.mainWindow.jobDependMaskValue.setText(jobDetails.get('depend_mask', ''))
        self.mainWindow.jobMaximumRunningValue.setText("%d" % jobDetails.get('max_running_tasks', -1))
        self.mainWindow.jobMaximumRunningPerHostValue.setText("%d" % jobDetails.get('max_running_tasks_per_host', -1))
        #print(jobDetails)

    
afGui()
