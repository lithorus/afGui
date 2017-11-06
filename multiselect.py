'''
Created on 6 Nov 2017

@author: jimmy
'''
from PySide import QtGui
from asn1crypto.cms import CertificateChoices


class multiselect(QtGui.QToolButton):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super(multiselect, self).__init__()
        self.choiceMenu = QtGui.QMenu(self)
        self.setMenu(self.choiceMenu)
        self.setPopupMode(QtGui.QToolButton.MenuButtonPopup)

    def updateChoices(self, choices):
        '''
        Update the Choices
        @param choices: List of choices
        '''
        self.choiceMenu.clear()
        for choice in choices:
            action = self.choiceMenu.addAction(choice)
            action.setCheckable(True)

    def getCheckedChoices(self):
        '''
        Get the choices
        '''
        values = []
        for action in self.choiceMenu.actions():
            if action.isChecked():
                values.append(action.text())
        return values
