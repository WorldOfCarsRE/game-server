from ai.suit.SuitGlobals import suitDepts, suitsPerDept, SuitHeads
from ai.suit import CogPageGlobals

class CogPageManagerAI:
    def __init__(self, air):
        self.air = air

    def toonKilledCogs(self, toon, killedCogs, zoneId):
        cogCounts = toon.getCogCount()
        cogs = toon.getCogStatus()

        for cog in killedCogs:
            if toon.doId in cog['activeToons']:
                deptIndex = suitDepts.index(cog['track'])
                if toon.getBuildingRadar()[deptIndex] == 1:
                    continue

                cogIndex = SuitHeads.at(cog['type'])
                buildingQuota = CogPageGlobals.COG_QUOTAS[1][cogIndex % suitsPerDept]
                cogQuota = CogPageGlobals.COG_QUOTAS[0][cogIndex % suitsPerDept]
                if cogCounts[cogIndex] >= buildingQuota:
                    return

                cogCounts[cogIndex] += 1
                if cogCounts[cogIndex] < cogQuota:
                    cogs[cogIndex] = CogPageGlobals.COG_DEFEATED
                elif cogQuota <= cogCounts[cogIndex] < buildingQuota:
                    cogs[cogIndex] = CogPageGlobals.COG_COMPLETE1
                else:
                    cogs[cogIndex] = CogPageGlobals.COG_COMPLETE2

        toon.b_setCogCount(cogCounts)
        toon.b_setCogStatus(cogs)
        newCogRadar = toon.getCogRadar()
        newBuildingRadar = toon.getBuildingRadar()

        for dept in range(len(suitDepts)):
            if newBuildingRadar[dept] == 1:
                continue
            cogRadar = 1
            buildingRadar = 1
            for cog in range(suitsPerDept):
                status = toon.getCogStatus()[dept * suitsPerDept + cog]
                if status != CogPageGlobals.COG_COMPLETE2:
                    buildingRadar = 0
                if status != CogPageGlobals.COG_COMPLETE1 or status != CogPageGlobals.COG_COMPLETE2:
                    cogRadar = 0
            newCogRadar[dept] = cogRadar
            newBuildingRadar[dept] = buildingRadar

        toon.b_setCogRadar(newCogRadar)
        toon.b_setBuildingRadar(newBuildingRadar)

    def toonEncounteredCogs(self, toon, encounteredCogs, zoneId):
        cogs = toon.getCogStatus()

        for cog in encounteredCogs:
            if toon.doId in cog['activeToons']:
                cogIndex = SuitHeads.at(cog['type'])
                if cogs[cogIndex] == CogPageGlobals.COG_UNSEEN:
                    cogs[cogIndex] = CogPageGlobals.COG_BATTLED

        toon.b_setCogStatus(cogs)