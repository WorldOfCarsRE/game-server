from ai.fishing.FishValueScales import *
import math

class FishBase:
    __slots__ = 'genus', 'species', 'weight'

    def __init__(self, genus, species, weight):
        self.genus = genus
        self.species = species
        self.weight = weight

    def getGenus(self):
        return self.genus

    def getSpecies(self):
        return self.species

    def getWeight(self):
        return self.weight

    def getVitals(self):
        return (
            self.getGenus(),
            self.getSpecies(),
            self.getWeight()
        )
        
    def getValue(self):
        rarity = simbase.air.getFishes()[self.getGenus()][self.getSpecies()].rarity
        rarityValue = math.pow(RARITY_VALUE_SCALE * rarity, 1.5)
        weightValue = math.pow(WEIGHT_VALUE_SCALE * self.getWeight(), 1.1)
        value = OVERALL_VALUE_SCALE * (rarityValue + weightValue)
        finalValue = int(math.ceil(value))
        # TODO: holiday stuff
        return finalValue