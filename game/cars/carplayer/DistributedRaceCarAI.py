from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.directnotify.DirectNotifyGlobal import directNotify

from .CarDNA import CarDNA

# To prevent circular import from CarPlayerAI on runtime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .DistributedCarPlayerAI import DistributedCarPlayerAI

MAX_RACING_POINTS = 1000001

class DistributedRaceCarAI(DistributedObjectAI):
    notify = directNotify.newCategory("DistributedRaceCarAI")
    notify.setDebug(True)

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.dna: CarDNA = None
        self.racingPoints: int = 0
        self.animations: list[int] = []
        self.consumables: list = []
        self.detailings: list[int] = []
        self.activeSponsor: int = 0
        self.player: DistributedCarPlayerAI = None
        self.offAddons: list = []

    def consume(self, usedConsumable) -> None:
        itemId: int = usedConsumable[0]
        consumables: list = self.getConsumables()

        for i, consumable in enumerate(consumables):
            inventoryItemId, quantity = consumable

            if inventoryItemId == itemId:
                if quantity == 1:
                    consumables.pop(i)
                else:
                    consumables[i] = (itemId, quantity - 1)

                self.setConsumables(consumables)
                return

        self.notify.warning(f"Consumable {itemId} not found in inventory")

    def setDNA(self, carDNA: CarDNA):
        if carDNA.validateDNA():
            self.dna = carDNA

    def d_setDNA(self, carDNA: CarDNA):
        if carDNA.validateDNA():
            self.sendUpdate("setDNA", [carDNA])

    def b_setDNA(self, carDNA: CarDNA):
        if carDNA.validateDNA():
            self.setDNA(carDNA)
            self.d_setDNA(carDNA)

    def modifyDNA(self, carName, carNumber, logoBackgroundId, logoBackgroundColor,
                  logoFontId, logoFontColor, gender, chassis, color, eyeColor,
                  wheel, tire, detailing, profileBackgroundId, costumeId,
                  stretches, decalSlots):
        self.modifyAllDNA(carName, carNumber, logoBackgroundId, logoBackgroundColor,
                          logoFontId, logoFontColor, gender, chassis, color, eyeColor,
                          wheel, tire, detailing, profileBackgroundId, costumeId,
                          stretches, decalSlots, self.dna.onAddons, [])

    def modifyAllDNA(self, carName, carNumber, logoBackgroundId, logoBackgroundColor,
                     logoFontId, logoFontColor, gender, chassis, color, eyeColor,
                     wheel, tire, detailing, profileBackgroundId, costumeId,
                     stretches, decalSlots, onAddons, offAddons):
        sender = self.air.getAvatarIdFromSender()

        dna = CarDNA()

        dna.carName = carName
        dna.carNumber = carNumber
        dna.logoBackgroundId = logoBackgroundId
        dna.logoBackgroundColor = logoBackgroundColor
        dna.logoFontId = logoFontId
        dna.logoFontColor = logoFontColor
        dna.gender = gender
        dna.careerType = self.dna.careerType
        dna.chassis = chassis
        dna.color = color
        dna.eyeColor = eyeColor
        dna.wheel = wheel
        dna.tire = tire
        dna.detailing = detailing
        dna.profileBackgroundId = profileBackgroundId
        dna.costumeId = costumeId
        dna.stretches = stretches.copy()
        dna.onAddons = onAddons.copy()
        dna.decalSlots = decalSlots.copy()

        # TODO: offAddons (disabled addons?)

        self.notify.debug(f"modifyDNA: {str(dna)}")

        # TODO: Confirm what can be changed by the client and reject attempt if suspicious.
        if not dna.validateDNA():
            self.notify.warning(f"Player {sender} attempted to modifyDNA with invalid values.  Halting.")
            self.air.writeServerEvent('suspicious', sender, 'modifyDNA: dna.validateDNA() = false')
            return

        # call setDNA for both CarPlayerAI and RaceCarAI
        self.b_setDNA(dna)
        self.player.b_setDNA(dna)

    def setActiveSponsor(self, sponsor: int):
        self.activeSponsor = sponsor

    def d_setActiveSponsor(self, sponsor: int):
        self.sendUpdate("setActiveSponsor", [sponsor])

    def b_setActiveSponsor(self, sponsor: int):
        self.setActiveSponsor(sponsor)
        self.d_setActiveSponsor(sponsor)

    def modifyActiveSponsor(self, sponsor):
        # TODO: Check if sponsorId is valid.
        self.b_setActiveSponsor(sponsor)

    def setRacingPoints(self, racingPoints: int):
        if racingPoints > MAX_RACING_POINTS:
            self.notify.warning(f"Car {self.doId} is over the racing points limit {racingPoints}, capping at {MAX_RACING_POINTS}.")
            self.b_setRacingPoints(MAX_RACING_POINTS)
            return

        self.racingPoints = racingPoints

    def getRacingPoints(self) -> int:
        return self.racingPoints

    def d_setRacingPoints(self, racingPoints: int):
        self.sendUpdate('setRacingPoints', [racingPoints])

    def b_setRacingPoints(self, racingPoints: int):
        self.setRacingPoints(racingPoints)
        self.d_setRacingPoints(racingPoints)

    def addRacingPoints(self, deltaPoints: int) -> int:
        finalAmount = deltaPoints + self.getRacingPoints()

        if finalAmount < MAX_RACING_POINTS:
            self.b_setRacingPoints(finalAmount)
            return 1

        return 9

    def setAnimations(self, animations: list):
        self.animations = animations
        if self.animations == []:
            self.animations = [21001, 21002, 21003, 21004, 21005, 21006, 21007]
            self.d_setAnimations(self.animations)

    def d_setAnimations(self, animations: list):
        self.sendUpdate('setAnimations', [animations])

    def getAnimations(self) -> list:
        return self.animations

    def setConsumables(self, consumables: list):
        self.consumables = consumables
        self.d_setConsumables(self.consumables)

    def d_setConsumables(self, consumables: list):
        self.sendUpdate('setConsumables', [consumables])

    def getConsumables(self) -> list:
        return self.consumables

    def setDetailings(self, detailings: list):
        self.detailings = detailings
        self.d_setDetailings(self.detailings)

    def d_setDetailings(self, detailings: list):
        self.sendUpdate('setDetailings', [detailings])

    def getDetailings(self) -> list:
        return self.detailings
    
    def setOffAddons(self, offAddons: list):
        self.offAddons = offAddons
        self.d_setOffAddons(self.offAddons)

    def d_setOffAddons(self, offAddons: list):
        self.sendUpdate('setOffAddons', [offAddons])

    def getOffAddons(self) -> list:
        return self.offAddons
    
    def modifyAddon(self, itemId: list, unk: list):
        offAddons: list = self.getOffAddons()

        # Unequip
        if itemId == []:
            # TODO: Get the addon inside addonItemList and move it back to offAddon
            pass

        # Equip
        for i, addon in enumerate(offAddons):
            catalogItemId, deformX, deformY, deformY = addon

            if catalogItemId == itemId[0]:
                # TODO: Add addon in addonItemList
                pass
