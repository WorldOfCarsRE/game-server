from ai.DistributedObjectAI import DistributedObjectAI
from ai.friends.FriendRequest import FriendRequest
from ai.friends.FriendInfo import FriendInfo

INVRESP_ACCEPTED = 5
INVRESP_DECLINED = 1
INVRESP_ALREADYFRIEND = 4

MAX_FRIENDS = 300

class PlayerFriendsManagerUD(DistributedObjectAI):

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.requests: Dict[int, FriendRequest] = {}

    def avatarOnline(self, racecarId: int, DISLid: int, friendDISLid: int):
        if friendDISLid in self.air.playerTable:
            player = self.air.playerTable[friendDISLid]
            self.updatePlayerFriend(player.getRaceCarId(), DISLid, 0)

        self.updatePlayerFriend(racecarId, friendDISLid, 0)

    def avatarOffline(self, DISLid: int, friendDISLid: int):
        player = self.air.playerTable[friendDISLid]
        self.updatePlayerFriend(player.getRaceCarId(), DISLid, 0)

    def updatePlayerFriend(self, racecarId: int, DISLid: int, newFriend: int):
        self.sendUpdateToAvatar(racecarId, 'updatePlayerFriend', [DISLid, self.createFriendInfo(DISLid), newFriend])

    def createFriendInfo(self, DISLid: int) -> FriendInfo:
        account = self.air.mongoInterface.retrieveFields('accounts', DISLid)

        return FriendInfo(
            onlineYesNo = int(DISLid in self.air.playerTable),
            playerName = account['playToken']
        )

    def addFriendship(self, senderId: int, otherPlayerId: int) -> tuple[bool, int]:
        fields = self.air.mongoInterface.retrieveFields('friends', senderId)
        friends = fields['ourFriends']

        if len(friends) >= MAX_FRIENDS:
            return False, INVRESP_DECLINED

        if otherPlayerId in friends:
            return False, INVRESP_ALREADYFRIEND

        friends.append(otherPlayerId)
        self.air.mongoInterface.updateField('friends', 'ourFriends', senderId, friends)

        return True, INVRESP_ACCEPTED

    def requestInvite(self, senderId: int, otherPlayerId: int, secretYesNo: int):
        print(f'requestInvite - {senderId} - {otherPlayerId} - {secretYesNo}')

        if senderId == otherPlayerId:
            return

        if senderId not in self.air.playerTable:
            return

        if otherPlayerId not in self.air.playerTable:
            return

        ourPlayer = self.air.playerTable[senderId]
        otherPlayer = self.air.playerTable[otherPlayerId]

        if senderId not in self.requests:
            request = FriendRequest(ourPlayer.getRaceCarId(), otherPlayer.getRaceCarId())

            self.requests[senderId] = request
            self.requests[otherPlayerId] = request

            self.sendUpdateToAvatar(otherPlayer.getRaceCarId(), 'invitationFrom', [senderId, otherPlayer.getDISLname()])
            return

        _, status = self.addFriendship(senderId, otherPlayerId)
        self.sendUpdateToAvatar(ourPlayer.doId, 'invitationResponse', [otherPlayerId, status, self.air.context()])
        self.updatePlayerFriend(ownPlayer.getRaceCarId(), otherPlayerId, 1)

        _, theirStatus = self.addFriendship(otherPlayerId, senderId)
        self.sendUpdateToAvatar(otherPlayer.doId, 'invitationResponse', [senderId, theirStatus, self.air.context()])
        self.updatePlayerFriend(otherPlayer.getRaceCarId(), senderId, 1)

        del self.requests[senderId]
        del self.requests[otherPlayerId]
