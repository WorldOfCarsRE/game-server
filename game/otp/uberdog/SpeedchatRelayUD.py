from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.DistributedObjectUD import DistributedObjectUD

class SpeedchatRelayUD(DistributedObjectUD):
    notify = directNotify.newCategory('SpeedchatRelayUD')

    def forwardSpeedchat(self, todo0, todo1, todo2, todo3, todo4, todo5):
        pass
