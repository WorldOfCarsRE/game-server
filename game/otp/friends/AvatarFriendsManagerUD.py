from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.DistributedObjectGlobalUD import DistributedObjectGlobalUD

from game.otp.friends.AvatarFriendInfo import AvatarFriendInfo

class AvatarFriendsManagerUD(DistributedObjectGlobalUD):
    notify = directNotify.newCategory('AvatarFriendsManagerUD')

    def handleFriendOnline(self, avatarId, friendId):
        def handleRetrieve(dclass, fields):
            if not dclass or not fields:
                self.notify.warning(f'Failed to query avatar {friendId}!')
                return

            friendName = fields.get('setName', ('',))[0]

            friend = AvatarFriendInfo(avatarName = friendName, onlineYesNo = 1, playerId = friendId, wlChatEnabledYesNo = 1)
            self.sendUpdateToAvatarId(avatarId, 'updateAvatarFriend', [friendId, friend])

        # Query the avatar.
        self.air.dbInterface.queryObject(self.air.dbId, friendId, handleRetrieve)

    def online(self):
        pass

    def requestInvite(self, todo0):
        pass

    def friendConsidering(self, todo0):
        pass

    def invitationFrom(self, todo0, todo1):
        pass

    def retractInvite(self, todo0):
        pass

    def rejectInvite(self, todo0, todo1):
        pass

    def requestRemove(self, todo0):
        pass

    def rejectRemove(self, todo0, todo1):
        pass

    def updateAvatarFriend(self, todo0, todo1):
        pass

    def removeAvatarFriend(self, todo0):
        pass

    def updateAvatarName(self, todo0, todo1):
        pass

    def avatarOnline(self, todo0, todo1, todo2, todo3, todo4, todo5, todo6):
        pass

    def avatarOffline(self, todo0):
        pass