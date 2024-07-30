from direct.directnotify.DirectNotifyGlobal import directNotify
from threading import Thread
import requests

class Webhook:
    notify = directNotify.newCategory('Webhook')

    def __init__(self):
        self.title = ''
        self.description = ''
        self.color = 0
        self.fields = []
        self.webhook = ''
        self.requestType = ''

    def setRequestType(self, requestType):
        self.requestType = requestType

    def setTitle(self, title):
        self.title = title

    def getTitle(self):
        return self.title

    def setDescription(self, description):
        self.description = description

    def getDescription(self):
        return self.description

    def setColor(self, color):
        self.color = color

    def getColor(self):
        return self.color

    def setFields(self, fields):
        self.fields = fields

    def getFields(self):
        return self.fields

    def setWebhook(self, webhook):
        self.webhook = webhook

    def getWebhook(self):
        return self.webhook

    def send(self, data):
        request = getattr(requests, self.requestType)(self.getWebhook(), json = data)

        if request.status_code == 204:
            self.notify.info('Successfully sent webhook!')

    def finalize(self):
        data = {}

        data['embeds'] = []
        embed = {}

        embed['title'] = self.getTitle()
        embed['description'] = self.getDescription()
        embed['color'] = self.getColor()

        embed['fields'] = self.getFields()

        data['embeds'].append(embed)

        Thread(target = self.send, args = (data,)).start()
