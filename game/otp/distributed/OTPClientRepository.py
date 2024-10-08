import sys
import time
import string
import types
import random
import gc
import os
from pandac.PandaModules import *
from pandac.PandaModules import *
from direct.gui.DirectGui import *
from game.otp.distributed.OtpDoGlobals import *
from direct.interval.IntervalGlobal import ivalMgr
from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.ClientRepositoryBase import ClientRepositoryBase
from direct.fsm.ClassicFSM import ClassicFSM
from direct.fsm.State import State
from direct.task import Task
from direct.distributed import DistributedSmoothNode
from direct.showbase import PythonUtil, GarbageReport, BulletinBoardWatcher
from direct.showbase.ContainerLeakDetector import ContainerLeakDetector
from direct.showbase import MessengerLeakDetector
from direct.showbase.GarbageReportScheduler import GarbageReportScheduler
from direct.showbase import LeakDetectors
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from game.otp.avatar import Avatar
from game.otp.avatar.DistributedPlayer import DistributedPlayer
from game.otp.login import TTAccount
from game.otp.login import LoginTTSpecificDevAccount
from game.otp.login import AccountServerConstants
from game.otp.login.CreateAccountScreen import CreateAccountScreen
from game.otp.login import LoginScreen
from game.otp.otpgui import OTPDialog
from game.otp.avatar import DistributedAvatar
from game.otp.otpbase import OTPLocalizer
from game.otp.login import LoginGSAccount
from game.otp.login import LoginGoAccount
from game.otp.login.LoginWebPlayTokenAccount import LoginWebPlayTokenAccount
from game.otp.login.LoginDISLTokenAccount import LoginDISLTokenAccount
from game.otp.login import LoginTTAccount
from game.otp.login import HTTPUtil
from game.otp.otpbase import OTPGlobals
from game.otp.otpbase import OTPLauncherGlobals
from game.otp.uberdog import OtpAvatarManager
from game.otp.distributed import OtpDoGlobals
from game.otp.distributed.TelemetryLimiter import TelemetryLimiter
from game.otp.ai.GarbageLeakServerEventAggregator import GarbageLeakServerEventAggregator
from .PotentialAvatar import PotentialAvatar
from .DistrictHandle import *
from .OrgMsgTypes import *


class OTPClientRepository(ClientRepositoryBase):
    notify = directNotify.newCategory('OTPClientRepository')
    avatarLimit = 6
    whiteListChatEnabled = 1
    WishNameResult = Enum(
        ['Failure', 'PendingApproval', 'Approved', 'Rejected'])

    def __init__(self, serverVersion, launcher=None, playGame=None):
        ClientRepositoryBase.__init__(self)
        self.handler = None
        self.launcher = launcher
        base.launcher = launcher
        self._OTPClientRepository__currentAvId = 0
        self.productName = config.GetString('product-name', 'DisneyOnline-US')
        self.createAvatarClass = None
        self.systemMessageSfx = None
        self.userName = ''
        reg_deployment = ''
        if self.productName == 'DisneyOnline-US':
            if self.launcher:
                if self.launcher.isDummy():
                    reg_deployment = self.launcher.getDeployment()
                else:
                    reg_deployment = self.launcher.getRegistry('DEPLOYMENT')
                    if reg_deployment != 'UK' and reg_deployment != 'AP':
                        reg_deployment = self.launcher.getRegistry(
                            'GAME_DEPLOYMENT')

                    self.notify.info('reg_deployment=%s' % reg_deployment)
                if reg_deployment == 'UK':
                    self.productName = 'DisneyOnline-UK'
                elif reg_deployment == 'AP':
                    self.productName = 'DisneyOnline-AP'

        self.blue = None
        if self.launcher:
            self.blue = self.launcher.getBlue()

        fakeBlue = config.GetString('fake-blue', '')
        if fakeBlue:
            self.blue = fakeBlue

        self.playToken = None
        if self.launcher:
            self.playToken = self.launcher.getPlayToken()

        fakePlayToken = config.GetString('fake-playtoken', '')
        if fakePlayToken:
            self.playToken = fakePlayToken

        self.DISLToken = None
        if self.launcher:
            self.DISLToken = self.launcher.getDISLToken()

        fakeDISLToken = config.GetString('fake-DISLToken', '')
        fakeDISLPlayerName = config.GetString('fake-DISL-PlayerName', '')
        if fakeDISLToken:
            self.DISLToken = fakeDISLToken
        elif fakeDISLPlayerName:
            defaultId = 42
            defaultNumAvatars = 4
            defaultNumAvatarSlots = 4
            defaultNumConcur = 1
            subCount = config.GetInt('fake-DISL-NumSubscriptions', 1)
            playerAccountId = config.GetInt('fake-DISL-PlayerAccountId',
                                            defaultId)
            self.DISLToken = 'ACCOUNT_NAME=%s' % fakeDISLPlayerName + '&ACCOUNT_NUMBER=%s' % playerAccountId + '&ACCOUNT_NAME_APPROVAL=%s' % config.GetString(
                'fake-DISL-PlayerNameApproved',
                'YES') + '&SWID=%s' % config.GetString(
                    'fake-DISL-SWID', '{1763AC36-D73F-41C2-A54A-B579E58B69C8}'
                ) + '&FAMILY_NUMBER=%s' % config.GetString(
                    'fake-DISL-FamilyAccountId',
                    '-1') + '&familyAdmin=%s' % config.GetString(
                        'fake-DISL-FamilyAdmin',
                        '1') + '&PIRATES_ACCESS=%s' % config.GetString(
                            'fake-DISL-PiratesAccess', 'FULL'
                        ) + '&PIRATES_MAX_NUM_AVATARS=%s' % config.GetInt(
                            'fake-DISL-MaxAvatars', defaultNumAvatars
                        ) + '&PIRATES_NUM_AVATAR_SLOTS=%s' % config.GetInt(
                            'fake-DISL-MaxAvatarSlots', defaultNumAvatarSlots
                        ) + '&expires=%s' % config.GetString(
                            'fake-DISL-expire', '1577898000'
                        ) + '&OPEN_CHAT_ENABLED=%s' % config.GetString(
                            'fake-DISL-OpenChatEnabled', 'YES'
                        ) + '&CREATE_FRIENDS_WITH_CHAT=%s' % config.GetString(
                            'fake-DISL-CreateFriendsWithChat', 'YES'
                        ) + '&CHAT_CODE_CREATION_RULE=%s' % config.GetString(
                            'fake-DISL-ChatCodeCreation',
                            'YES') + '&FAMILY_MEMBERS=%s' % config.GetString(
                                'fake-DISL-FamilyMembers'
                            ) + '&PIRATES_SUB_COUNT=%s' % subCount
            for i in range(subCount):
                self.DISLToken += '&PIRATES_SUB_%s_ACCESS=%s' % (
                    i, config.GetString('fake-DISL-Sub-%s-Access' % i, 'FULL')
                ) + '&PIRATES_SUB_%s_ACTIVE=%s' % (
                    i, config.GetString('fake-DISL-Sub-%s-Active' % i, 'YES')
                ) + '&PIRATES_SUB_%s_ID=%s' % (
                    i,
                    config.GetInt('fake-DISL-Sub-%s-Id' % i, playerAccountId) +
                    config.GetInt('fake-DISL-Sub-Id-Offset', 0)
                ) + '&PIRATES_SUB_%s_LEVEL=%s' % (
                    i, config.GetInt('fake-DISL-Sub-%s-Level' % i, 3)
                ) + '&PIRATES_SUB_%s_NAME=%s' % (
                    i,
                    config.GetString('fake-DISL-Sub-%s-Name' % i,
                                     fakeDISLPlayerName)
                ) + '&PIRATES_SUB_%s_NUM_AVATARS=%s' % (
                    i,
                    config.GetInt('fake-DISL-Sub-%s-NumAvatars' % i,
                                  defaultNumAvatars)
                ) + '&PIRATES_SUB_%s_NUM_CONCUR=%s' % (
                    i,
                    config.GetInt('fake-DISL-Sub-%s-NumConcur' % i,
                                  defaultNumConcur)
                ) + '&PIRATES_SUB_%s_OWNERID=%s' % (
                    i,
                    config.GetInt('fake-DISL-Sub-%s-OwnerId' % i,
                                  playerAccountId)
                ) + '&PIRATES_SUB_%s_FOUNDER=%s' % (
                    i, config.GetString('fake-DISL-Sub-%s-Founder' % i, 'YES'))

            self.DISLToken += '&WL_CHAT_ENABLED=%s' % config.GetString(
                'fake-DISL-WLChatEnabled', 'YES') + '&valid=true'
            if base.logPrivateInfo:
                print(self.DISLToken)

        self.requiredLogin = config.GetString('required-login', 'auto')
        if self.requiredLogin == 'auto':
            self.notify.info('required-login auto.')
        elif self.requiredLogin == 'green':
            self.notify.error('The green code is out of date')
        elif self.requiredLogin == 'blue':
            if not (self.blue):
                self.notify.error(
                    'The tcr does not have the required blue login')

        elif self.requiredLogin == 'playToken':
            if not (self.playToken):
                self.notify.error(
                    'The tcr does not have the required playToken login')

        elif self.requiredLogin == 'DISLToken':
            if not (self.DISLToken):
                self.notify.error(
                    'The tcr does not have the required DISL token login')

        elif self.requiredLogin == 'gameServer':
            self.notify.info('Using game server name/password.')
            self.DISLToken = None
        else:
            self.notify.error('The required-login was not recognized.')
        self.computeValidateDownload()
        self.wantMagicWords = base.config.GetString('want-magic-words', '')
        if self.launcher and hasattr(self.launcher, 'http'):
            self.http = self.launcher.http
        else:
            self.http = HTTPClient()
        self.allocateDcFile()
        self.accountOldAuth = config.GetBool('account-old-auth', 0)
        self.accountOldAuth = config.GetBool('%s-account-old-auth' % game.name,
                                             self.accountOldAuth)
        self.useNewTTDevLogin = base.config.GetBool(
            'use-tt-specific-dev-login', False)
        if self.useNewTTDevLogin:
            self.loginInterface = LoginTTSpecificDevAccount.LoginTTSpecificDevAccount(
                self)
            self.notify.info('loginInterface: LoginTTSpecificDevAccount')
        elif self.accountOldAuth:
            self.loginInterface = LoginGSAccount.LoginGSAccount(self)
            self.notify.info('loginInterface: LoginGSAccount')
        elif self.blue:
            self.loginInterface = LoginGoAccount.LoginGoAccount(self)
            self.notify.info('loginInterface: LoginGoAccount')
        elif self.playToken:
            self.loginInterface = LoginWebPlayTokenAccount(self)
            self.notify.info('loginInterface: LoginWebPlayTokenAccount')
        elif self.DISLToken:
            self.loginInterface = LoginDISLTokenAccount(self)
            self.notify.info('loginInterface: LoginDISLTokenAccount')
        else:
            self.loginInterface = LoginTTAccount.LoginTTAccount(self)
            self.notify.info('loginInterface: LoginTTAccount')
        self.secretChatAllowed = base.config.GetBool('allow-secret-chat', 0)
        self.openChatAllowed = base.config.GetBool('allow-open-chat', 0)
        if base.config.GetBool('secret-chat-needs-parent-password',
                               0) and self.launcher:
            pass
        self.secretChatNeedsParentPassword = self.launcher.getNeedPwForSecretKey(
        )
        if base.config.GetBool('parent-password-set', 0) and self.launcher:
            pass
        self.parentPasswordSet = self.launcher.getParentPasswordSet()
        self.userSignature = base.config.GetString('signature', 'none')
        self.freeTimeExpiresAt = -1
        self._OTPClientRepository__isPaid = 0
        self.periodTimerExpired = 0
        self.periodTimerStarted = None
        self.periodTimerSecondsRemaining = None
        self.parentMgr.registerParent(OTPGlobals.SPRender, base.render)
        self.parentMgr.registerParent(OTPGlobals.SPHidden, NodePath())
        self.timeManager = None
        if config.GetBool('detect-leaks', 0) or config.GetBool(
                'client-detect-leaks', 0):
            self.startLeakDetector()

        if config.GetBool('detect-messenger-leaks', 0) or config.GetBool(
                'ai-detect-messenger-leaks', 0):
            self.messengerLeakDetector = MessengerLeakDetector.MessengerLeakDetector(
                'client messenger leak detector')
            if config.GetBool('leak-messages', 0):
                MessengerLeakDetector._leakMessengerObject()

        if config.GetBool('run-garbage-reports', 0) or config.GetBool(
                'client-run-garbage-reports', 0):
            noneValue = -1.0
            reportWait = config.GetFloat('garbage-report-wait', noneValue)
            reportWaitScale = config.GetFloat('garbage-report-wait-scale',
                                              noneValue)
            if reportWait == noneValue:
                reportWait = 60.0 * 2.0

            if reportWaitScale == noneValue:
                reportWaitScale = None

            self.garbageReportScheduler = GarbageReportScheduler(
                waitBetween=reportWait, waitScale=reportWaitScale)

        if not config.GetBool('proactive-leak-checks', 1):
            pass
        self._proactiveLeakChecks = config.GetBool(
            'client-proactive-leak-checks', 1)
        self._crashOnProactiveLeakDetect = config.GetBool(
            'crash-on-proactive-leak-detect', 1)
        self.activeDistrictMap = {}
        self.telemetryLimiter = TelemetryLimiter()
        self.serverVersion = serverVersion
        self.waitingForDatabase = None
        self.loginFSM = ClassicFSM('loginFSM', [
            State('loginOff', self.enterLoginOff, self.exitLoginOff,
                  ['connect']),
            State('connect', self.enterConnect, self.exitConnect,
                  ['login', 'failedToConnect', 'failedToGetServerConstants']),
            State('login', self.enterLogin, self.exitLogin, [
                'noConnection', 'waitForGameList', 'createAccount', 'reject',
                'failedToConnect', 'shutdown'
            ]),
            State('createAccount', self.enterCreateAccount,
                  self.exitCreateAccount, [
                      'noConnection', 'waitForGameList', 'login', 'reject',
                      'failedToConnect', 'shutdown'
                  ]),
            State('failedToConnect', self.enterFailedToConnect,
                  self.exitFailedToConnect, ['connect', 'shutdown']),
            State('failedToGetServerConstants',
                  self.enterFailedToGetServerConstants,
                  self.exitFailedToGetServerConstants,
                  ['connect', 'shutdown', 'noConnection']),
            State('shutdown', self.enterShutdown, self.exitShutdown,
                  ['loginOff']),
            State(
                'waitForGameList', self.enterWaitForGameList,
                self.exitWaitForGameList,
                ['noConnection', 'waitForShardList', 'missingGameRootObject']),
            State('missingGameRootObject', self.enterMissingGameRootObject,
                  self.exitMissingGameRootObject,
                  ['waitForGameList', 'shutdown']),
            State('waitForShardList', self.enterWaitForShardList,
                  self.exitWaitForShardList,
                  ['noConnection', 'waitForAvatarList', 'noShards']),
            State('noShards', self.enterNoShards, self.exitNoShards,
                  ['noConnection', 'noShardsWait', 'shutdown']),
            State('noShardsWait', self.enterNoShardsWait,
                  self.exitNoShardsWait,
                  ['noConnection', 'waitForShardList', 'shutdown']),
            State('reject', self.enterReject, self.exitReject, []),
            State('noConnection', self.enterNoConnection,
                  self.exitNoConnection, ['login', 'connect', 'shutdown']),
            State('afkTimeout', self.enterAfkTimeout, self.exitAfkTimeout,
                  ['waitForAvatarList', 'shutdown']),
            State('periodTimeout', self.enterPeriodTimeout,
                  self.exitPeriodTimeout, ['shutdown']),
            State('waitForAvatarList', self.enterWaitForAvatarList,
                  self.exitWaitForAvatarList,
                  ['noConnection', 'chooseAvatar', 'shutdown']),
            State('chooseAvatar', self.enterChooseAvatar,
                  self.exitChooseAvatar, [
                      'noConnection', 'createAvatar', 'waitForAvatarList',
                      'waitForSetAvatarResponse',
                      'waitForDeleteAvatarResponse', 'shutdown', 'login'
                  ]),
            State('createAvatar', self.enterCreateAvatar,
                  self.exitCreateAvatar, [
                      'noConnection', 'chooseAvatar',
                      'waitForSetAvatarResponse', 'shutdown'
                  ]),
            State('waitForDeleteAvatarResponse',
                  self.enterWaitForDeleteAvatarResponse,
                  self.exitWaitForDeleteAvatarResponse,
                  ['noConnection', 'chooseAvatar', 'shutdown']),
            State('rejectRemoveAvatar', self.enterRejectRemoveAvatar,
                  self.exitRejectRemoveAvatar,
                  ['noConnection', 'chooseAvatar', 'shutdown']),
            State('waitForSetAvatarResponse',
                  self.enterWaitForSetAvatarResponse,
                  self.exitWaitForSetAvatarResponse,
                  ['noConnection', 'playingGame', 'shutdown']),
            State('playingGame', self.enterPlayingGame, self.exitPlayingGame, [
                'noConnection', 'waitForAvatarList', 'login', 'shutdown',
                'afkTimeout', 'periodTimeout', 'noShards'
            ])
        ], 'loginOff', 'loginOff')
        self.gameFSM = ClassicFSM('gameFSM', [
            State('gameOff', self.enterGameOff, self.exitGameOff,
                  ['waitOnEnterResponses']),
            State('waitOnEnterResponses', self.enterWaitOnEnterResponses,
                  self.exitWaitOnEnterResponses,
                  ['playGame', 'tutorialQuestion', 'gameOff']),
            State('tutorialQuestion', self.enterTutorialQuestion,
                  self.exitTutorialQuestion, ['playGame', 'gameOff']),
            State('playGame', self.enterPlayGame, self.exitPlayGame,
                  ['gameOff', 'closeShard', 'switchShards']),
            State('switchShards', self.enterSwitchShards,
                  self.exitSwitchShards, ['gameOff', 'waitOnEnterResponses']),
            State('closeShard', self.enterCloseShard, self.exitCloseShard,
                  ['gameOff', 'waitOnEnterResponses'])
        ], 'gameOff', 'gameOff')
        self.loginFSM.getStateNamed('playingGame').addChild(self.gameFSM)
        self.loginFSM.enterInitialState()
        self.loginScreen = None
        self.music = None
        self.gameDoneEvent = 'playGameDone'
        self.playGame = playGame(self.gameFSM, self.gameDoneEvent)
        self.shardListHandle = None
        self.uberZoneInterest = None
        self.wantSwitchboard = config.GetBool('want-switchboard', 0)
        self.wantSwitchboardHacks = base.config.GetBool(
            'want-switchboard-hacks', 0)
        self.centralLogger = self.generateGlobalObject(
            OtpDoGlobals.OTP_DO_ID_CENTRAL_LOGGER, 'CentralLogger')

    def startLeakDetector(self):
        if hasattr(self, 'leakDetector'):
            return False

        firstCheckDelay = config.GetFloat('leak-detector-first-check-delay',
                                          2 * 60.0)
        self.leakDetector = ContainerLeakDetector(
            'client container leak detector', firstCheckDelay=firstCheckDelay)
        self.objectTypesLeakDetector = LeakDetectors.ObjectTypesLeakDetector()
        self.garbageLeakDetector = LeakDetectors.GarbageLeakDetector()
        self.renderLeakDetector = LeakDetectors.SceneGraphLeakDetector(render)
        self.hiddenLeakDetector = LeakDetectors.SceneGraphLeakDetector(hidden)
        self.cppMemoryUsageLeakDetector = LeakDetectors.CppMemoryUsage()
        self.taskLeakDetector = LeakDetectors.TaskLeakDetector()
        self.messageListenerTypesLeakDetector = LeakDetectors.MessageListenerTypesLeakDetector(
        )
        return True

    def getGameDoId(self):
        return self.GameGlobalsId

    def enterLoginOff(self):
        self.handler = self.handleMessageType
        self.shardListHandle = None

    enterLoginOff = report(types=['args', 'deltaStamp'],
                           dConfigParam='teleport')(enterLoginOff)

    def exitLoginOff(self):
        self.handler = None

    exitLoginOff = report(types=['args', 'deltaStamp'],
                          dConfigParam='teleport')(exitLoginOff)

    def computeValidateDownload(self):
        if self.launcher:
            hash = HashVal()
            hash.mergeWith(launcher.launcherFileDbHash)
            hash.mergeWith(launcher.serverDbFileHash)
            self.validateDownload = hash.asHex()
        else:
            self.validateDownload = ''
            if not os.path.expandvars('$TOONTOWN'):
                pass
            basePath = './toontown'
            downloadParFilename = Filename.expandFrom(
                basePath + '/src/configfiles/download.par')
            if downloadParFilename.exists():
                downloadPar = open(downloadParFilename.toOsSpecific())
                for line in downloadPar.readlines():
                    i = string.find(line, 'VALIDATE_DOWNLOAD=')
                    if i != -1:
                        self.validateDownload = string.strip(line[i + 18:])
                        break
                        continue

    def getServerVersion(self):
        return self.serverVersion

    def enterConnect(self, serverList):
        self.serverList = serverList
        dialogClass = OTPGlobals.getGlobalDialogClass()
        self.connectingBox = dialogClass(message=OTPLocalizer.CRConnecting)
        self.connectingBox.show()
        self.renderFrame()
        self.handler = self.handleMessageType
        self.connect(self.serverList,
                     successCallback=self._handleConnected,
                     failureCallback=self.failedToConnect)

    enterConnect = report(types=['args', 'deltaStamp'],
                          dConfigParam='teleport')(enterConnect)

    def failedToConnect(self, statusCode, statusString):
        self.loginFSM.request('failedToConnect', [statusCode, statusString])

    failedToConnect = report(types=['args', 'deltaStamp'],
                             dConfigParam='teleport')(failedToConnect)

    def exitConnect(self):
        self.connectingBox.cleanup()
        del self.connectingBox

    exitConnect = report(types=['args', 'deltaStamp'],
                         dConfigParam='teleport')(exitConnect)

    def handleSystemMessage(self, di):
        message = ClientRepositoryBase.handleSystemMessage(self, di)
        whisper = WhisperPopup(message, OTPGlobals.getInterfaceFont(),
                               WhisperPopup.WTSystem)
        whisper.manage(base.marginManager)
        if not self.systemMessageSfx:
            self.systemMessageSfx = base.loadSfx(
                'phase_3/audio/sfx/clock03.mp3')

        if self.systemMessageSfx:
            base.playSfx(self.systemMessageSfx)

    def getConnectedEvent(self):
        return 'OTPClientRepository-connected'

    def _handleConnected(self):
        self.launcher.setDisconnectDetailsNormal()
        messenger.send(self.getConnectedEvent())
        self.gotoFirstScreen()

    _handleConnected = report(types=['args', 'deltaStamp'],
                              dConfigParam='teleport')(_handleConnected)

    def gotoFirstScreen(self):
        """ # kept for study
        try:
            self.accountServerConstants = AccountServerConstants.AccountServerConstants(
                self)
        except TTAccount.TTAccountException:
            e = None
            self.notify.debug(str(e))
            self.loginFSM.request('failedToGetServerConstants', [e])
            return None
        """

        self.startReaderPollTask()
        self.startHeartbeat()
        newInstall = launcher.getIsNewInstallation()
        newInstall = base.config.GetBool('new-installation', newInstall)
        if newInstall:
            self.notify.warning('new installation')

        self.loginFSM.request('login')

    def enterLogin(self):
        self.sendSetAvatarIdMsg(0)
        """
        self.loginScreen = LoginScreen.LoginScreen(self, self.loginDoneEvent)
        self.accept(self.loginDoneEvent,
                    self._OTPClientRepository__handleLoginDone)
        self.loginScreen.load()
        self.loginScreen.enter()
        """
        #! Temporary login
        datagram = PyDatagram()
        datagram.addUint16(16)
        datagram.addString(sys.argv[1])  # Play token
        datagram.addString(self.serverVersion)
        datagram.addUint32(0)  #! Temporary hash val
        datagram.addInt32(3)
        self.send(datagram)

    enterLogin = report(types=['args', 'deltaStamp'],
                        dConfigParam='teleport')(enterLogin)

    def __handleLoginDone(self, doneStatus):
        mode = doneStatus['mode']
        if mode == 'success':
            self.setIsNotNewInstallation()
            self.loginFSM.request('waitForGameList')
        elif mode == 'getChatPassword':
            self.loginFSM.request('parentPassword')
        elif mode == 'freeTimeExpired':
            self.loginFSM.request('freeTimeInform')
        elif mode == 'createAccount':
            self.loginFSM.request('createAccount', [{
                'back': 'login',
                'backArgs': []
            }])
        elif mode == 'reject':
            self.loginFSM.request('reject')
        elif mode == 'quit':
            self.loginFSM.request('shutdown')
        elif mode == 'failure':
            self.loginFSM.request('failedToConnect', [-1, '?'])
        else:
            self.notify.error('Invalid doneStatus mode from loginScreen: ' +
                              str(mode))

    _OTPClientRepository__handleLoginDone = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(__handleLoginDone)

    def exitLogin(self):
        if self.loginScreen:
            self.loginScreen.exit()
            self.loginScreen.unload()
            self.loginScreen = None
            self.renderFrame()

        #self.ignore(self.loginDoneEvent)
        #del self.loginDoneEvent
        self.handler = None

    exitLogin = report(types=['args', 'deltaStamp'],
                       dConfigParam='teleport')(exitLogin)

    def enterCreateAccount(self,
                           createAccountDoneData={
                               'back': 'login',
                               'backArgs': []
                           }):
        self.createAccountDoneData = createAccountDoneData
        self.createAccountDoneEvent = 'createAccountDone'
        self.createAccountScreen = None
        self.createAccountScreen = CreateAccountScreen(
            self, self.createAccountDoneEvent)
        self.accept(self.createAccountDoneEvent,
                    self._OTPClientRepository__handleCreateAccountDone)
        self.createAccountScreen.load()
        self.createAccountScreen.enter()

    enterCreateAccount = report(types=['args', 'deltaStamp'],
                                dConfigParam='teleport')(enterCreateAccount)

    def __handleCreateAccountDone(self, doneStatus):
        mode = doneStatus['mode']
        if mode == 'success':
            self.setIsNotNewInstallation()
            #self.loginFSM.request('waitForGameList')
            self.loginFSM.request('waitForShardList')
        elif mode == 'reject':
            self.loginFSM.request('reject')
        elif mode == 'cancel':
            self.loginFSM.request(self.createAccountDoneData['back'],
                                  self.createAccountDoneData['backArgs'])
        elif mode == 'failure':
            self.loginFSM.request(self.createAccountDoneData['back'],
                                  self.createAccountDoneData['backArgs'])
        elif mode == 'quit':
            self.loginFSM.request('shutdown')
        else:
            self.notify.error(
                'Invalid doneStatus mode from CreateAccountScreen: ' +
                str(mode))

    _OTPClientRepository__handleCreateAccountDone = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(__handleCreateAccountDone)

    def exitCreateAccount(self):
        if self.createAccountScreen:
            self.createAccountScreen.exit()
            self.createAccountScreen.unload()
            self.createAccountScreen = None
            self.renderFrame()

        self.ignore(self.createAccountDoneEvent)
        del self.createAccountDoneEvent
        self.handler = None

    exitCreateAccount = report(types=['args', 'deltaStamp'],
                               dConfigParam='teleport')(exitCreateAccount)

    def enterFailedToConnect(self, statusCode, statusString):
        self.handler = self.handleMessageType
        messenger.send('connectionIssue')
        url = self.serverList[0]
        self.notify.warning(
            'Failed to connect to %s (%s %s).  Notifying user.' %
            (url.cStr(), statusCode, statusString))
        if statusCode == 1403 and statusCode == 1405 or statusCode == 1400:
            message = OTPLocalizer.CRNoConnectProxyNoPort % (
                url.getServer(), url.getPort(), url.getPort())
            style = OTPDialog.CancelOnly
        else:
            message = OTPLocalizer.CRNoConnectTryAgain % (url.getServer(),
                                                          url.getPort())
            style = OTPDialog.TwoChoice
        dialogClass = OTPGlobals.getGlobalDialogClass()
        self.failedToConnectBox = dialogClass(message=message,
                                              doneEvent='failedToConnectAck',
                                              text_wordwrap=18,
                                              style=style)
        self.failedToConnectBox.show()
        self.notify.info(message)
        self.accept('failedToConnectAck',
                    self._OTPClientRepository__handleFailedToConnectAck)

    enterFailedToConnect = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(enterFailedToConnect)

    def __handleFailedToConnectAck(self):
        doneStatus = self.failedToConnectBox.doneStatus
        if doneStatus == 'ok':
            self.loginFSM.request('connect', [self.serverList])
            messenger.send('connectionRetrying')
        elif doneStatus == 'cancel':
            self.loginFSM.request('shutdown')
        else:
            self.notify.error('Unrecognized doneStatus: ' + str(doneStatus))

    _OTPClientRepository__handleFailedToConnectAck = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(__handleFailedToConnectAck)

    def exitFailedToConnect(self):
        self.handler = None
        self.ignore('failedToConnectAck')
        self.failedToConnectBox.cleanup()
        del self.failedToConnectBox

    exitFailedToConnect = report(types=['args', 'deltaStamp'],
                                 dConfigParam='teleport')(exitFailedToConnect)

    def enterFailedToGetServerConstants(self, e):
        self.handler = self.handleMessageType
        messenger.send('connectionIssue')
        url = AccountServerConstants.AccountServerConstants.getServerURL()
        statusCode = 0
        if isinstance(e, HTTPUtil.ConnectionError):
            statusCode = e.statusCode
            self.notify.warning('Got status code %s from connection to %s.' %
                                (statusCode, url.cStr()))
        else:
            self.notify.warning(
                "Didn't get status code from connection to %s." % url.cStr())
        if statusCode == 1403 or statusCode == 1400:
            message = OTPLocalizer.CRServerConstantsProxyNoPort % (
                url.cStr(), url.getPort())
            style = OTPDialog.CancelOnly
        elif statusCode == 1405:
            message = OTPLocalizer.CRServerConstantsProxyNoCONNECT % url.cStr()
            style = OTPDialog.CancelOnly
        else:
            message = OTPLocalizer.CRServerConstantsTryAgain % url.cStr()
            style = OTPDialog.TwoChoice
        dialogClass = OTPGlobals.getGlobalDialogClass()
        self.failedToGetConstantsBox = dialogClass(
            message=message,
            doneEvent='failedToGetConstantsAck',
            text_wordwrap=18,
            style=style)
        self.failedToGetConstantsBox.show()
        self.accept('failedToGetConstantsAck',
                    self._OTPClientRepository__handleFailedToGetConstantsAck)
        self.notify.warning(
            'Failed to get account server constants. Notifying user.')

    enterFailedToGetServerConstants = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(enterFailedToGetServerConstants)

    def __handleFailedToGetConstantsAck(self):
        doneStatus = self.failedToGetConstantsBox.doneStatus
        if doneStatus == 'ok':
            self.loginFSM.request('connect', [self.serverList])
            messenger.send('connectionRetrying')
        elif doneStatus == 'cancel':
            self.loginFSM.request('shutdown')
        else:
            self.notify.error('Unrecognized doneStatus: ' + str(doneStatus))

    _OTPClientRepository__handleFailedToGetConstantsAck = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(__handleFailedToGetConstantsAck)

    def exitFailedToGetServerConstants(self):
        self.handler = None
        self.ignore('failedToGetConstantsAck')
        self.failedToGetConstantsBox.cleanup()
        del self.failedToGetConstantsBox

    exitFailedToGetServerConstants = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(exitFailedToGetServerConstants)

    def enterShutdown(self, errorCode=None):
        self.handler = self.handleMessageType
        self.sendDisconnect()
        self.notify.info('Exiting cleanly')
        base.exitShow(errorCode)

    enterShutdown = report(types=['args', 'deltaStamp'],
                           dConfigParam='teleport')(enterShutdown)

    def exitShutdown(self):
        if hasattr(self, 'garbageWatcher'):
            self.garbageWatcher.destroy()
            del self.garbageWatcher

        self.handler = None

    exitShutdown = report(types=['args', 'deltaStamp'],
                          dConfigParam='teleport')(exitShutdown)

    def enterWaitForGameList(self):
        self.loginFSM.request('waitForShardList')
        """
        self.gameDoDirectory = self.addTaggedInterest(
            self.GameGlobalsId,
            OTP_ZONE_ID_MANAGEMENT,
            self.ITAG_PERM,
            'game directory',
            event='GameList_Complete')
        self.acceptOnce('GameList_Complete', self.waitForGetGameListResponse)
        """

    enterWaitForGameList = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(enterWaitForGameList)

    def waitForGetGameListResponse(self):
        if self.isGameListCorrect():
            if base.config.GetBool('game-server-tests', 0):
                GameServerTestSuite = GameServerTestSuite
                import otp.distributed
                GameServerTestSuite.GameServerTestSuite(self)

            self.loginFSM.request('waitForShardList')
        else:
            self.loginFSM.request('missingGameRootObject')

    waitForGetGameListResponse = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(waitForGetGameListResponse)

    def isGameListCorrect(self):
        return 1

    isGameListCorrect = report(types=['args', 'deltaStamp'],
                               dConfigParam='teleport')(isGameListCorrect)

    def exitWaitForGameList(self):
        self.handler = None

    exitWaitForGameList = report(types=['args', 'deltaStamp'],
                                 dConfigParam='teleport')(exitWaitForGameList)

    def enterMissingGameRootObject(self):
        self.notify.warning('missing some game root objects.')
        self.handler = self.handleMessageType
        dialogClass = OTPGlobals.getGlobalDialogClass()
        self.missingGameRootObjectBox = dialogClass(
            message=OTPLocalizer.CRMissingGameRootObject,
            doneEvent='missingGameRootObjectBoxAck',
            style=OTPDialog.TwoChoice)
        self.missingGameRootObjectBox.show()
        self.accept('missingGameRootObjectBoxAck',
                    self._OTPClientRepository__handleMissingGameRootObjectAck)

    enterMissingGameRootObject = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(enterMissingGameRootObject)

    def __handleMissingGameRootObjectAck(self):
        doneStatus = self.missingGameRootObjectBox.doneStatus
        if doneStatus == 'ok':
            self.loginFSM.request('waitForGameList')
        elif doneStatus == 'cancel':
            self.loginFSM.request('shutdown')
        else:
            self.notify.error('Unrecognized doneStatus: ' + str(doneStatus))

    _OTPClientRepository__handleMissingGameRootObjectAck = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(__handleMissingGameRootObjectAck)

    def exitMissingGameRootObject(self):
        self.handler = None
        self.ignore('missingGameRootObjectBoxAck')
        self.missingGameRootObjectBox.cleanup()
        del self.missingGameRootObjectBox

    exitMissingGameRootObject = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(exitMissingGameRootObject)

    def enterWaitForShardList(self):
        #self.noInterestShardList()
        #return
        if not self.isValidInterestHandle(self.shardListHandle):
            self.shardListHandle = self.addTaggedInterest(
                self.GameGlobalsId,
                OTP_ZONE_ID_DISTRICTS,
                self.ITAG_PERM,
                'LocalShardList',
                event='ShardList_Complete')
            self.acceptOnce('ShardList_Complete', self._wantShardListComplete)
        else:
            self._wantShardListComplete()

    enterWaitForShardList = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(enterWaitForShardList)

    def noInterestShardList(self):
        datagram = PyDatagram()
        datagram.addUint16(8)
        self.send(datagram)

    def __handleShardList(self, di):
        numDistricts = di.getUint16()
        for i in range(numDistricts):
            channel = di.getUint32()
            name = di.getString()
            pop = di.getUint32()
            self.activeDistrictMap[channel] = DistrictHandle(
                channel, name, pop)

        if self.loginFSM.getCurrentState().getName() == "waitForShardList":
            self.wuantShardListComplete()

    def wuantShardListComplete(self):
        if self._shardsAreReady():
            self.loginFSM.request('waitForAvatarList')
        else:
            self.loginFSM.request('noShards')

    def _wantShardListComplete(self):
        if self._shardsAreReady():
            self.loginFSM.request('waitForAvatarList')
        else:
            self.loginFSM.request('noShards')

    _wantShardListComplete = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(_wantShardListComplete)

    def _shardsAreReady(self):
        for shard in list(self.activeDistrictMap.values()):
            if shard.available:
                return True
                continue
        else:
            return False

    _shardsAreReady = report(types=['args', 'deltaStamp'],
                             dConfigParam='teleport')(_shardsAreReady)

    def exitWaitForShardList(self):
        self.ignore('ShardList_Complete')
        self.handler = None

    exitWaitForShardList = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(exitWaitForShardList)

    def enterNoShards(self):
        messenger.send('connectionIssue')
        self.handler = self.handleMessageType
        dialogClass = OTPGlobals.getGlobalDialogClass()
        self.noShardsBox = dialogClass(
            message=OTPLocalizer.CRNoDistrictsTryAgain,
            doneEvent='noShardsAck',
            style=OTPDialog.TwoChoice)
        self.noShardsBox.show()
        self.accept('noShardsAck',
                    self._OTPClientRepository__handleNoShardsAck)

    enterNoShards = report(types=['args', 'deltaStamp'],
                           dConfigParam='teleport')(enterNoShards)

    def __handleNoShardsAck(self):
        doneStatus = self.noShardsBox.doneStatus
        if doneStatus == 'ok':
            messenger.send('connectionRetrying')
            self.loginFSM.request('noShardsWait')
        elif doneStatus == 'cancel':
            self.loginFSM.request('shutdown')
        else:
            self.notify.error('Unrecognized doneStatus: ' + str(doneStatus))

    _OTPClientRepository__handleNoShardsAck = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(__handleNoShardsAck)

    def exitNoShards(self):
        self.handler = None
        self.ignore('noShardsAck')
        self.noShardsBox.cleanup()
        del self.noShardsBox

    exitNoShards = report(types=['args', 'deltaStamp'],
                          dConfigParam='teleport')(exitNoShards)

    def enterNoShardsWait(self):
        dialogClass = OTPGlobals.getGlobalDialogClass()
        self.connectingBox = dialogClass(message=OTPLocalizer.CRConnecting)
        self.connectingBox.show()
        self.renderFrame()
        self.noShardsWaitTaskName = 'noShardsWait'

        def doneWait(task, self=self):
            self.loginFSM.request('waitForShardList')

        if __dev__:
            delay = 0.0
        else:
            delay = 6.5 + random.random() * 2.0
        taskMgr.doMethodLater(delay, doneWait, self.noShardsWaitTaskName)

    enterNoShardsWait = report(types=['args', 'deltaStamp'],
                               dConfigParam='teleport')(enterNoShardsWait)

    def exitNoShardsWait(self):
        taskMgr.remove(self.noShardsWaitTaskName)
        del self.noShardsWaitTaskName
        self.connectingBox.cleanup()
        del self.connectingBox

    exitNoShardsWait = report(types=['args', 'deltaStamp'],
                              dConfigParam='teleport')(exitNoShardsWait)

    def enterReject(self):
        self.handler = self.handleMessageType
        self.notify.warning('Connection Rejected')
        launcher.setPandaErrorCode(13)
        sys.exit()

    enterReject = report(types=['args', 'deltaStamp'],
                         dConfigParam='teleport')(enterReject)

    def exitReject(self):
        self.handler = None

    exitReject = report(types=['args', 'deltaStamp'],
                        dConfigParam='teleport')(exitReject)

    def enterNoConnection(self):
        messenger.send('connectionIssue')
        self.resetInterestStateForConnectionLoss()
        self.shardListHandle = None
        self.handler = self.handleMessageType
        self._OTPClientRepository__currentAvId = 0
        self.stopHeartbeat()
        self.stopReaderPollTask()
        gameUsername = launcher.getValue('GAME_USERNAME', base.cr.userName)
        if self.bootedIndex is not None and self.bootedIndex in OTPLocalizer.CRBootedReasons:
            message = OTPLocalizer.CRBootedReasons[self.bootedIndex] % {
                'name': gameUsername
            }
        elif self.bootedText is not None:
            message = OTPLocalizer.CRBootedReasonUnknownCode % self.bootedIndex
        else:
            message = OTPLocalizer.CRLostConnection
        reconnect = 1
        if self.bootedIndex in (152, 127):
            reconnect = 0

        self.launcher.setDisconnectDetails(self.bootedIndex, message)
        style = OTPDialog.Acknowledge
        if reconnect and self.loginInterface.supportsRelogin():
            message += OTPLocalizer.CRTryConnectAgain
            style = OTPDialog.TwoChoice

        dialogClass = OTPGlobals.getGlobalDialogClass()
        self.lostConnectionBox = dialogClass(doneEvent='lostConnectionAck',
                                             message=message,
                                             text_wordwrap=18,
                                             style=style)
        self.lostConnectionBox.show()
        self.accept('lostConnectionAck',
                    self._OTPClientRepository__handleLostConnectionAck)
        self.notify.warning('Lost connection to server. Notifying user.')

    enterNoConnection = report(types=['args', 'deltaStamp'],
                               dConfigParam='teleport')(enterNoConnection)

    def __handleLostConnectionAck(self):
        if self.lostConnectionBox.doneStatus == 'ok' and self.loginInterface.supportsRelogin(
        ):
            self.loginFSM.request('connect', [self.serverList])
        else:
            self.loginFSM.request('shutdown')

    _OTPClientRepository__handleLostConnectionAck = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(__handleLostConnectionAck)

    def exitNoConnection(self):
        self.handler = None
        self.ignore('lostConnectionAck')
        self.lostConnectionBox.cleanup()
        messenger.send('connectionRetrying')

    exitNoConnection = report(types=['args', 'deltaStamp'],
                              dConfigParam='teleport')(exitNoConnection)

    def enterAfkTimeout(self):
        self.sendSetAvatarIdMsg(0)
        msg = OTPLocalizer.AfkForceAcknowledgeMessage
        dialogClass = OTPGlobals.getDialogClass()
        self.afkDialog = dialogClass(
            text=msg,
            command=self._OTPClientRepository__handleAfkOk,
            style=OTPDialog.Acknowledge)
        self.handler = self.handleMessageType

    enterAfkTimeout = report(types=['args', 'deltaStamp'],
                             dConfigParam='teleport')(enterAfkTimeout)

    def __handleAfkOk(self, value):
        self.loginFSM.request('waitForAvatarList')

    _OTPClientRepository__handleAfkOk = report(
        types=['args', 'deltaStamp'], dConfigParam='teleport')(__handleAfkOk)

    def exitAfkTimeout(self):
        if self.afkDialog:
            self.afkDialog.cleanup()
            self.afkDialog = None

        self.handler = None

    exitAfkTimeout = report(types=['args', 'deltaStamp'],
                            dConfigParam='teleport')(exitAfkTimeout)

    def enterPeriodTimeout(self):
        self.sendSetAvatarIdMsg(0)
        self.sendDisconnect()
        msg = OTPLocalizer.PeriodForceAcknowledgeMessage
        dialogClass = OTPGlobals.getDialogClass()
        self.periodDialog = dialogClass(
            text=msg,
            command=self._OTPClientRepository__handlePeriodOk,
            style=OTPDialog.Acknowledge)
        self.handler = self.handleMessageType

    enterPeriodTimeout = report(types=['args', 'deltaStamp'],
                                dConfigParam='teleport')(enterPeriodTimeout)

    def __handlePeriodOk(self, value):
        base.exitShow()

    _OTPClientRepository__handlePeriodOk = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(__handlePeriodOk)

    def exitPeriodTimeout(self):
        if self.periodDialog:
            self.periodDialog.cleanup()
            self.periodDialog = None

        self.handler = None

    exitPeriodTimeout = report(types=['args', 'deltaStamp'],
                               dConfigParam='teleport')(exitPeriodTimeout)

    def enterWaitForAvatarList(self):
        self.handler = self.handleWaitForAvatarList
        self._requestAvatarList()

    enterWaitForAvatarList = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(enterWaitForAvatarList)

    def _requestAvatarList(self):
        self.sendGetAvatarsMsg()
        self.waitForDatabaseTimeout(requestName='WaitForAvatarList')
        self.acceptOnce(OtpAvatarManager.OtpAvatarManager.OnlineEvent,
                        self._requestAvatarList)

    _requestAvatarList = report(types=['args', 'deltaStamp'],
                                dConfigParam='teleport')(_requestAvatarList)

    def sendGetAvatarsMsg(self):
        datagram = PyDatagram()
        datagram.addUint16(CLIENT_GET_AVATARS)
        self.send(datagram)

    sendGetAvatarsMsg = report(types=['args', 'deltaStamp'],
                               dConfigParam='teleport')(sendGetAvatarsMsg)

    def exitWaitForAvatarList(self):
        self.cleanupWaitingForDatabase()
        self.ignore(OtpAvatarManager.OtpAvatarManager.OnlineEvent)
        self.handler = None

    exitWaitForAvatarList = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(exitWaitForAvatarList)

    def handleWaitForAvatarList(self, msgType, di):
        if msgType == CLIENT_GET_AVATARS_RESP:
            self.handleGetAvatarsRespMsg(di)
        elif msgType == CLIENT_GET_AVATARS_RESP2:
            pass
        else:
            self.handleMessageType(msgType, di)

    handleWaitForAvatarList = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(handleWaitForAvatarList)

    def handleGetAvatarsRespMsg(self, di):
        returnCode = di.getUint8()
        if returnCode == 0:
            avatarTotal = di.getUint16()
            avList = []
            for i in range(0, avatarTotal):
                avNum = di.getUint32()
                avNames = ['', '', '', '']
                avNames[0] = di.getString()
                avNames[1] = di.getString()
                avNames[2] = di.getString()
                avNames[3] = di.getString()
                avDNA = di.getString()
                avPosition = di.getUint8()
                aname = di.getUint8()
                potAv = PotentialAvatar(avNum, avNames, avDNA, avPosition,
                                        aname)
                avList.append(potAv)

            self.avList = avList
            self.loginFSM.request('chooseAvatar', [self.avList])
        else:
            self.notify.error('Bad avatar list return code: ' +
                              str(returnCode))
            self.loginFSM.request('shutdown')

    handleGetAvatarsRespMsg = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(handleGetAvatarsRespMsg)

    def handleGetAvatarsResp2Msg(self, di):
        returnCode = di.getUint8()
        if returnCode == 0:
            avatarTotal = di.getUint16()
            avList = []
            for i in range(0, avatarTotal):
                avNum = di.getUint32()
                avNames = ['', '', '', '']
                avNames[0] = di.getString()
                avDNA = None
                avPosition = di.getUint8()
                aname = None
                potAv = PotentialAvatar(avNum, avNames, avDNA, avPosition,
                                        aname)
                avList.append(potAv)

            self.avList = avList
            self.loginFSM.request('chooseAvatar', [self.avList])
        else:
            self.notify.error('Bad avatar list return code: ' +
                              str(returnCode))
            self.loginFSM.request('shutdown')

    handleGetAvatarsResp2Msg = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(handleGetAvatarsResp2Msg)

    def enterChooseAvatar(self, avList):
        pass

    enterChooseAvatar = report(types=['args', 'deltaStamp'],
                               dConfigParam='teleport')(enterChooseAvatar)

    def exitChooseAvatar(self):
        pass

    exitChooseAvatar = report(types=['args', 'deltaStamp'],
                              dConfigParam='teleport')(exitChooseAvatar)

    def enterCreateAvatar(self, avList, index, newDNA=None):
        pass

    enterCreateAvatar = report(types=['args', 'deltaStamp'],
                               dConfigParam='teleport')(enterCreateAvatar)

    def exitCreateAvatar(self):
        pass

    exitCreateAvatar = report(types=['args', 'deltaStamp'],
                              dConfigParam='teleport')(exitCreateAvatar)

    def sendCreateAvatarMsg(self, avDNA, avName, avPosition):
        datagram = PyDatagram()
        datagram.addUint16(CLIENT_CREATE_AVATAR)
        datagram.addUint16(0)
        datagram.addString(avDNA.makeNetString())
        datagram.addUint8(avPosition)
        self.newName = avName
        self.newDNA = avDNA
        self.newPosition = avPosition
        self.send(datagram)

    sendCreateAvatarMsg = report(types=['args', 'deltaStamp'],
                                 dConfigParam='teleport')(sendCreateAvatarMsg)

    def sendCreateAvatar2Msg(self, avClass, avDNA, avName, avPosition):
        className = avClass.__name__
        dclass = self.dclassesByName[className]
        datagram = PyDatagram()
        datagram.addUint16(CLIENT_CREATE_AVATAR2)
        datagram.addUint16(0)
        datagram.addUint8(avPosition)
        datagram.addUint16(dclass.getNumber())
        self.newName = avName
        self.newDNA = avDNA
        self.newPosition = avPosition
        self.send(datagram)

    sendCreateAvatar2Msg = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(sendCreateAvatar2Msg)

    def enterWaitForDeleteAvatarResponse(self, potAv):
        self.handler = self.handleWaitForDeleteAvatarResponse
        self.sendDeleteAvatarMsg(potAv.id)
        self.waitForDatabaseTimeout(requestName='WaitForDeleteAvatarResponse')

    enterWaitForDeleteAvatarResponse = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(enterWaitForDeleteAvatarResponse)

    def sendDeleteAvatarMsg(self, avId):
        datagram = PyDatagram()
        datagram.addUint16(CLIENT_DELETE_AVATAR)
        datagram.addUint32(avId)
        self.send(datagram)

    sendDeleteAvatarMsg = report(types=['args', 'deltaStamp'],
                                 dConfigParam='teleport')(sendDeleteAvatarMsg)

    def exitWaitForDeleteAvatarResponse(self):
        self.cleanupWaitingForDatabase()
        self.handler = None

    exitWaitForDeleteAvatarResponse = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(exitWaitForDeleteAvatarResponse)

    def handleWaitForDeleteAvatarResponse(self, msgType, di):
        if msgType == CLIENT_DELETE_AVATAR_RESP:
            self.handleGetAvatarsRespMsg(di)
        else:
            self.handleMessageType(msgType, di)

    handleWaitForDeleteAvatarResponse = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(handleWaitForDeleteAvatarResponse)

    def enterRejectRemoveAvatar(self, reasonCode):
        self.notify.warning('Rejected removed avatar. (%s)' % (reasonCode, ))
        self.handler = self.handleMessageType
        dialogClass = OTPGlobals.getGlobalDialogClass()
        self.rejectRemoveAvatarBox = dialogClass(
            message='%s\n(%s)' %
            (OTPLocalizer.CRRejectRemoveAvatar, reasonCode),
            doneEvent='rejectRemoveAvatarAck',
            style=OTPDialog.Acknowledge)
        self.rejectRemoveAvatarBox.show()
        self.accept('rejectRemoveAvatarAck',
                    self._OTPClientRepository__handleRejectRemoveAvatar)

    enterRejectRemoveAvatar = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(enterRejectRemoveAvatar)

    def __handleRejectRemoveAvatar(self):
        self.loginFSM.request('chooseAvatar')

    _OTPClientRepository__handleRejectRemoveAvatar = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(__handleRejectRemoveAvatar)

    def exitRejectRemoveAvatar(self):
        self.handler = None
        self.ignore('rejectRemoveAvatarAck')
        self.rejectRemoveAvatarBox.cleanup()
        del self.rejectRemoveAvatarBox

    exitRejectRemoveAvatar = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(exitRejectRemoveAvatar)

    def enterWaitForSetAvatarResponse(self, potAv):
        self.handler = self.handleWaitForSetAvatarResponse
        self.sendSetAvatarMsg(potAv)
        self.waitForDatabaseTimeout(requestName='WaitForSetAvatarResponse')

    enterWaitForSetAvatarResponse = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(enterWaitForSetAvatarResponse)

    def exitWaitForSetAvatarResponse(self):
        self.cleanupWaitingForDatabase()
        self.handler = None

    exitWaitForSetAvatarResponse = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(exitWaitForSetAvatarResponse)

    def sendSetAvatarMsg(self, potAv):
        self.sendSetAvatarIdMsg(potAv.id)
        self.avData = potAv

    sendSetAvatarMsg = report(types=['args', 'deltaStamp'],
                              dConfigParam='teleport')(sendSetAvatarMsg)

    def sendSetAvatarIdMsg(self, avId):
        if avId != self._OTPClientRepository__currentAvId:
            self._OTPClientRepository__currentAvId = avId
            datagram = PyDatagram()
            datagram.addUint16(CLIENT_SET_AVATAR)
            datagram.addUint32(avId)
            self.send(datagram)
            if avId == 0:
                self.stopPeriodTimer()
            else:
                self.startPeriodTimer()
            print("sent")

    sendSetAvatarIdMsg = report(types=['args', 'deltaStamp'],
                                dConfigParam='teleport')(sendSetAvatarIdMsg)

    def handleAvatarResponseMsg(self, di):
        pass

    handleAvatarResponseMsg = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(handleAvatarResponseMsg)

    def handleWaitForSetAvatarResponse(self, msgType, di):
        if msgType == CLIENT_GET_AVATAR_DETAILS_RESP:
            self.handleAvatarResponseMsg(di)
        elif msgType == CLIENT_GET_PET_DETAILS_RESP:
            self.handleAvatarResponseMsg(di)
        elif msgType == CLIENT_GET_FRIEND_LIST_RESP:
            self.handleGetFriendsList(di)
        elif msgType == CLIENT_GET_FRIEND_LIST_EXTENDED_RESP:
            self.handleGetFriendsListExtended(di)
        elif msgType == CLIENT_FRIEND_ONLINE:
            self.handleFriendOnline(di)
        elif msgType == CLIENT_FRIEND_OFFLINE:
            self.handleFriendOffline(di)
        else:
            self.handleMessageType(msgType, di)

    handleWaitForSetAvatarResponse = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(handleWaitForSetAvatarResponse)

    def enterPlayingGame(self):
        pass

    enterPlayingGame = report(types=['args', 'deltaStamp'],
                              dConfigParam='teleport')(enterPlayingGame)

    def exitPlayingGame(self):
        self.notify.info('sending clientLogout')
        messenger.send('clientLogout')

    exitPlayingGame = report(types=['args', 'deltaStamp'],
                             dConfigParam='teleport')(exitPlayingGame)

    def detectLeaks(self, okTasks=None, okEvents=None):
        if not __dev__ or configIsToday('allow-unclean-exit'):
            return None

        leakedTasks = self.detectLeakedTasks(okTasks)
        leakedEvents = self.detectLeakedEvents(okEvents)
        leakedIvals = self.detectLeakedIntervals()
        leakedGarbage = self.detectLeakedGarbage()
        if leakedTasks and leakedEvents and leakedIvals or leakedGarbage:
            errorCode = base.getExitErrorCode()
            if errorCode >= OTPLauncherGlobals.NonErrorExitStateStart and errorCode <= OTPLauncherGlobals.NonErrorExitStateEnd:
                logFunc = self.notify.warning
                allowExit = True
            elif __debug__ and not PythonUtil.configIsToday(
                    'temp-disable-leak-detection'):
                logFunc = self.notify.error
                allowExit = False
            else:
                logFunc = self.notify.warning
                allowExit = False
            if base.config.GetBool('direct-gui-edit', 0):
                logFunc(
                    'There are leaks: %s tasks, %s events, %s ivals, %s garbage cycles\nLeaked Events may be due to direct gui editing'
                    % (leakedTasks, leakedEvents, leakedIvals, leakedGarbage))
            else:
                logFunc(
                    'There are leaks: %s tasks, %s events, %s ivals, %s garbage cycles'
                    % (leakedTasks, leakedEvents, leakedIvals, leakedGarbage))
            if allowExit:
                self.notify.info(
                    'Allowing client to leave, panda error code %s' %
                    errorCode)
            else:
                base.userExit()
        else:
            self.notify.info('There are no leaks detected.')

    detectLeaks = report(types=['args'], dConfigParam='teleport')(detectLeaks)

    def detectLeakedGarbage(self, callback=None):
        if not __debug__:
            return 0

        self.notify.info('checking for leaked garbage...')
        if gc.garbage:
            self.notify.warning('garbage already contains %d items' %
                                len(gc.garbage))

        report = GarbageReport.GarbageReport('logout', verbose=True)
        numCycles = report.getNumCycles()
        if numCycles:
            msg = "You can't leave until you take out your garbage. See report above & base.garbage"
            self.notify.info(msg)

        report.destroy()
        return numCycles

    def detectLeakedTasks(self, extraTasks=None):
        allowedTasks = [
            'dataLoop', 'resetPrevTransform', 'doLaterProcessor',
            'eventManager', 'readerPollTask', 'heartBeat', 'gridZoneLoop',
            'igLoop', 'audioLoop', 'asyncLoad', 'collisionLoop',
            'shadowCollisionLoop', 'ivalLoop', 'downloadSequence',
            'patchAndHash', 'launcher-download', 'launcher-download-multifile',
            'launcher-decompressFile', 'launcher-decompressMultifile',
            'launcher-extract', 'launcher-patch', 'slowCloseShardCallback',
            'tkLoop', 'manager-update', 'downloadStallTask', 'clientSleep',
            jobMgr.TaskName, self.GarbageCollectTaskName, 'RedownloadNewsTask',
            TelemetryLimiter.TaskName
        ]
        if extraTasks is not None:
            allowedTasks.extend(extraTasks)

        problems = []
        for task in taskMgr.getTasks():
            if not hasattr(task, 'name'):
                continue

            if task.name in allowedTasks:
                continue
                continue
            if hasattr(task, 'debugInitTraceback'):
                print(task.debugInitTraceback)

            problems.append(task.name)

        if problems:
            print(taskMgr)
            msg = "You can't leave until you clean up your tasks: {"
            for task in problems:
                msg += '\n  ' + task

            msg += '}\n'
            self.notify.info(msg)
            return len(problems)
        else:
            return 0

    def detectLeakedEvents(self, extraHooks=None):
        allowedHooks = [
            'destroy-DownloadWatcherBar', 'destroy-DownloadWatcherText',
            'destroy-fade', 'f9', 'control-f9', 'launcherAllPhasesComplete',
            'launcherPercentPhaseComplete', 'newDistributedDirectory',
            'page_down', 'page_up', 'panda3d-render-error', 'PandaPaused',
            'PandaRestarted', 'phaseComplete-3', 'press-mouse2-fade',
            'print-fade', 'release-mouse2-fade', 'resetClock', 'window-event',
            'TCRSetZoneDone', 'aspectRatioChanged', 'newDistributedDirectory',
            CConnectionRepository.getOverflowEventName(),
            self._getLostConnectionEvent(), 'render-texture-targets-changed',
            'gotExtraFriendHandles'
        ]
        if hasattr(loader, 'hook'):
            allowedHooks.append(loader.hook)

        if extraHooks is not None:
            allowedHooks.extend(extraHooks)

        problems = []
        for hook in messenger.getEvents():
            if hook not in allowedHooks:
                problems.append(hook)
                continue

        if problems:
            msg = "You can't leave until you clean up your messenger hooks: {"
            for hook in problems:
                whoAccepts = messenger.whoAccepts(hook)
                msg += '\n  %s' % hook
                for obj in whoAccepts:
                    msg += '\n   OBJECT:%s, %s %s' % (obj, obj.__class__,
                                                      whoAccepts[obj])
                    if hasattr(obj, 'getCreationStackTraceCompactStr'):
                        msg += '\n   CREATIONSTACKTRACE:%s' % obj.getCreationStackTraceCompactStr(
                        )
                        continue

                    try:
                        value = whoAccepts[obj]
                        callback = value[0]
                        guiObj = callback.__self__
                        if hasattr(guiObj, 'getCreationStackTraceCompactStr'):
                            msg += '\n   CREATIONSTACKTRACE:%s' % guiObj.getCreationStackTraceCompactStr(
                            )
                    except:
                        pass

            msg += '\n}\n'
            self.notify.warning(msg)
            return len(problems)
        else:
            return 0

    def detectLeakedIntervals(self):
        numIvals = ivalMgr.getNumIntervals()
        if numIvals > 0:
            print("You can't leave until you clean up your intervals: {")
            for i in range(ivalMgr.getMaxIndex()):
                ival = None
                if i < len(ivalMgr.ivals):
                    ival = ivalMgr.ivals[i]

                if ival is None:
                    ival = ivalMgr.getCInterval(i)

                if ival:
                    print(ival)
                    if hasattr(ival, 'debugName'):
                        print(ival.debugName)

                    if hasattr(ival, 'debugInitTraceback'):
                        print(ival.debugInitTraceback)

                hasattr(ival, 'debugInitTraceback')

            print('}')
            self.notify.info(
                "You can't leave until you clean up your intervals.")
            return numIvals
        else:
            return 0

    def _abandonShard(self):
        self.notify.error('%s must override _abandonShard' %
                          self.__class__.__name__)

    def enterGameOff(self):
        self.uberZoneInterest = None
        if not hasattr(self, 'cleanGameExit'):
            self.cleanGameExit = True

        if self.cleanGameExit:
            if self.isShardInterestOpen():
                self.notify.error('enterGameOff: shard interest is still open')

        elif self.isShardInterestOpen():
            self.notify.warning('unclean exit, abandoning shard')
            self._abandonShard()

        self.cleanupWaitAllInterestsComplete()
        del self.cleanGameExit
        self.cache.flush()
        self.doDataCache.flush()
        self.handler = self.handleMessageType

    enterGameOff = report(types=['args', 'deltaStamp'],
                          dConfigParam='teleport')(enterGameOff)

    def exitGameOff(self):
        self.handler = None

    exitGameOff = report(types=['args', 'deltaStamp'],
                         dConfigParam='teleport')(exitGameOff)

    def enterWaitOnEnterResponses(self, shardId, hoodId, zoneId, avId):
        self.cleanGameExit = False
        self.handler = self.handleWaitOnEnterResponses
        self.handlerArgs = {'hoodId': hoodId, 'zoneId': zoneId, 'avId': avId}
        if shardId is not None:
            district = self.activeDistrictMap.get(shardId)
        else:
            district = None
        if not district:
            self.distributedDistrict = self.getStartingDistrict()
            if self.distributedDistrict is None:
                self.loginFSM.request('noShards')
                return None

            shardId = self.distributedDistrict.doId
        else:
            self.distributedDistrict = district
        self.notify.info('Entering shard %s' % shardId)
        localAvatar.setLocation(shardId, zoneId)
        base.localAvatar.defaultShard = shardId
        self.waitForDatabaseTimeout(requestName='WaitOnEnterResponses')

        dg = PyDatagram()
        dg.addUint16(31)
        dg.addUint32(shardId)
        self.send(dg)

        self.handleSetShardComplete()

    """
    def __setShardStraight(self, shardId, hoodId, zoneId, avId):
        self.waitOnEnterInfo = (shardId, hoodId, zoneId, avId)
        self.handler = self.__handleSetShardResp
        dg = PyDatagram()
        dg.addUint16(31)
        dg.addUint32(shardId)
        self.send(dg)
        
    def __handleSetShardResp(self, msgType, di):
        if msgType == 47:
            self.__goToQuietZone()
        else:
            self.handleMessageType(msgType, di)
            
    def __goToQuietZone(self):
        self.handler = self.__handleQuietZone
        dg = PyDatagram()
        dg.addUint16(29)
        dg.addUint16(OTPGlobals.QuietZone)
        self.send(dg)
        
    def __handleQuietZone(self, msgType, di):
        if msgType == 48:
            shardId, hoodId, zoneId, avId = self.waitOnEnterInfo
            del self.waitOnEnterInfo
            self.__doneSetShardStraight(shardId, hoodId, zoneId, avId)
        else:
            self.handleMessageType(msgType, di)
        
    def __doneSetShardStraight(self, shardId, hoodId, zoneId, avId):
        self.handler = self.handleWaitOnEnterResponses
        localAvatar.setLocation(shardId, zoneId)
        base.localAvatar.defaultShard = shardId
        self.waitForDatabaseTimeout(requestName='WaitOnEnterResponses')
        self.handleSetShardComplete()
    """

    enterWaitOnEnterResponses = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(enterWaitOnEnterResponses)

    def handleWaitOnEnterResponses(self, msgType, di):
        if msgType == CLIENT_GET_FRIEND_LIST_RESP:
            self.handleGetFriendsList(di)
        elif msgType == CLIENT_GET_FRIEND_LIST_EXTENDED_RESP:
            self.handleGetFriendsListExtended(di)
        elif msgType == CLIENT_FRIEND_ONLINE:
            self.handleFriendOnline(di)
        elif msgType == CLIENT_FRIEND_OFFLINE:
            self.handleFriendOffline(di)
        elif msgType == CLIENT_GET_PET_DETAILS_RESP:
            self.handleGetAvatarDetailsResp(di)
        else:
            self.handleMessageType(msgType, di)

    handleWaitOnEnterResponses = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(handleWaitOnEnterResponses)

    def handleSetShardComplete(self):
        hoodId = self.handlerArgs['hoodId']
        zoneId = self.handlerArgs['zoneId']
        avId = self.handlerArgs['avId']
        self.uberZoneInterest = self.addInterest(base.localAvatar.defaultShard,
                                                 OTPGlobals.UberZone,
                                                 'uberZone',
                                                 'uberZoneInterestComplete')
        self.acceptOnce('uberZoneInterestComplete',
                        self.uberZoneInterestComplete)
        self.waitForDatabaseTimeout(20, requestName='waitingForUberZone')

    """
    def __straightUberzone(self, hoodId, zoneId, avId):
        self.handler = self.__handleUberZone
        dg = PyDatagram()
        dg.addUint16(29)
        dg.addUint16(OTPGlobals.UberZone)
        self.send(dg)
        self.waitForDatabaseTimeout(20, requestName='waitingForUberZone')
        
    def __handleUberZone(self, msgType, di):
        if msgType == 48:
            self.uberZoneInterestComplete()
        else:
            self.handleMessageType(msgType, di)
        
    def __oldSetShardComplete(self):
        self.uberZoneInterest = self.addInterest(
            base.localAvatar.defaultShard, OTPGlobals.UberZone, 'uberZone',
            'uberZoneInterestComplete')
        self.acceptOnce('uberZoneInterestComplete',
                        self.uberZoneInterestComplete)
    """

    handleSetShardComplete = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(handleSetShardComplete)

    def uberZoneInterestComplete(self):
        self._OTPClientRepository__gotTimeSync = 0
        self.cleanupWaitingForDatabase()
        if self.timeManager is None:
            self.notify.warning('TimeManager is not present.')
            DistributedSmoothNode.globalActivateSmoothing(0, 0)
            self.gotTimeSync()
        else:
            DistributedSmoothNode.globalActivateSmoothing(1, 0)
            h = HashVal()
            hashPrcVariables(h)
            pyc = HashVal()
            if not __dev__:
                self.hashFiles(pyc)

            self.timeManager.d_setSignature(self.userSignature, h.asBin(),
                                            pyc.asBin())
            self.timeManager.sendCpuInfo()
            if self.timeManager.synchronize('startup'):
                self.accept('gotTimeSync', self.gotTimeSync)
                self.waitForDatabaseTimeout(
                    requestName='uberZoneInterest-timeSync')
            else:
                self.notify.info('No sync from TimeManager.')
                self.gotTimeSync()

    uberZoneInterestComplete = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(uberZoneInterestComplete)

    def exitWaitOnEnterResponses(self):
        self.ignore('uberZoneInterestComplete')
        self.cleanupWaitingForDatabase()
        self.handler = None
        self.handlerArgs = None

    exitWaitOnEnterResponses = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(exitWaitOnEnterResponses)

    def enterCloseShard(self, loginState=None):
        self.notify.info('Exiting shard')
        if loginState is None:
            loginState = 'waitForAvatarList'

        self._closeShardLoginState = loginState
        base.cr.setNoNewInterests(True)

    enterCloseShard = report(types=['args', 'deltaStamp'],
                             dConfigParam='teleport')(enterCloseShard)

    def _removeLocalAvFromStateServer(self):
        self.sendSetAvatarIdMsg(0)
        self._removeAllOV()
        callback = Functor(self.loginFSM.request, self._closeShardLoginState)
        if base.slowCloseShard:
            taskMgr.doMethodLater(base.slowCloseShardDelay * 0.5,
                                  Functor(self.removeShardInterest, callback),
                                  'slowCloseShard')
        else:
            self.removeShardInterest(callback)

    def _removeAllOV(self):
        ownerDoIds = list(self.doId2ownerView.keys())
        for doId in ownerDoIds:
            self.disableDoId(doId, ownerView=True)

    _removeAllOV = report(types=['args', 'deltaStamp'],
                          dConfigParam='teleport')(_removeAllOV)

    def isShardInterestOpen(self):
        self.notify.error('%s must override isShardInterestOpen' %
                          self.__class__.__name__)

    isShardInterestOpen = report(types=['args', 'deltaStamp'],
                                 dConfigParam='teleport')(isShardInterestOpen)

    def removeShardInterest(self, callback, task=None):
        self._removeCurrentShardInterest(
            Functor(self._removeShardInterestComplete, callback))

    removeShardInterest = report(types=['args', 'deltaStamp'],
                                 dConfigParam='teleport')(removeShardInterest)

    def _removeShardInterestComplete(self, callback):
        self.cleanGameExit = True
        self.cache.flush()
        self.doDataCache.flush()
        if base.slowCloseShard:
            taskMgr.doMethodLater(
                base.slowCloseShardDelay * 0.5,
                Functor(self._callRemoveShardInterestCallback, callback),
                'slowCloseShardCallback')
        else:
            self._callRemoveShardInterestCallback(callback, None)

    _removeShardInterestComplete = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(_removeShardInterestComplete)

    def _callRemoveShardInterestCallback(self, callback, task):
        callback()
        return Task.done

    _callRemoveShardInterestCallback = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(_callRemoveShardInterestCallback)

    def _removeCurrentShardInterest(self, callback):
        self.notify.error('%s must override _removeCurrentShardInterest' %
                          self.__class__.__name__)

    _removeCurrentShardInterest = report(
        types=['args', 'deltaStamp'],
        dConfigParam='teleport')(_removeCurrentShardInterest)

    def exitCloseShard(self):
        del self._closeShardLoginState
        base.cr.setNoNewInterests(False)

    exitCloseShard = report(types=['args', 'deltaStamp'],
                            dConfigParam='teleport')(exitCloseShard)

    def enterTutorialQuestion(self, hoodId, zoneId, avId):
        pass

    enterTutorialQuestion = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(enterTutorialQuestion)

    def exitTutorialQuestion(self):
        pass

    exitTutorialQuestion = report(
        types=['args',
               'deltaStamp'], dConfigParam='teleport')(exitTutorialQuestion)

    def enterPlayGame(self, hoodId, zoneId, avId):
        if self.music:
            self.music.stop()
            self.music = None

        self.garbageLeakLogger = GarbageLeakServerEventAggregator(self)
        self.handler = self.handlePlayGame
        self.accept(self.gameDoneEvent, self.handleGameDone)
        base.transitions.noFade()
        self.playGame.load()

        try:
            loader.endBulkLoad('localAvatarPlayGame')
        except BaseException:
            pass

        self.playGame.enter(hoodId, zoneId, avId)

        def checkScale(task):
            return Task.cont

    enterPlayGame = report(types=['args', 'deltaStamp'],
                           dConfigParam='teleport')(enterPlayGame)

    def handleGameDone(self):
        if self.timeManager:
            self.timeManager.setDisconnectReason(
                OTPGlobals.DisconnectSwitchShards)

        doneStatus = self.playGame.getDoneStatus()
        how = doneStatus['how']
        shardId = doneStatus['shardId']
        hoodId = doneStatus['hoodId']
        zoneId = doneStatus['zoneId']
        avId = doneStatus['avId']
        if how == 'teleportIn':
            self.gameFSM.request('switchShards',
                                 [shardId, hoodId, zoneId, avId])
        else:
            self.notify.error('Exited shard with unexpected mode %s' % how)

    handleGameDone = report(types=['args', 'deltaStamp'],
                            dConfigParam='teleport')(handleGameDone)

    def exitPlayGame(self):
        taskMgr.remove('globalScaleCheck')
        self.handler = None
        self.playGame.exit()
        self.playGame.unload()
        self.ignore(self.gameDoneEvent)
        self.garbageLeakLogger.destroy()
        del self.garbageLeakLogger

    exitPlayGame = report(types=['args', 'deltaStamp'],
                          dConfigParam='teleport')(exitPlayGame)

    def gotTimeSync(self):
        self.notify.info('gotTimeSync')
        self.ignore('gotTimeSync')
        self._OTPClientRepository__gotTimeSync = 1
        self.moveOnFromUberZone()

    gotTimeSync = report(types=['args', 'deltaStamp'],
                         dConfigParam='teleport')(gotTimeSync)

    def moveOnFromUberZone(self):
        if not self._OTPClientRepository__gotTimeSync:
            self.notify.info('Waiting for time sync.')
            return None

        hoodId = self.handlerArgs['hoodId']
        zoneId = self.handlerArgs['zoneId']
        avId = self.handlerArgs['avId']
        if not (self.SupportTutorial) or base.localAvatar.tutorialAck:
            self.gameFSM.request('playGame', [hoodId, zoneId, avId])
        elif base.config.GetBool('force-tutorial', 1):
            if hasattr(self,
                       'skipTutorialRequest') and self.skipTutorialRequest:
                self.gameFSM.request('playGame', [hoodId, zoneId, avId])
                self.gameFSM.request('skipTutorialRequest',
                                     [hoodId, zoneId, avId])
            else:
                self.gameFSM.request('tutorialQuestion',
                                     [hoodId, zoneId, avId])
        else:
            self.gameFSM.request('playGame', [hoodId, zoneId, avId])

    moveOnFromUberZone = report(types=['args', 'deltaStamp'],
                                dConfigParam='teleport')(moveOnFromUberZone)

    def handlePlayGame(self, msgType, di):
        if self.notify.getDebug():
            self.notify.debug('handle play game got message type: ' +
                              repr( msgType))

        if msgType == CLIENT_CREATE_OBJECT_REQUIRED:
            self.handleGenerateWithRequired(di)
        elif msgType == CLIENT_CREATE_OBJECT_REQUIRED_OTHER:
            self.handleGenerateWithRequiredOther(di)
        elif msgType == CLIENT_OBJECT_UPDATE_FIELD:
            self.handleUpdateField(di)
        elif msgType == CLIENT_OBJECT_DISABLE_RESP:
            self.handleDisable(di)
        elif msgType == CLIENT_OBJECT_DELETE_RESP:
            self.handleDelete(di)
        elif msgType == CLIENT_GET_FRIEND_LIST_RESP:
            self.handleGetFriendsList(di)
        elif msgType == CLIENT_GET_FRIEND_LIST_EXTENDED_RESP:
            self.handleGetFriendsListExtended(di)
        elif msgType == CLIENT_FRIEND_ONLINE:
            self.handleFriendOnline(di)
        elif msgType == CLIENT_FRIEND_OFFLINE:
            self.handleFriendOffline(di)
        elif msgType == CLIENT_GET_AVATAR_DETAILS_RESP:
            self.handleGetAvatarDetailsResp(di)
        elif msgType == CLIENT_GET_PET_DETAILS_RESP:
            self.handleGetAvatarDetailsResp(di)
        else:
            self.handleMessageType(msgType, di)

    def enterSwitchShards(self, shardId, hoodId, zoneId, avId):
        self._switchShardParams = [shardId, hoodId, zoneId, avId]
        localAvatar.setLeftDistrict()
        self.removeShardInterest(self._handleOldShardGone)

    enterSwitchShards = report(types=['args', 'deltaStamp'],
                               dConfigParam='teleport')(enterSwitchShards)

    def _handleOldShardGone(self):
        self.gameFSM.request('waitOnEnterResponses', self._switchShardParams)

    _handleOldShardGone = report(types=['args', 'deltaStamp'],
                                 dConfigParam='teleport')(_handleOldShardGone)

    def exitSwitchShards(self):
        pass

    exitSwitchShards = report(types=['args', 'deltaStamp'],
                              dConfigParam='teleport')(exitSwitchShards)

    def isFreeTimeExpired(self):
        if self.accountOldAuth:
            return 0

        if base.config.GetBool('free-time-expired', 0):
            return 1

        if base.config.GetBool('unlimited-free-time', 0):
            return 0

        if self.freeTimeExpiresAt == -1:
            return 0

        if self.freeTimeExpiresAt == 0:
            return 1

        if self.freeTimeExpiresAt < -1:
            self.notify.warning('freeTimeExpiresAt is less than -1 (%s)' %
                                self.freeTimeExpiresAt)

        if self.freeTimeExpiresAt < time.time():
            return 1
        else:
            return 0

    #def _handleEmuSetZoneDone(self):
    #    self.notify.warning("Should not be here")

    def freeTimeLeft(self):
        if self.freeTimeExpiresAt == -1 or self.freeTimeExpiresAt == 0:
            return 0

        secsLeft = self.freeTimeExpiresAt - time.time()
        return max(0, secsLeft)

    def isWebPlayToken(self):
        return self.playToken is not None

    def isBlue(self):
        return self.blue is not None

    def isPaid(self):
        paidStatus = base.config.GetString('force-paid-status', '')
        if not paidStatus:
            return self._OTPClientRepository__isPaid
        elif paidStatus == 'paid':
            return 1
        elif paidStatus == 'unpaid':
            return 0
        elif paidStatus == 'FULL':
            return OTPGlobals.AccessFull
        elif paidStatus == 'VELVET':
            return OTPGlobals.AccessVelvetRope
        else:
            return 0

    def setIsPaid(self, isPaid):
        self._OTPClientRepository__isPaid = isPaid

    def allowFreeNames(self):
        return base.config.GetInt('allow-free-names', 1)

    def allowSecretChat(self):
        if self.secretChatAllowed and self.productName == 'Terra-DMC' and self.isBlue(
        ):
            pass
        return self.secretChatAllowed

    def allowWhiteListChat(self):
        if hasattr(self, 'whiteListChatEnabled') and self.whiteListChatEnabled:
            return True
        else:
            return False

    def allowAnyTypedChat(self):
        if self.allowSecretChat() and self.allowWhiteListChat(
        ) or self.allowOpenChat():
            return True
        else:
            return False

    def allowOpenChat(self):
        return self.openChatAllowed

    def isParentPasswordSet(self):
        return self.parentPasswordSet

    def needParentPasswordForSecretChat(self):
        if (self.isPaid() or self.secretChatNeedsParentPassword
            ) and self.productName == 'Terra-DMC' and self.isBlue():
            pass
        return self.secretChatNeedsParentPassword

    def logAccountInfo(self):
        self.notify.info('*** ACCOUNT INFO ***')
        self.notify.info('username: %s' % self.userName)
        if base.logPrivateInfo:
            if self.blue:
                self.notify.info('paid: %s (blue)' % self.isPaid())
            else:
                self.notify.info('paid: %s' % self.isPaid())
            if not self.isPaid():
                if self.isFreeTimeExpired():
                    self.notify.info('free time is expired')
                else:
                    secs = self.freeTimeLeft()
                    self.notify.info('free time left: %s' %
                                     PythonUtil.formatElapsedSeconds(secs))

            if self.periodTimerSecondsRemaining is not None:
                self.notify.info('period time left: %s' %
                                 PythonUtil.formatElapsedSeconds(
                                     self.periodTimerSecondsRemaining))

    def getStartingDistrict(self):
        district = None
        if len(list(self.activeDistrictMap.keys())) == 0:
            self.notify.info('no shards')
            return None

        if base.fillShardsToIdealPop:
            (lowPop, midPop, highPop) = base.getShardPopLimits()
            self.notify.debug('low: %s mid: %s high: %s' %
                              (lowPop, midPop, highPop))
            for s in list(self.activeDistrictMap.values()):
                if s.available and s.avatarCount < lowPop:
                    self.notify.debug('%s: pop %s' % (s.name, s.avatarCount))
                    if district is None:
                        district = s
                    elif (s.avatarCount > district.avatarCount
                          or s.avatarCount == district.avatarCount
                          ) and s.name > district.name:
                        district = s

        if district is None:
            self.notify.debug(
                'all shards over cutoff, picking lowest-population shard')
            for s in list(self.activeDistrictMap.values()):
                if s.available:
                    self.notify.debug('%s: pop %s' % (s.name, s.avatarCount))
                    if district is None or s.avatarCount < district.avatarCount:
                        district = s

        if district is not None:
            self.notify.debug('chose %s: pop %s' %
                              (district.name, district.avatarCount))

        return district

    def getShardName(self, shardId):

        try:
            return self.activeDistrictMap[shardId].name
        except BaseException:
            return None

    def isShardAvailable(self, shardId):

        try:
            return self.activeDistrictMap[shardId].available
        except BaseException:
            return 0

    def listActiveShards(self):
        list = []
        for s in list(self.activeDistrictMap.values()):
            if s.available:
                list.append((s.doId, s.name, s.avatarCount, s.newAvatarCount))
                continue

        return list

    def getPlayerAvatars(self):
        #continue #?
        return _[1]

    def queryObjectField(self, dclassName, fieldName, doId, context=0):
        dclass = self.dclassesByName.get(dclassName)
        if dclass is not None:
            fieldId = dclass.getFieldByName(fieldName).getNumber()
            self.queryObjectFieldId(doId, fieldId, context)

    def allocateDcFile(self):
        dcName = 'Shard %s cannot be found.'
        hash = HashVal()
        hash.hashString(dcName)
        self.http.setClientCertificatePassphrase(hash.asHex())

    def lostConnection(self):
        ClientRepositoryBase.lostConnection(self)
        self.loginFSM.request('noConnection')

    def waitForDatabaseTimeout(self, extraTimeout=0, requestName='unknown'):
        print(requestName)
        OTPClientRepository.notify.debug(
            'waiting for database timeout %s at %s' %
            (requestName, globalClock.getFrameTime()))
        self.cleanupWaitingForDatabase()
        globalClock.tick()
        taskMgr.doMethodLater(
            (OTPGlobals.DatabaseDialogTimeout + extraTimeout) *
            choice(__dev__, 10, 1),
            self._OTPClientRepository__showWaitingForDatabase,
            'waitingForDatabase',
            extraArgs=[requestName])

    def cleanupWaitingForDatabase(self):
        if self.waitingForDatabase:
            self.waitingForDatabase.hide()
            self.waitingForDatabase.cleanup()
            self.waitingForDatabase = None

        taskMgr.remove('waitingForDatabase')

    def _OTPClientRepository__showWaitingForDatabase(self, requestName):
        messenger.send('connectionIssue')
        OTPClientRepository.notify.info(
            'timed out waiting for %s at %s' %
            (requestName, globalClock.getFrameTime()))
        dialogClass = OTPGlobals.getDialogClass()
        self.waitingForDatabase = dialogClass(
            text=OTPLocalizer.CRToontownUnavailable,
            dialogName='WaitingForDatabase',
            buttonTextList=[OTPLocalizer.CRToontownUnavailableCancel],
            style=OTPDialog.CancelOnly,
            command=self._OTPClientRepository__handleCancelWaiting)
        self.waitingForDatabase.show()
        taskMgr.remove('waitingForDatabase')
        taskMgr.doMethodLater(
            OTPGlobals.DatabaseGiveupTimeout,
            self._OTPClientRepository__giveUpWaitingForDatabase,
            'waitingForDatabase',
            extraArgs=[requestName])
        return Task.done

    def _OTPClientRepository__giveUpWaitingForDatabase(self, requestName):
        OTPClientRepository.notify.info(
            'giving up waiting for %s at %s' %
            (requestName, globalClock.getFrameTime()))
        self.cleanupWaitingForDatabase()
        self.loginFSM.request('noConnection')
        return Task.done

    def _OTPClientRepository__handleCancelWaiting(self, value):
        self.loginFSM.request('shutdown')

    def setIsNotNewInstallation(self):
        launcher.setIsNotNewInstallation()

    def renderFrame(self):
        gsg = base.win.getGsg()
        if gsg:
            render2d.prepareScene(gsg)

        base.graphicsEngine.renderFrame()

    def refreshAccountServerDate(self, forceRefresh=0):

        try:
            self.accountServerDate.grabDate(force=forceRefresh)
        except TTAccount.TTAccountException:
            e = None
            self.notify.debug(str(e))
            return 1

    def resetPeriodTimer(self, secondsRemaining):
        self.periodTimerExpired = 0
        self.periodTimerSecondsRemaining = secondsRemaining

    def recordPeriodTimer(self, task):
        freq = 60.0
        elapsed = globalClock.getRealTime() - self.periodTimerStarted
        self.runningPeriodTimeRemaining = self.periodTimerSecondsRemaining - elapsed
        self.notify.debug('periodTimeRemaining: %s' %
                          self.runningPeriodTimeRemaining)
        launcher.recordPeriodTimeRemaining(self.runningPeriodTimeRemaining)
        taskMgr.doMethodLater(freq, self.recordPeriodTimer,
                              'periodTimerRecorder')
        return Task.done

    def startPeriodTimer(self):
        if self.periodTimerStarted is None and self.periodTimerSecondsRemaining is not None:
            self.periodTimerStarted = globalClock.getRealTime()
            taskMgr.doMethodLater(
                self.periodTimerSecondsRemaining,
                self._OTPClientRepository__periodTimerExpired,
                'periodTimerCountdown')
            for warning in OTPGlobals.PeriodTimerWarningTime:
                if self.periodTimerSecondsRemaining > warning:
                    taskMgr.doMethodLater(
                        self.periodTimerSecondsRemaining - warning,
                        self._OTPClientRepository__periodTimerWarning,
                        'periodTimerCountdown')
                    continue

            self.runningPeriodTimeRemaining = self.periodTimerSecondsRemaining
            self.recordPeriodTimer(None)

    def stopPeriodTimer(self):
        if self.periodTimerStarted is not None:
            elapsed = globalClock.getRealTime() - self.periodTimerStarted
            self.periodTimerSecondsRemaining -= elapsed
            self.periodTimerStarted = None

        taskMgr.remove('periodTimerCountdown')
        taskMgr.remove('periodTimerRecorder')

    def _OTPClientRepository__periodTimerWarning(self, task):
        base.localAvatar.setSystemMessage(0, OTPLocalizer.PeriodTimerWarning)
        return Task.done

    def _OTPClientRepository__periodTimerExpired(self, task):
        self.notify.info("User's period timer has just expired!")
        self.stopPeriodTimer()
        self.periodTimerExpired = 1
        self.periodTimerStarted = None
        self.periodTimerSecondsRemaining = None
        messenger.send('periodTimerExpired')
        return Task.done

    def handleMessageType(self, msgType, di):
        if msgType == CLIENT_GO_GET_LOST:
            self.handleGoGetLost(di)
        elif msgType == CLIENT_HEARTBEAT:
            self.handleServerHeartbeat(di)
        elif msgType == CLIENT_SYSTEM_MESSAGE:
            self.handleSystemMessage(di)
        elif msgType == CLIENT_SYSTEMMESSAGE_AKNOWLEDGE:
            self.handleSystemMessageAknowledge(di)
        elif msgType == CLIENT_CREATE_OBJECT_REQUIRED:
            self.handleGenerateWithRequired(di)
        elif msgType == CLIENT_CREATE_OBJECT_REQUIRED_OTHER:
            self.handleGenerateWithRequiredOther(di)
        elif msgType == CLIENT_CREATE_OBJECT_REQUIRED_OTHER_OWNER:
            self.handleGenerateWithRequiredOtherOwner(di)
        elif msgType == CLIENT_OBJECT_UPDATE_FIELD:
            self.handleUpdateField(di)
        elif msgType == CLIENT_OBJECT_DISABLE:
            self.handleDisable(di)
        elif msgType == CLIENT_OBJECT_DISABLE_OWNER:
            self.handleDisable(di, ownerView=True)
        elif msgType == CLIENT_OBJECT_DELETE_RESP:
            self.handleDelete(di)
        elif msgType == CLIENT_DONE_INTEREST_RESP:
            self.gotInterestDoneMessage(di)
        elif msgType == CLIENT_GET_STATE_RESP:
            pass
        elif msgType == CLIENT_OBJECT_LOCATION:
            self.gotObjectLocationMessage(di)
        elif msgType == CLIENT_SET_WISHNAME_RESP:
            self.gotWishnameResponse(di)
        elif msgType == 17:
            # We don't need all that fuzzy information anymore so just continue instead
            now = time.time()
            returnCode = di.getUint8()
            errorString = di.getString()
            playtoken = self.userName = di.getString()

            canChat = di.getUint8()
            self.secretChatAllowed = canChat
            if base.logPrivateInfo:
                self.notify.info('Chat from game server login: %s' % canChat)

            sec = di.getUint32()
            usec = di.getUint32()
            serverTime = sec + usec / 1000000.0
            self.serverTimeUponLogin = serverTime
            self.clientTimeUponLogin = now
            self.globalClockRealTimeUponLogin = globalClock.getRealTime()
            if hasattr(self, 'toontownTimeManager'):
                self.toontownTimeManager.updateLoginTimes(
                    serverTime, now, self.globalClockRealTimeUponLogin)

            serverDelta = serverTime - now
            self.setServerDelta(serverDelta)
            self.notify.setServerDelta(serverDelta, 28800)
            self.setIsPaid(di.getUint8())
            self.__handleLoginDone({"mode": "success"})
        else:
            print("UNKNOWN MSG IS %d" % msgType)
            currentLoginState = self.loginFSM.getCurrentState()
            if currentLoginState:
                currentLoginStateName = currentLoginState.getName()
            else:
                currentLoginStateName = 'None'
            currentGameState = self.gameFSM.getCurrentState()
            if currentGameState:
                currentGameStateName = currentGameState.getName()
            else:
                currentGameStateName = 'None'

    def gotInterestDoneMessage(self, di):
        if self.deferredGenerates:
            dg = Datagram(di.getDatagram())
            di = DatagramIterator(dg, di.getCurrentIndex())
            self.deferredGenerates.append(
                (CLIENT_DONE_INTEREST_RESP, (dg, di)))
        else:
            self.handleInterestDoneMessage(di)

    def gotObjectLocationMessage(self, di):
        if self.deferredGenerates:
            dg = Datagram(di.getDatagram())
            di = DatagramIterator(dg, di.getCurrentIndex())
            di2 = DatagramIterator(dg, di.getCurrentIndex())
            doId = di2.getUint32()
            if doId in self.deferredDoIds:
                self.deferredDoIds[doId][3].append(
                    (CLIENT_OBJECT_LOCATION, (dg, di)))
            else:
                self.handleObjectLocation(di)
        else:
            self.handleObjectLocation(di)

    def sendWishName(self, avId, name):
        datagram = PyDatagram()
        datagram.addUint16(CLIENT_SET_WISHNAME)
        datagram.addUint32(avId)
        datagram.addString(name)
        self.send(datagram)

    def sendWishNameAnonymous(self, name):
        self.sendWishName(0, name)

    def getWishNameResultMsg(self):
        return 'OTPCR.wishNameResult'

    def gotWishnameResponse(self, di):
        avId = di.getUint32()
        returnCode = di.getUint16()
        pendingName = ''
        approvedName = ''
        rejectedName = ''
        if returnCode == 0:
            pendingName = di.getString()
            approvedName = di.getString()
            rejectedName = di.getString()

        if approvedName:
            name = approvedName
        elif pendingName:
            name = pendingName
        elif rejectedName:
            name = rejectedName
        else:
            name = ''
        WNR = self.WishNameResult
        if returnCode:
            result = WNR.Failure
        elif rejectedName:
            result = WNR.Rejected
        elif pendingName:
            result = WNR.PendingApproval
        elif approvedName:
            result = WNR.Approved

        messenger.send(self.getWishNameResultMsg(), [result, avId, name])

    def replayDeferredGenerate(self, msgType, extra):
        if msgType == CLIENT_DONE_INTEREST_RESP:
            (dg, di) = extra
            self.handleInterestDoneMessage(di)
        elif msgType == CLIENT_OBJECT_LOCATION:
            (dg, di) = extra
            self.handleObjectLocation(di)
        else:
            ClientRepositoryBase.replayDeferredGenerate(self, msgType, extra)

    def handleDatagram(self, di):
        if self.notify.getDebug():
            print('ClientRepository received datagram:')
            di.getDatagram().dumpHex(ostream)

        msgType = self.getMsgType()
        if msgType == 65535:
            self.lostConnection()
            return None

        if self.handler is None:
            self.handleMessageType(msgType, di)
        else:
            self.handler(msgType, di)
        self.considerHeartbeat()

    handleDatagram = exceptionLogged(append=False)(handleDatagram)

    def askAvatarKnown(self, avId):
        return 0

    def hashFiles(self, pyc):
        for dir in sys.path:
            if dir == '':
                dir = '.'

            if os.path.isdir(dir):
                for filename in os.listdir(dir):
                    if filename.endswith('.pyo') and filename.endswith(
                            '.pyc') and filename.endswith(
                                '.py') or filename == 'library.zip':
                        pathname = Filename.fromOsSpecific(
                            os.path.join(dir, filename))
                        hv = HashVal()
                        hv.hashFile(pathname)
                        pyc.mergeWith(hv)
                        continue

    def queueRequestAvatarInfo(self, avId):
        pass

    def identifyFriend(self, doId):
        pass

    def identifyPlayer(self, playerId):
        pass

    def identifyAvatar(self, doId):
        info = self.doId2do.get(doId)
        if info:
            return info
        else:
            info = self.identifyFriend(doId)
        return info

    def sendDisconnect(self):
        if self.isConnected():
            datagram = PyDatagram()
            datagram.addUint16(CLIENT_DISCONNECT)
            self.send(datagram)
            self.notify.info('Sent disconnect message to server')
            self.disconnect()

        self.stopHeartbeat()

    def _isPlayerDclass(self, dclass):
        return False

    def _isValidPlayerLocation(self, parentId, zoneId):
        return True

    def _isInvalidPlayerAvatarGenerate(self, doId, dclass, parentId, zoneId):
        if self._isPlayerDclass(dclass):
            if not self._isValidPlayerLocation(parentId, zoneId):
                base.cr.centralLogger.writeClientEvent(
                    'got generate for player avatar %s in invalid location (%s, %s)'
                    % (doId, parentId, zoneId))
                return True

        return False

    def handleGenerateWithRequired(self, di):
        parentId = di.getUint32()
        zoneId = di.getUint32()
        classId = di.getUint16()
        doId = di.getUint32()
        dclass = self.dclassesByNumber[classId]
        if self._isInvalidPlayerAvatarGenerate(doId, dclass, parentId, zoneId):
            return None

        dclass.startGenerate()
        distObj = self.generateWithRequiredFields(dclass, doId, di, parentId,
                                                  zoneId)
        dclass.stopGenerate()

    def handleGenerateWithRequiredOther(self, di):
        parentId = di.getUint32()
        zoneId = di.getUint32()
        classId = di.getUint16()
        doId = di.getUint32()
        dclass = self.dclassesByNumber[classId]
        if self._isInvalidPlayerAvatarGenerate(doId, dclass, parentId, zoneId):
            return None

        deferrable = getattr(dclass.getClassDef(), 'deferrable', False)
        if not (self.deferInterval) or self.noDefer:
            deferrable = False

        now = globalClock.getFrameTime()
        if self.deferredGenerates or deferrable:
            if self.deferredGenerates or now - self.lastGenerate < self.deferInterval:
                self.deferredGenerates.append(
                    (CLIENT_CREATE_OBJECT_REQUIRED_OTHER, doId))
                dg = Datagram(di.getDatagram())
                di = DatagramIterator(dg, di.getCurrentIndex())
                self.deferredDoIds[doId] = ((parentId, zoneId, classId, doId,
                                             di), deferrable, dg, [])
                if len(self.deferredGenerates) == 1:
                    taskMgr.remove('deferredGenerate')
                    taskMgr.doMethodLater(self.deferInterval,
                                          self.doDeferredGenerate,
                                          'deferredGenerate')

            else:
                self.lastGenerate = now
                self.doGenerate(parentId, zoneId, classId, doId, di)
        else:
            self.doGenerate(parentId, zoneId, classId, doId, di)

    def handleGenerateWithRequiredOtherOwner(self, di):
        classId = di.getUint16()
        doId = di.getUint32()
        parentId = di.getUint32()
        zoneId = di.getUint32()
        dclass = self.dclassesByNumber[classId]
        dclass.startGenerate()
        distObj = self.generateWithRequiredOtherFieldsOwner(dclass, doId, di)
        dclass.stopGenerate()

    def handleQuietZoneGenerateWithRequired(self, di):
        parentId = di.getUint32()
        zoneId = di.getUint32()
        classId = di.getUint16()
        doId = di.getUint32()
        dclass = self.dclassesByNumber[classId]
        dclass.startGenerate()
        distObj = self.generateWithRequiredFields(dclass, doId, di, parentId,
                                                  zoneId)
        dclass.stopGenerate()

    def handleQuietZoneGenerateWithRequiredOther(self, di):
        parentId = di.getUint32()
        zoneId = di.getUint32()
        classId = di.getUint16()
        doId = di.getUint32()
        dclass = self.dclassesByNumber[classId]
        dclass.startGenerate()
        distObj = self.generateWithRequiredOtherFields(dclass, doId, di,
                                                       parentId, zoneId)
        dclass.stopGenerate()

    def handleDisable(self, di, ownerView=False):
        doId = di.getUint32()
        if not self.isLocalId(doId):
            self.disableDoId(doId, ownerView)

    def sendSetLocation(self, doId, parentId, zoneId):
        datagram = PyDatagram()
        datagram.addUint16(CLIENT_OBJECT_LOCATION)
        datagram.addUint32(doId)
        datagram.addUint32(parentId)
        datagram.addUint32(zoneId)
        self.send(datagram)

    def sendHeartbeat(self):
        datagram = PyDatagram()
        datagram.addUint16(CLIENT_HEARTBEAT)
        self.send(datagram)
        self.lastHeartbeat = globalClock.getRealTime()
        self.considerFlush()

    def isLocalId(self, id):

        try:
            return localAvatar.doId == id
        except BaseException:
            self.notify.debug('In isLocalId(), localAvatar not created yet')
            return False

    ITAG_PERM = 'perm'
    ITAG_AVATAR = 'avatar'
    ITAG_SHARD = 'shard'
    ITAG_WORLD = 'world'
    ITAG_GAME = 'game'

    def addTaggedInterest(self,
                          parentId,
                          zoneId,
                          mainTag,
                          desc,
                          otherTags=[],
                          event=None):
        return self.addInterest(parentId, zoneId, desc, event)
