import math
from typing import List

from .DistributedCarAvatarAI import DistributedCarAvatarAI
from game.cars.zone import ZoneConstants

from .DistributedRaceCarAI import DistributedRaceCarAI
from .CarDNA import CarDNA

BUY_RESP_CODE_SUCCESS = 0
BUY_RESP_CODE_ALREADY_OWNED = 1
BUY_RESP_CODE_INVALID_STORE_ITEM = 4
BUY_RESP_CODE_NOT_ENOUGH_CARCOIN = 8
BUY_RESP_CODE_NOT_PURCHASEABLE = 12

DEDUCT_COINS_EVENT_ID = 10008

class DistributedCarPlayerAI(DistributedCarAvatarAI):
    def __init__(self, air):
        DistributedCarAvatarAI.__init__(self, air)
        self.DISLname = ''
        self.DISLid = 0
        self.carCoins = 0
        self.carCount = 0
        self.racecarId = 0
        self.yardStocks: list = []
        self.racecar: DistributedRaceCarAI = None
        self.dna: CarDNA = None
        self.activeQuests: list = []
        self.badges: list = []

    def buyItemRequest(self, shopId: int, itemId: int) -> None:
        item: None | dict = self.air.getShopItem(str(shopId), itemId)

        if item is None:
            self.d_buyItemResponse(itemId, BUY_RESP_CODE_INVALID_STORE_ITEM)
            return

        if not self.takeCoins(item["storePrice"]):
            self.d_buyItemResponse(itemId, BUY_RESP_CODE_NOT_ENOUGH_CARCOIN)
            return

        itemType: str = item["storeThumbnail"].split("_")[3]

        if itemType in ("spo", "tlp", "exh", "eng", "orn", "hat"):
            # Addon
            self.handleAddonPurchase(itemId)

        if itemType in ("cns", "ger"):
            # Consumable
            quantity = 1

            if itemType == "ger":
                itemId, quantity = item["stackItemId"], item["quantity"]

            self.handleConsumablePurchase(item, itemId, quantity)

        elif itemType == "pjb":
            # PaintJob
            self.handlePaintJobPurchase(itemId)

        elif itemType == "yar":
            # Yard
            self.handleYardPurchase(item, itemId)

        self.d_buyItemResponse(itemId, BUY_RESP_CODE_SUCCESS)

    def handleAddonPurchase(self, itemId: int) -> None:
        offAddons: list = self.racecar.getOffAddons()

        # We also need to check in addonItemList (Equipped addon)
        for i, addon in enumerate(offAddons):
            catalogItemId, deformX, deformY, deformY = addon

            if catalogItemId == itemId[0]:
                self.d_buyItemResponse(itemId, BUY_RESP_CODE_ALREADY_OWNED)
                return

        offAddons.append((itemId, 0, 0, 0))

        self.racecar.setOffAddons(offAddons)

    def handleConsumablePurchase(self, item: dict, itemId: int, count: int) -> None:
        consumableInInventory: bool = False

        consumables: list = self.racecar.getConsumables()

        for i, consumable in enumerate(consumables):
            inventoryItemId, quantity = consumable

            if inventoryItemId == itemId:
                consumableInInventory: bool = True

                if quantity >= item["maximumOwnable"]:
                    self.d_buyItemResponse(itemId, BUY_RESP_CODE_NOT_PURCHASEABLE)
                    return

                consumables[i] = (itemId, quantity + count)

        if not consumableInInventory:
            consumables.append((itemId, count))

        self.racecar.setConsumables(consumables)

    def handlePaintJobPurchase(self, itemId: int) -> None:
        detailings: list = self.racecar.getDetailings()

        if itemId in detailings:
            self.d_buyItemResponse(itemId, BUY_RESP_CODE_ALREADY_OWNED)
            return

        detailings.append(itemId)

        self.racecar.setDetailings(detailings)

    def handleYardPurchase(self, item: dict, itemId: int) -> None:
        itemInInventory: bool = False

        yardStocks: list = self.getYardStocks()

        for i, yardItem in enumerate(yardStocks):
            catalogItemId, quantity, usedQuantity = yardItem

            if catalogItemId == itemId:
                itemInInventory: bool = True

                if quantity >= item["maximumOwnable"]:
                    self.d_buyItemResponse(itemId, BUY_RESP_CODE_NOT_PURCHASEABLE)
                    return

                yardStocks[i] = (itemId, quantity + 1, usedQuantity)

        if not itemInInventory:
            yardStocks.append((itemId, 1, 0))

        self.setYardStocks(yardStocks)

    def d_buyItemResponse(self, itemId: int, responseCode: int) -> None:
        self.sendUpdateToAvatarId(self.doId, 'buyItemResponse', [itemId, responseCode])

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

    def setCars(self, carCount: int, cars: list):
        self.carCount = carCount
        self.racecarId = cars[0]

        if self.racecarId:
            # Retrieve their DistributedRaceCar object.
            def callback(dbo, retCode):
                if retCode == 0:
                    self.racecar = dbo.do
                    self.racecar.player = self
                    if self.racecarId not in self.air.doId2do:
                        self.air.addDOToTables(dbo.do, (self.parentId, 0))

                        # Call the local generate methods to prevent a warning on delete
                        dbo.do.generate()
                        dbo.do.announceGenerate()
                        dbo.do.postGenerateMessage()

                        self.air.setAIReceiver(self.racecarId)

            self.acceptOnce(self.taskName("getRaceCar"), callback)
            self.air.readRaceCar(self.racecarId, doneEvent = self.taskName("getRaceCar"))

    def getRaceCarId(self) -> int:
        return self.racecarId

    def setDISLname(self, DISLname: str):
        self.DISLname = DISLname

    def getDISLname(self) -> str:
        return self.DISLname

    def setDISLid(self, DISLid: int) -> int:
        self.DISLid = DISLid

    def getDISLid(self) -> int:
        return self.DISLid

    def setCarCoins(self, carCoins: int):
        self.carCoins = carCoins

    def getCarCoins(self) -> int:
        return self.carCoins

    def d_setCarCoins(self, carCoins: int):
        self.sendUpdate('setCarCoins', [carCoins])

    def b_setCarCoins(self, carCoins: int):
        self.setCarCoins(carCoins)
        self.d_setCarCoins(carCoins)

    def announceGenerate(self):
        self.air.sendFriendManagerAccountOnline(self.DISLid)

        self.sendUpdateToAvatarId(self.doId, 'setRuleStates', [[[100, 1, 1, 1]]]) # To skip the tutorial, remove me to go to tutorial.
        self.sendUpdateToAvatarId(self.doId, 'generateComplete', [])

        self.air.incrementPopulation()

        # Fill in the missing information from the database (i.e. coins)
        self.air.fillInCarsPlayer(self)

    def delete(self):
        # TODO: Set a post-remove message in case of an AI crash.
        self.air.sendFriendManagerAccountOffline(self.DISLid)

        self.air.decrementPopulation()

        DistributedCarAvatarAI.delete(self)

    def sendEventLog(self, event: str, params: list, args: list):
        self.air.writeServerEvent(event, self.doId, f'{params}:{args}')

    def persistRequest(self, context: int):
        self.sendUpdateToAvatarId(self.doId, 'persistResponse', [context, 1])

    def invokeRuleRequest(self, eventId: int, rules: list, context: int):
        print(f'invokeRuleRequest - {eventId} - {rules} - {context}')

        if eventId in ZoneConstants.MINIGAMES:
            if eventId == ZoneConstants.PAINT_BLASTER:
                coins = 100 * len(rules)
            elif eventId == ZoneConstants.LIGHTNING_STORM:
                coins = sum(rules[1::2])
            elif eventId == ZoneConstants.FILLMORES_FUEL_MIXIN_AREA_MAN:
                coins = 10
            elif eventId == ZoneConstants.DOCS_CLINIC:
                coins = math.ceil(rules[1] / 20)
            elif eventId == ZoneConstants.LUIGIS_CASA_DELLA_TIRES:
                coins = math.ceil(rules[1] / 2)
            elif eventId == ZoneConstants.MATERS_SLING_SHOOT:
                coins = math.ceil(rules[1] / 5)

            rules = [coins]

            self.addCoins(coins)
        elif eventId == DEDUCT_COINS_EVENT_ID:
            self.takeCoins(rules[0])

        self.d_invokeRuleResponse(eventId, rules, context)

    def d_invokeRuleResponse(self, eventId: int, rules: List[int], context: int):
        self.sendUpdateToAvatarId(self.doId, 'invokeRuleResponse', [eventId, rules, context])

    def addCoins(self, deltaCoins: int):
        self.b_setCarCoins(deltaCoins + self.getCarCoins())

    def takeCoins(self, deltaCoins: int) -> bool:
        totalCoins = self.carCoins

        if deltaCoins > totalCoins:
            return False

        self.b_setCarCoins(self.carCoins - deltaCoins)

        return True

    def d_showDialogs(self, dialogId: int, args: List[str]):
        self.sendUpdateToAvatarId(self.doId, 'showDialogs', [[[dialogId, args]]])

    def d_setYardStocks(self, yardStocks: list) -> None:
        self.sendUpdate('setYardStocks', [yardStocks])

    def setYardStocks(self, yardStocks: list) -> None:
        self.yardStocks = yardStocks
        self.d_setYardStocks(self.yardStocks)

    def getYardStocks(self) -> list:
        return self.yardStocks

    def setActiveQuests(self, activeQuests: list):
        self.activeQuests = activeQuests
        self.d_setActiveQuests(activeQuests)
 
    def getActiveQuests(self) -> list:
        return self.activeQuests
 
    def d_setActiveQuests(self, activeQuests: list):
        self.sendUpdate('setActiveQuests', [activeQuests])

    def setBadges(self, badges: list):
        self.badges = badges
        self.d_setBadges(badges)
 
    def getBadges(self) -> list:
        return self.badges
 
    def d_setBadges(self, badges: list):
        self.sendUpdate('setBadges', [badges])