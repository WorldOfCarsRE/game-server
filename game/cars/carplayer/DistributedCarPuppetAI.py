from panda3d.core import ConfigVariableString
from direct.directnotify import DirectNotifyGlobal
from direct.distributed.PyDatagram import PyDatagram
from .DistributedCarGMAI import DistributedCarGMAI
from .DistributedCarPlayerAI import DistributedCarPlayerAI
from game.otp.ai import AIMsgTypes
import requests

CLIENT_GO_GET_LOST_RESP = 4 # Sent by the server when it is dropping the connection deliberately.

LOGOUT_REASON_ACCOUNT_DISABLED = 152

CLIENT_SYSTEM_ALERT = 78
CLIENT_SYSTEM_ALERT_WITHRESP = 123

class DistributedCarPuppetAI(DistributedCarGMAI):
    notify = DirectNotifyGlobal.directNotify.newCategory("DistributedCarPuppetAI")
    notify.setInfo(True)

    def __init__(self, air):
        DistributedCarGMAI.__init__(self, air)

    def verifyAccess(self, avatarId: int) -> bool:
        # We use this function to verify that we actally have access to GM functionality.
        # Someone might manage to generate the GM object wiht a normal account somehow, should be impossible, but it could always happen somehow, (CarsClient error or something)
        # TODO: Account access levels implementation?
        avatar: self = self.air.getDo(avatarId)

        if self.air.isProdServer() and avatar.getDISLid() not in self.air.staffMembers:
            dg = PyDatagram()
            dg.addServerHeader(self.GetPuppetConnectionChannel(avatarId), 0, AIMsgTypes.CLIENTAGENT_EJECT)
            dg.addUint16(126)
            dg.addString("You are not authorized to use administrator privileges.")
            self.air.send(dg)
            return False

        return True

    def warnPlayer(self, playerId: int, context: int) -> None:
        if self.verifyAccess(self.air.getAvatarIdFromSender()):
            # Prepare the client message.
            clientMsg = PyDatagram()
            clientMsg.addUint16(CLIENT_SYSTEM_ALERT_WITHRESP)
            clientMsg.addString("You have been warned by a staff member.")
            self.sendMessage(playerId, clientMsg)

    def banPlayer(self, playerId: int, context: int) -> None:
        if self.verifyAccess(self.air.getAvatarIdFromSender()):
            # Prepare the client message.
            clientMsg = PyDatagram()
            clientMsg.addUint16(CLIENT_GO_GET_LOST_RESP)
            clientMsg.addUint16(LOGOUT_REASON_ACCOUNT_DISABLED)
            clientMsg.addString("There has been a reported violation of our Terms of Use connected to this account. For safety purposes, we have placed a temporary hold on the account.  For more details, please review the messages sent to the email address associated with this account.")
            self.sendMessage(playerId, clientMsg)

            player: DistributedCarPlayerAI = self.air.getDo(playerId)

            if self.air.isProdServer() and player:
                # Ban the player.
                self.banAccount(player.getDISLname(), "Breaking rules.")

    def sendMessage(self, playerId: int, clientMsg: PyDatagram) -> None:
        # Send it.
        dg = PyDatagram()
        dg.addServerHeader(self.GetPuppetConnectionChannel(playerId), 0, AIMsgTypes.CLIENT_AGENT_SEND_DATAGRAM)
        dg.addBlob(clientMsg.getMessage())
        self.air.send(dg)

    def banAccount(self, playToken: str, reason: str) -> None:
        self.notify.info(f"Attempting to ban {playToken} for reason: {reason}")

        try:
            response = requests.post("https://toontastic.sunrise.games/bans/BanAccount.php", {
                "username": playToken,
                "banReason": reason,
                "secretKey": ConfigVariableString("api-token", "0").getValue()
            }, headers={
                "User-Agent": "Sunrise Games - DistributedCarGMAI"
            })
            self.notify.info(f"Got response from API: {response.text}")
        except:
            self.notify.warning("Failed to ban account.")
