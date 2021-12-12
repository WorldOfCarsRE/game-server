from ai.house.DistributedFurnitureItemAI import DistributedFurnitureItemAI
from ai import ToontownGlobals
from ai.catalog import CatalogItem
from ai.toon import ToonDNA

PHONE_MOVIE_CLEAR = 2
PHONE_MOVIE_EMPTY = 3
PHONE_MOVIE_PICKUP = 4
PHONE_MOVIE_HANGUP = 5

class DistributedPhoneAI(DistributedFurnitureItemAI):
    defaultScale = 0.75

    def __init__(self, air, furnitureMgr, item):
        DistributedFurnitureItemAI.__init__(self, air, furnitureMgr, item)

        self.av = None
        self.busy = 0

        self.furnitureMgr = furnitureMgr

        # Figure out the initial scale of the phone. If the owner is
        # around, it will be scaled to match the owner; otherwise, it
        # will just be a default scale.
        scale = self.defaultScale
        ownerId = self.furnitureMgr.house.avId
        owner = self.air.doTable.get(ownerId)

        if owner:
            animalStyle = owner.dna.getAnimal()
            scale = ToonDNA.toonBodyScales[animalStyle]

        self.initialScale = (scale, scale, scale)

    def setInitialScale(self):
        pass

    def getInitialScale(self):
        return self.initialScale

    def setNewScale(self, sx, sy, sz):
        # A client, presumably the avatar at the phone, is telling us
        # what scale the phone will be if anyone asks.
        avId = self.air.currentAvatarSender

        # Sanity check the parameters; ignore requests from unexpected
        # clients or unreasonable scales.
        if self.busy == avId:
            if (sx >= 0.25 or sy >= 0.25 or sz >= 0.25):
                # If it passes, store it.
                self.initialScale = (sx, sy, sz)
                self.sendUpdate('setInitialScale', [sx, sy, sz])

    def getNewScale(self):
        return self.initialScale

    def freeAvatar(self, avId):
        # Free this avatar, probably because he requested interaction while
        # I was busy. This can happen when two avatars request interaction
        # at the same time. The AI will accept the first, sending a setMovie,
        # and free the second
        self.sendUpdateToAvatar(avId, 'freeAvatar', [])
        return

    def avatarEnter(self):
        avId = self.air.currentAvatarSender

        # If we are busy, free this new avatar
        if self.busy:
            self.freeAvatar(avId)
            return

        # Fetch the actual avatar object
        av = self.air.doTable.get(avId)

        if not av:
            return

        # Flag us as busy with this avatar Id
        self.busy = avId
        self.av = av

        # Handle unexpected exit
        self.acceptOnce(self.air.getDeleteDoIdEvent(avId), self.__handleUnexpectedExit, extraArgs = [avId])
        self.acceptOnce(f'bootAvFromEstate-{str(avId)}', self.__handleBootMessage, extraArgs = [avId])

        # Update the quest manager. Yes, there are phone quests.
        self.air.questManager.toonUsedPhone(self.av)

        # We don't care who the owner of the phone is--anyone can use
        # any phone.
        if len(av.weeklyCatalog) + len(av.monthlyCatalog) + len(av.backCatalog) != 0:
            self.lookupHouse()
        else:
            # No catalog yet.
            self.d_setMovie(PHONE_MOVIE_EMPTY, avId)
            self.sendClearMovie()

    def lookupHouse(self):
        # Looks up the avatar's house information so we can figure out
        # how much stuff is in the attic.  We need to tell this
        # information to the client so it can warn the user if he's in
        # danger of overfilling it.

        if not self.av.houseId:
            self.sendCatalog(0)
            return

        # Maybe the house is already instantiated. This will be true
        # when the avatar is calling from his own house, for instance.
        house = self.air.doTable.get(self.av.houseId)

        if house:
            numAtticItems = len(house.atticItems) + len(house.atticWallpaper) + len(house.atticWindows)
            numHouseItems = numAtticItems + len(house.interiorItems)
            self.sendCatalog(numHouseItems)
            return

    def sendCatalog(self, numHouseItems):
        # Send the setMovie command to the user to tell him to open up
        # his catalog. But first, tell him how much stuff he's got in
        # his house.
        self.sendUpdateToAvatar(self.av.doId, 'setLimits', [numHouseItems])

        # Now open the catalog up on the client.
        self.d_setMovie(PHONE_MOVIE_PICKUP, self.av.doId)

        # The avatar has seen his catalog now.
        if self.av.catalogNotify == ToontownGlobals.NewItems:
            self.av.b_setCatalogNotify(ToontownGlobals.OldItems, self.av.mailboxNotify)

    def avatarExit(self):
        avId = self.air.currentAvatarSender

        if self.busy == avId:
            self.d_setMovie(PHONE_MOVIE_HANGUP, self.av.doId)
            self.sendClearMovie()
        else:
            self.freeAvatar(avId)

    def __handleUnexpectedExit(self, avId):
        self.sendClearMovie()

    def __handleBootMessage(self, avId):
        self.sendClearMovie()

    def sendClearMovie(self):
        # Ignore unexpected exits on whoever I was busy with
        self.ignoreAll()
        self.busy = 0
        self.av = None
        self.d_setMovie(PHONE_MOVIE_CLEAR, 0)

    def d_setMovie(self, mode, avId):
        timestamp = globalClockDelta.getRealNetworkTime(bits = 32)
        self.sendUpdate('setMovie', [mode, avId, timestamp])

    def requestPurchaseMessage(self, context, blob, optional):
        # Sent from the client code to request a particular purchase item.
        avId = self.air.currentAvatarSender

        item = CatalogItem.getItem(blob, store = CatalogItem.Customization)

        if self.busy != avId:
            retcode = ToontownGlobals.P_NotShopping
        else:
            # The user is requesting purchase of one particular item.
            retcode = self.air.catalogManager.purchaseItem(self.av, item, optional)

        self.sendUpdateToAvatar(avId, 'requestPurchaseResponse', [context, retcode])