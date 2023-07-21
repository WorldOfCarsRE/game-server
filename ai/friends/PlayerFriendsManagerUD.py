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

    def avatarOnline(self, DISLid: int, racecarId: int):
        fields = self.air.mongoInterface.retrieveFields('friends', DISLid)

        if fields:
            for friendDISLid in fields['ourFriends']:
                friendInfo = FriendInfo(
                    onlineYesNo = friendDISLid in self.air.playerTable,
                    playerName = '???' # TODO: Grab from database
                )

                self.sendUpdateToAvatar(racecarId, 'updatePlayerFriend', [friendDISLid, friendInfo, 0])

    def addFriendship(self, senderId: int, otherPlayerId: int) -> tuple[bool, int]:
        fields = self.air.mongoInterface.retrieveFields('friends', senderId)

        if fields:
            friends = fields['ourFriends']

            if len(friends) >= MAX_FRIENDS:
                return False, INVRESP_DECLINED

            if otherPlayerId in friends:
                return False, INVRESP_ALREADYFRIEND

            friends.append(otherPlayerId)
            self.air.mongoInterface.updateField('friends', 'ourFriends', senderId, friends)
        else:
            # Create us a brand new friends list
            self.air.mongoInterface.mongodb.friends.insert_one(
                {
                    '_id': senderId,
                    'ourFriends': [otherPlayerId]
                }
            )

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

        _, theirStatus = self.addFriendship(otherPlayerId, senderId)
        self.sendUpdateToAvatar(otherPlayer.doId, 'invitationResponse', [senderId, theirStatus, self.air.context()])

        del self.requests[senderId]
        del self.requests[otherPlayerId]
