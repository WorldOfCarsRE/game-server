from direct.directnotify.DirectNotifyGlobal import directNotify
import random
from ai.globals import CogDisguiseGlobals
from ai.battle.BattleGlobals import getInvasionMultiplier
from ai.suit.SuitGlobals import suitDepts
MeritMultiplier = 0.5

class PromotionManagerAI:
    notify = directNotify.newCategory('PromotionManagerAI')

    def __init__(self, air):
        self.air = air

    def getPercentChance(self):
        return 100.0

    def recoverMerits(self, av, cogList, zoneId, multiplier = 1, extraMerits = None):
        avId = av.doId
        meritsRecovered = [0,
         0,
         0,
         0]
        if extraMerits is None:
            extraMerits = [0,
             0,
             0,
             0]
        if self.air.suitInvasionManager.getInvading():
            multiplier *= getInvasionMultiplier()
        for i in range(len(extraMerits)):
            if CogDisguiseGlobals.isSuitComplete(av.getCogParts(), i):
                meritsRecovered[i] += extraMerits[i]
                self.notify.debug(f'recoverMerits: extra merits = {extraMerits[i]}')

        self.notify.debug(f'recoverMerits: multiplier = {multiplier}')
        for cogDict in cogList:
            dept = suitDepts.index(cogDict['track'])
            if avId in cogDict['activeToons']:
                if CogDisguiseGlobals.isSuitComplete(av.getCogParts(), dept):
                    self.notify.debug(f'recoverMerits: checking against cogDict: {cogDict}')
                    rand = random.random() * 100
                    if rand <= self.getPercentChance() and not cogDict['isVirtual']:
                        merits = cogDict['level'] * MeritMultiplier
                        merits = int(round(merits))
                        if cogDict['hasRevives']:
                            merits *= 2
                        merits = merits * multiplier
                        merits = int(round(merits))
                        meritsRecovered[dept] += merits
                        self.notify.debug(f'recoverMerits: merits = {merits}')
                    else:
                        self.notify.debug('recoverMerits: virtual cog!')

        if meritsRecovered != [0,
         0,
         0,
         0]:
            actualCounted = [0,
             0,
             0,
             0]
            merits = av.getCogMerits()
            for i in range(len(meritsRecovered)):
                maxMerits = CogDisguiseGlobals.getTotalMerits(av, i)
                if maxMerits:
                    if merits[i] + meritsRecovered[i] <= maxMerits:
                        actualCounted[i] = meritsRecovered[i]
                        merits[i] += meritsRecovered[i]
                    else:
                        actualCounted[i] = maxMerits - merits[i]
                        merits[i] = maxMerits
                    av.b_setCogMerits(merits)

            if reduce(lambda x, y: x + y, actualCounted):
                meritsTuple = tuple(actualCounted)
                one, two, three, four = meritsTuple[0], meritsTuple[1], meritsTuple[2], meritsTuple[3]

                self.air.writeServerEvent('merits', avId, f'{one}|{two}|{three}|{four}')
                self.notify.debug(f'recoverMerits: av {avId} recovered merits {actualCounted}')
        return meritsRecovered
