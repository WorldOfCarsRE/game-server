import math

from typing import List

from .DistributedCarAvatarAI import DistributedCarAvatarAI
from game.cars.zone import ZoneConstants

from .DistributedRaceCarAI import DistributedRaceCarAI

BUY_RESP_CODE_SUCCESS = 0
BUY_RESP_CODE_ALREADY_OWNED = 1
BUY_RESP_CODE_INVALID_STORE_ITEM = 4
BUY_RESP_CODE_NOT_ENOUGH_CARCOIN = 8
BUY_RESP_CODE_NOT_PURCHASEABLE = 12

class DistributedCarPlayerAI(DistributedCarAvatarAI):
    def __init__(self, air):
        DistributedCarAvatarAI.__init__(self, air)
        self.DISLname = ''
        self.DISLid = 0
        self.carCoins = 0
        self.carCount = 0
        self.racecarId = 0
        self.racecar: DistributedRaceCarAI = None

    def buyItemRequest(self, shopId: int, itemId: int) -> None:
        item: None | dict = self.air.getShopItem(str(shopId), itemId)

        if item is None:
            self.d_buyItemResponse(itemId, BUY_RESP_CODE_INVALID_STORE_ITEM)
            return

        if not self.takeCoins(item["storePrice"]):
            self.d_buyItemResponse(itemId, BUY_RESP_CODE_NOT_ENOUGH_CARCOIN)
            return

        itemType: str = item["storeThumbnail"].split("_")[3]

        if itemType == "cns":
            # Consumable
            self.handleConsumablePurchase(item, itemId)

        elif itemType == "pjb":
            # PaintJob
            self.handlePaintJobPurchase(item, itemId)

        self.d_buyItemResponse(itemId, BUY_RESP_CODE_SUCCESS)

    def handleConsumablePurchase(self, item: dict, itemId: int) -> None:
        consumableInInventory: bool = False

        consumables: list = self.racecar.getConsumables()

        for i, consumable in enumerate(consumables):
            inventoryItemId, quantity = consumable

            if inventoryItemId == itemId:
                consumableInInventory: bool = True

                if quantity >= item["maximumOwnable"]:
                    self.d_buyItemResponse(itemId, BUY_RESP_CODE_NOT_PURCHASEABLE)
                    return

                consumables[i] = (itemId, quantity + 1)

            if not consumableInInventory:
                consumables.append((itemId, 1))

        self.racecar.setConsumables(consumables)

    def handlePaintJobPurchase(self, item: dict, itemId: int) -> None:
        detailings: list = self.racecar.getDetailings()

        if itemId in detailings:
            self.d_buyItemResponse(itemId, BUY_RESP_CODE_ALREADY_OWNED)
            return

        detailings.append(itemId)

        self.racecar.setDetailings(detailings)

    def d_buyItemResponse(self, itemId: int, returnCode: int) -> None:
        self.sendUpdateToAvatarId(self.doId, 'buyItemResponse', [itemId, returnCode])

    def setCars(self, carCount: int, cars: list):
        self.carCount = carCount
        self.racecarId = cars[0]

        if self.racecarId:
            # Retrieve their DistributedRaceCar object.
            self.racecar = self.air.readRaceCar(self.racecarId)

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
