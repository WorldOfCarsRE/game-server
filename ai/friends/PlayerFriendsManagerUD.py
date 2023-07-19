from ai.DistributedObjectAI import DistributedObjectAI

INVRESP_ACCEPTED = 5
INVRESP_DECLINED = 1
INVRESP_ALREADYFRIEND = 4

MAX_FRIENDS = 300

class PlayerFriendsManagerUD(DistributedObjectAI):

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

    def requestInvite(self, senderId: int, otherPlayerId: int, secretYesNo: int):
        print(f'requestInvite - {senderId} - {otherPlayerId} - {secretYesNo}')

        accData = self.air.mongoInterface.retrieveFields('accounts', otherPlayerId)

        self.sendUpdateToAvatar(accData['racecarId'], 'invitationFrom', [senderId, accData['playToken']])
