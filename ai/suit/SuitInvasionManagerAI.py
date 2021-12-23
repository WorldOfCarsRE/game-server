from direct.directnotify.DirectNotifyGlobal import directNotify

class SuitInvasionManagerAI:
    notify = directNotify.newCategory('SuitInvasionManagerAI')

    def __init__(self, air):
        self.air = air

    def getInvadingCog(self):
        return None, 0

    def getInvading(self):
        return False