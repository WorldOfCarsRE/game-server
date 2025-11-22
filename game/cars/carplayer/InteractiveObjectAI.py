from direct.directnotify import DirectNotifyGlobal
from .DistributedCarAvatarAI import DistributedCarAvatarAI

TYPE_NPC = 0
TYPE_SPAWNED_SPRITE = 1
TYPE_MAP_SPRITE = 2

# Interation types
CMD_TYPE_NEGATIVE = 0
CMD_TYPE_POSITIVE = 1

COMMAND_OFFER_QUERY_INTERACTIONS = 1
COMMAND_OFFER_PLAYER_HONK = 52
COMMAND_OFFER_PLAYER_APPROACH = 54
COMMAND_OFFER_PLAYER_RETREAT = 55
COMMAND_OFFER_PLAYER_CLICK = 57
COMMAND_CLICK = COMMAND_OFFER_PLAYER_CLICK

COMMAND_OFFER_PLAYER_INTRODUCTION = 30
COMMAND_OFFER_SPEAK = 31
COMMAND_OFFER_SHOP = 32
COMMAND_OFFER_GAME = 33
COMMAND_OFFER_SPONSOR_BOOTH = 35

COMMAND_SET_MAP_EFFECT = 78

COMMAND_SHOW_GPS = 72

COMMAND_OFFER_QUEST_ACCEPT = 20
COMMAND_OFFER_QUEST_ABANDON = 21
COMMAND_OFFER_QUEST_COMPLETE = 22
COMMAND_OFFER_QUEST_READY = 23
COMMAND_OFFER_QUEST_PASSIVE = 24
COMMAND_OFFER_QUEST_LATER = 25

COMMAND_OFFER_RACING_QUEST_ACCEPT = 120
COMMAND_OFFER_RACING_QUEST_IN_PROGRESS = 126
COMMAND_OFFER_RACING_QUEST_COMPLETE = 122

class InteractiveObjectAI(DistributedCarAvatarAI):
    notify = directNotify.newCategory('InteractiveObjectAI')

    def __init__(self, air):
        DistributedCarAvatarAI.__init__(self, air)
        self.name = ''
        self.assetId = 0
        self.catalogId = 0
        self.objType = TYPE_MAP_SPRITE
        self.globalState = 0
        self.visible = 1
        self.clientScript = 'scripts/interactive/default_npc.lua'

    def announceGenerate(self):
        DistributedCarAvatarAI.announceGenerate(self)

    def getName(self):
        return self.name

    def getAssetId(self):
        return self.assetId

    def getCatalogId(self):
        return self.catalogId

    def getType(self):
        return self.objType

    def getGlobalState(self):
        return self.globalState

    def getVisible(self):
        return self.visible

    def getClientScript(self):
        return self.clientScript

    def getState(self):
        return 0

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        """
        Classes inheriting us will override this function.
        """
        pass

    def triggerInteraction(self, eventId: int, args: list):
        avatarId = self.air.getAvatarIdFromSender()
        self.notify.debug(f'triggerInteraction - {eventId} - {args}')

        self.handleInteraction(avatarId, eventId, args)

    def d_broadcastChoreography(self, animation: list, sound: list, effect: list, dialogue: list):
        self.sendUpdate('broadcastChoreography', [[*animation], [*sound], [*effect], [*dialogue]])

    def d_broadcastChoreographyToPlayer(self, playerId: int, animation: list, sound: list, effect: list, dialogue: list):
        self.sendUpdateToAvatarId(playerId, 'broadcastChoreography', [[*animation], [*sound], [*effect], [*dialogue]])

    def d_setInteractiveCommands(self, avatarId: int, eventId: int, args: list):
        self.sendUpdateToAvatarId(avatarId, 'setInteractiveCommands', [eventId, [args]])
