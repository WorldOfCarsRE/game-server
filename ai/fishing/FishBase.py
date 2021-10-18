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