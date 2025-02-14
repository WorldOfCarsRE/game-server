from direct.directnotify.DirectNotifyGlobal import directNotify
from game.cars.lobby.DistributedLobbyUD import DistributedLobbyUD
from game.cars.lobby.DistributedTutorialLobbyContextUD import DistributedTutorialLobbyContextUD
from game.cars.distributed.CarsGlobals import *

class DistributedTutorialLobbyUD(DistributedLobbyUD):
    notify = directNotify.newCategory("DistributedTutorialLobbyUD")

    def __init__(self, air):
        DistributedLobbyUD.__init__(self, air)
        self.dungeonItemId = 1000
        self.zoneContext = 0

    def join(self):
        avatarId = self.air.getAvatarIdFromSender()
        print("join", avatarId)

        def gotAvatarLocation(doId, parentId, zoneId):
            if avatarId != doId:
                self.notify.warning(f"Got unexpected location for doId {doId}, was expecting {avatarId}!")
                return

            # Get the AI channel of the avatar's shard:
            shardChannel = self.air.shardManager.getShardChannel(parentId)
            if not shardChannel:
                self.notify.warning(f"No shardChannel")
                return

            self.zoneContext += 1

            lobbyContext = DistributedTutorialLobbyContextUD(self.air)
            lobbyContext.lobby = self
            lobbyContext.playersInContext.append(avatarId)
            lobbyContext.generateOtpObject(self.doId, self.zoneContext)
            self.sendUpdateToAvatarId(avatarId, 'gotoLobbyContext', [self.zoneContext])

            def gotDungeon(doId, parentId, zoneId):
                lobbyContext.b_setGotoDungeon(parentId, zoneId)

            self.air.remoteGenerateDungeon(shardChannel, DUNGEON_TYPE_TUTORIAL, self.doId, lobbyContext.doId, [avatarId], gotDungeon)

        self.air.getObjectLocation(avatarId, gotAvatarLocation)
