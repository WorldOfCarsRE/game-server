from pandac.PandaModules import *
from game.otp.otpbase import OTPGlobals
from direct.gui.DirectGui import *
from game.otp.otpgui import OTPDialog
from direct.directnotify import DirectNotifyGlobal
from game.otp.otpbase import OTPLocalizer
from direct.task.Task import Task


class GuiScreen:
    notify = DirectNotifyGlobal.directNotify.newCategory('GuiScreen')
    DGG.ENTERPRESS_ADVANCE = 0
    DGG.ENTERPRESS_ADVANCE_IFNOTEMPTY = 1
    DGG.ENTERPRESS_DONT_ADVANCE = 2
    DGG.ENTERPRESS_REMOVE_FOCUS = 3
    ENTRY_WIDTH = 20

    def __init__(self):
        self.waitingForDatabase = None
        self.focusIndex = None
        self.suppressClickSound = 0

    def startFocusMgmt(self,
                       startFocus=0,
                       enterPressBehavior=DGG.ENTERPRESS_ADVANCE_IFNOTEMPTY,
                       overrides={},
                       globalFocusHandler=None):
        GuiScreen.notify.debug(
            'startFocusMgmt:\nstartFocus=%s,\nenterPressBehavior=%s\noverrides=%s'
            % (startFocus, enterPressBehavior, overrides))
        self.accept('tab', self._GuiScreen__handleTab)
        self.accept('shift-tab', self._GuiScreen__handleShiftTab)
        self.accept('enter', self._GuiScreen__handleEnter)
        self._GuiScreen__startFrameStartTask()
        self.userGlobalFocusHandler = globalFocusHandler
        self.focusHandlerAbsorbCounts = {}
        for i in range(len(self.focusList)):
            item = self.focusList[i]
            if isinstance(item, DirectEntry):
                self.focusHandlerAbsorbCounts[item] = 0
                continue

        self.userFocusHandlers = {}
        self.userCommandHandlers = {}
        for i in range(len(self.focusList)):
            item = self.focusList[i]
            if isinstance(item, DirectEntry):
                self.userFocusHandlers[item] = (item['focusInCommand'],
                                                item['focusInExtraArgs'])
                item[
                    'focusInCommand'] = self._GuiScreen__handleFocusChangeAbsorb
                item['focusInExtraArgs'] = [i]
                self.userCommandHandlers[item] = (item['command'],
                                                  item['extraArgs'])
                item['command'] = None
                item['extraArgs'] = []
                continue
            if isinstance(item, DirectScrolledList):
                self.userCommandHandlers[item] = (item['command'],
                                                  item['extraArgs'])
                item[
                    'command'] = self._GuiScreen__handleDirectScrolledListCommand
                item['extraArgs'] = [i]
                continue

        self.enterPressHandlers = {}
        for i in range(len(self.focusList)):
            item = self.focusList[i]
            behavior = enterPressBehavior
            if item in overrides:
                behavior = overrides[item]

            if callable(behavior):
                self.enterPressHandlers[item] = behavior
                continue
            if not isinstance(
                    item, DirectEntry
            ) and behavior == GuiScreen_ENTERPRESS_ADVANCE_IFNOTEMPTY:
                behavior = GuiScreen_ENTERPRESS_ADVANCE

            commandHandlers = (self._GuiScreen__alwaysAdvanceFocus,
                               self._GuiScreen__advanceFocusIfNotEmpty,
                               self._GuiScreen__neverAdvanceFocus,
                               self._GuiScreen__ignoreEnterPress)
            self.enterPressHandlers[item] = commandHandlers[behavior]

        self.setFocus(startFocus)

    def focusMgmtActive(self):
        return self.focusIndex is not None

    def stopFocusMgmt(self):
        GuiScreen.notify.debug('stopFocusMgmt')
        if not self.focusMgmtActive():
            return None

        self.ignore('tab')
        self.ignore('shift-tab')
        self.ignore('enter')
        self._GuiScreen__stopFrameStartTask()
        self.userGlobalFocusHandler = None
        self.focusIndex = None
        self.focusHandlerAbsorbCounts = {}
        for item in self.focusList:
            if isinstance(item, DirectEntry):
                (userHandler, userHandlerArgs) = self.userFocusHandlers[item]
                item['focusInCommand'] = userHandler
                item['focusInExtraArgs'] = userHandlerArgs
                (userHandler, userHandlerArgs) = self.userCommandHandlers[item]
                item['command'] = userHandler
                item['extraArgs'] = userHandlerArgs
                continue
            if isinstance(item, DirectScrolledList):
                (userHandler, userHandlerArgs) = self.userCommandHandlers[item]
                item['command'] = userHandler
                item['extraArgs'] = userHandlerArgs
                continue

        self.userFocusHandlers = {}
        self.userCommandHandlers = {}
        self.enterPressHandlers = {}

    def setFocus(self, arg, suppressSound=1):
        if isinstance(arg, type(0)):
            index = arg
        else:
            index = self.focusList.index(arg)
        if suppressSound:
            self.suppressClickSound += 1

        self._GuiScreen__setFocusIndex(index)

    def advanceFocus(self, condition=1):
        index = self.getFocusIndex()
        if condition:
            index += 1

        self.setFocus(index, suppressSound=0)

    def getFocusIndex(self):
        if not self.focusMgmtActive():
            return None

        return self.focusIndex

    def getFocusItem(self):
        if not self.focusMgmtActive():
            return None

        return self.focusList[self.focusIndex]

    def removeFocus(self):
        focusItem = self.getFocusItem()
        if isinstance(focusItem, DirectEntry):
            focusItem['focus'] = 0

        if self.userGlobalFocusHandler:
            self.userGlobalFocusHandler(None)

    def restoreFocus(self):
        self.setFocus(self.getFocusItem())

    def _GuiScreen__setFocusIndex(self, index):
        focusIndex = index % len(self.focusList)
        focusItem = self.focusList[focusIndex]
        if isinstance(focusItem, DirectEntry):
            focusItem['focus'] = 1
            self.focusHandlerAbsorbCounts[focusItem] += 1

        self._GuiScreen__handleFocusChange(focusIndex)

    def _GuiScreen__chainToUserCommandHandler(self, item):
        (userHandler, userHandlerArgs) = self.userCommandHandlers[item]
        if userHandler:
            if isinstance(item, DirectEntry):
                enteredText = item.get()
                userHandler(*[enteredText] + userHandlerArgs)
            elif isinstance(item, DirectScrolledList):
                userHandler(*userHandlerArgs)

    def _GuiScreen__chainToUserFocusHandler(self, item):
        if isinstance(item, DirectEntry):
            (userHandler, userHandlerArgs) = self.userFocusHandlers[item]
            if userHandler:
                userHandler(*userHandlerArgs)

    def _GuiScreen__handleTab(self):
        self.tabPressed = 1
        self.focusDirection = 1
        self._GuiScreen__setFocusIndex(self.getFocusIndex() +
                                       self.focusDirection)

    def _GuiScreen__handleShiftTab(self):
        self.tabPressed = 1
        self.focusDirection = -1
        self._GuiScreen__setFocusIndex(self.getFocusIndex() +
                                       self.focusDirection)

    def _GuiScreen__handleFocusChangeAbsorb(self, index):
        item = self.focusList[index]
        if self.focusHandlerAbsorbCounts[item] > 0:
            self.focusHandlerAbsorbCounts[item] -= 1
        else:
            self._GuiScreen__handleFocusChange(index)

    def playFocusChangeSound(self):
        base.playSfx(DGG.getDefaultClickSound())

    def _GuiScreen__handleFocusChange(self, index):
        if index != self.focusIndex:
            self.removeFocus()

        self._GuiScreen__focusChangedThisFrame = 1
        if hasattr(self, 'tabPressed'):
            del self.tabPressed
        else:
            self.focusDirection = 1
        self.focusIndex = index
        if self.suppressClickSound > 0:
            self.suppressClickSound -= 1
        else:
            self.playFocusChangeSound()
        focusItem = self.getFocusItem()
        if self.userGlobalFocusHandler:
            self.userGlobalFocusHandler(focusItem)

        if self.getFocusItem() != focusItem:
            GuiScreen.notify.debug('focus changed by global focus handler')

        if self.focusMgmtActive():
            self._GuiScreen__chainToUserFocusHandler(focusItem)

    def _GuiScreen__startFrameStartTask(self):
        self._GuiScreen__focusChangedThisFrame = 0
        self.frameStartTaskName = 'GuiScreenFrameStart'
        taskMgr.add(self._GuiScreen__handleFrameStart, self.frameStartTaskName,
                    -100)

    def _GuiScreen__stopFrameStartTask(self):
        taskMgr.remove(self.frameStartTaskName)
        del self.frameStartTaskName
        del self._GuiScreen__focusChangedThisFrame

    def _GuiScreen__handleFrameStart(self, task):
        self._GuiScreen__focusChangedThisFrame = 0
        return Task.cont

    def _GuiScreen__handleDirectScrolledListCommand(self, index):
        self._GuiScreen__chainToUserCommandHandler(self.focusList[index])
        self.setFocus(index, suppressSound=self.getFocusIndex() == index)

    def _GuiScreen__handleEnter(self):
        if self._GuiScreen__focusChangedThisFrame:
            return None

        focusItem = self.getFocusItem()
        if isinstance(focusItem, DirectEntry):
            self._GuiScreen__chainToUserCommandHandler(focusItem)

        if self.focusMgmtActive() and focusItem == self.getFocusItem():
            self.enterPressHandlers[focusItem]()

    def _GuiScreen__alwaysAdvanceFocus(self):
        self.advanceFocus()

    def _GuiScreen__advanceFocusIfNotEmpty(self):
        focusItem = self.getFocusItem()
        enteredText = focusItem.get()
        if enteredText != '':
            self.advanceFocus()
        else:
            self.setFocus(self.getFocusIndex())

    def _GuiScreen__neverAdvanceFocus(self):
        self.setFocus(self.getFocusIndex())

    def _GuiScreen__ignoreEnterPress(self):
        pass

    def waitForDatabaseTimeout(self, requestName='unknown'):
        GuiScreen.notify.debug('waiting for database timeout %s at %s' %
                               (requestName, globalClock.getFrameTime()))
        globalClock.tick()
        taskMgr.doMethodLater(OTPGlobals.DatabaseDialogTimeout,
                              self._GuiScreen__showWaitingForDatabase,
                              'waitingForDatabase',
                              extraArgs=[requestName])

    def _GuiScreen__showWaitingForDatabase(self, requestName):
        GuiScreen.notify.info('timed out waiting for %s at %s' %
                              (requestName, globalClock.getFrameTime()))
        dialogClass = OTPGlobals.getDialogClass()
        self.waitingForDatabase = dialogClass(
            text=OTPLocalizer.GuiScreenToontownUnavailable,
            dialogName='WaitingForDatabase',
            buttonTextList=[OTPLocalizer.GuiScreenCancel],
            style=OTPDialog.Acknowledge,
            command=self._GuiScreen__handleCancelWaiting)
        self.waitingForDatabase.show()
        taskMgr.doMethodLater(OTPGlobals.DatabaseGiveupTimeout,
                              self._GuiScreen__giveUpWaitingForDatabase,
                              'waitingForDatabase',
                              extraArgs=[requestName])
        return Task.done

    def _GuiScreen__giveUpWaitingForDatabase(self, requestName):
        GuiScreen.notify.info('giving up waiting for %s at %s' %
                              (requestName, globalClock.getFrameTime()))
        self.cleanupWaitingForDatabase()
        messenger.send(self.doneEvent, [{'mode': 'failure'}])
        return Task.done

    def cleanupWaitingForDatabase(self):
        if self.waitingForDatabase is not None:
            self.waitingForDatabase.cleanup()
            self.waitingForDatabase = None

        taskMgr.remove('waitingForDatabase')

    def _GuiScreen__handleCancelWaiting(self, value):
        self.cleanupWaitingForDatabase()
        messenger.send(self.doneEvent, [{'mode': 'quit'}])
