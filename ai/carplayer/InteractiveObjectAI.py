from .DistributedCarAvatarAI import DistributedCarAvatarAI

TYPE_NPC = 0

# Interation types
COMMAND_OFFER_QUERY_INTERACTIONS = 1

class InteractiveObjectAI(DistributedCarAvatarAI):
    def __init__(self, air):
        DistributedCarAvatarAI.__init__(self, air)
        self.name = ''
        self.assetId = 0
        self.objType = TYPE_NPC
        self.globalState = 0
        self.visible = 1

    def getName(self):
        return self.name

    def getAssetId(self):
        return self.assetId

    def getType(self):
        return self.objType

    def getGlobalState(self):
        return self.globalState

    def getVisible(self):
        return self.visible

    def getClientScript(self):
        return 'scripts/interactive/default_npc_no_physics.lua'
