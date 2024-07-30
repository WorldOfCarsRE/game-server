from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.DistributedObjectGlobalUD import DistributedObjectGlobalUD

from game.otp.server.ServerBase import ServerBase
from game.otp.discord.Webhook import Webhook
from game.otp.server.ServerGlobals import WORLD_OF_CARS_ONLINE

import json

class CentralLoggerUD(DistributedObjectGlobalUD, ServerBase):
    notify = directNotify.newCategory('CentralLoggerUD')

    def __init__(self, air):
        DistributedObjectGlobalUD.__init__(self, air)
        ServerBase.__init__(self)

    def getCategory(self, category):
        if category == 'MODERATION_FOUL_LANGUAGE':
            return 'Foul Language'
        elif category == 'MODERATION_PERSONAL_INFO':
            return 'Personal Information'
        elif category == 'MODERATION_RUDE_BEHAVIOR':
            return 'Rude Behavior'
        elif category == 'MODERATION_BAD_NAME':
            return 'Bad Name'
        elif category == 'MODERATION_HACKING':
            return 'Hacking'
        else:
            return 'Unknown Category'

    def sendMessage(self, category, message, targetDISLid, targetAvId):
        self.notify.debug('Received message from client')

        parts = message.split('|')
        msgType = parts[0]

        fields = {
            'targetDISLid': targetDISLid,
            'targetAvId': targetAvId
        }

        if msgType == 'GUEST_FEEDBACK':
            fields['feedbackCategory'] = parts[1]
            fields['feedbackMessage'] = parts[2]

        if self.notify.getDebug():
            print(msgType)

            event = {
                'category': category,
                'message': message,
                'type': msgType,
            }
            event.update(fields)

            data = json.dumps(event)
            print(data)

        if self.isProdServer():
            category = self.getCategory(category)

            # Report this to our Discord channel.
            hookFields = [{
                'name': 'Message',
                'value': message,
                'inline': True
            },
            {
                'name': 'Category',
                'value': category,
                'inline': True
            },
            {
                'name': 'Target Avatar Id',
                'value': targetAvId,
                'inline': True
            },
            {
                'name': 'Sender Avatar Id',
                'value': self.air.getAvatarIdFromSender(),
                'inline': True
            },
            {
                'name': 'Server Type',
                'value': WORLD_OF_CARS_ONLINE,
                'inline': True
            }]

            if category != 'Unknown Category':
                messageObj = Webhook()
                messageObj.setRequestType('post')
                messageObj.setDescription('Someone is reporting to us!')
                messageObj.setFields(hookFields)
                messageObj.setColor(1127128)
                messageObj.setWebhook(config.GetString('discord-reports-webhook'))
                messageObj.finalize()

        self.air.writeServerEvent(category, messageType = msgType, message = message, **fields)

    def logAIGarbage(self):
        pass
