'''
Created on 6 Nov 2017

@author: jimmy
'''
from PySide import QtGui
from asn1crypto.cms import CertificateChoices


class Multiselect(QtGui.QToolButton):
    '''
    classdocs
    '''

    def __init__(self, title):
        '''
        Constructor
        '''
        super(Multiselect, self).__init__()
        self.setText(title)
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

    def setChoice(self, choice, checked):
        for action in self.choiceMenu.actions():
            if action.text() == choice:
                action.setChecked(checked)

    def getCheckedChoices(self):
        '''
        Get the choices
        '''
        values = []
        for action in self.choiceMenu.actions():
            if action.isChecked():
                values.append(action.text())
        return values
