'''
Created on 6 Nov 2017

@author: jimmy
'''
from PySide2 import QtWidgets


class Multiselect(QtWidgets.QToolButton):
    '''
    classdocs
    '''

    def __init__(self, title):
        '''
        Constructor
        '''
        super(Multiselect, self).__init__()
        self.setText(title)
        self.choiceMenu = QtWidgets.QMenu(self)
        self.setMenu(self.choiceMenu)
        self.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.clicked.connect(self.showMenu)

    def updateChoices(self, choices):
        '''
        Update the Choices
        @param choices: List of choices
        '''
        oldChoices = []
        for action in self.choiceMenu.actions():
            oldChoices.append(action.text())
        # self.choiceMenu.clear()
        for choice in choices:
            if choice not in oldChoices:
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
