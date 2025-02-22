FIRST_VALID_GENDER: int = 0
NUM_VALID_GENDERS: int = 2

CHASSIS_TYPE_INVALID: int = 0
COLOR_TYPE_INVALID:int = 0
EYES_TYPE_INVALID:int = 0
WHEELS_TYPE_INVALID:int = 0
TIRES_TYPE_INVALID:int = 0

NUM_STRETCHES:int = 6
NUM_DECAL_SLOTS:int = 16

class CarDNA:
    def __init__(self):
        self.carName: str = ""
        self.carNumber: int = 0
        self.logoBackgroundId: int = 0
        self.logoBackgroundColor: int = 0
        self.logoFontId: int = 0
        self.logoFontColor: int = 0
        self.gender: int = 0
        self.careerType: int = 0
        self.chassis: int = 0
        self.color: int = 0
        self.eyeColor: int = 0
        self.wheel: int = 0
        self.tire: int = 0
        self.detailing: int = 0
        self.profileBackgroundId: int = 0
        self.stretches: list[int] = []
        self.decalSlots: list[int] = []
        self.onAddons: list[int] = []
        self.costumeId: int = 0

    def __str__(self) -> str:
        return f"""CarDNA:
        carName = {self.carName}
        carNumber = {self.carNumber}
        logoBackgroundId = {self.logoBackgroundId}
        logoBackgroundColor = {self.logoBackgroundColor}
        logoFontId = {self.logoFontId}
        logoFontColor = {self.logoFontColor}
        gender = {self.gender}
        careerType = {self.careerType}
        chassis = {self.chassis}
        color = {self.color}
        eyeColor = {self.eyeColor}
        wheel = {self.wheel}
        tire = {self.tire}
        detailing = {self.detailing}
        profileBackgroundId = {self.profileBackgroundId}
        stretches = {self.stretches}
        decalSlots = {self.decalSlots}
        onAddons = {self.onAddons}
        costumeId = {self.costumeId}"""

    def validateDNA(self) -> bool:
        if self.carName == "" or len(self.carName.split(',')) != 3:
            return False

        if not isinstance(self.gender, int) or \
        self.gender < FIRST_VALID_GENDER or \
        self.gender >= FIRST_VALID_GENDER + NUM_VALID_GENDERS:
            return False

        if not isinstance(self.chassis, int) or self.chassis == CHASSIS_TYPE_INVALID:
            return False
        if not isinstance(self.color, int) or self.color == COLOR_TYPE_INVALID:
            return False
        if not isinstance(self.eyeColor, int) or self.eyeColor == EYES_TYPE_INVALID:
            return False
        if not isinstance(self.wheel, int) or self.wheel == WHEELS_TYPE_INVALID:
            return False
        if not isinstance(self.tire, int) or self.tire == TIRES_TYPE_INVALID:
            return False

        for attr in (self.logoBackgroundId, self.logoBackgroundColor,
                    self.logoFontId, self.logoFontColor, self.careerType,
                    self.detailing, self.profileBackgroundId, self.costumeId):
            if not isinstance(attr, int):
                return False

        if self.stretches is None or \
        not isinstance(self.stretches, list) or \
        len(self.stretches) < NUM_STRETCHES or \
        not all(isinstance(x, int) for x in self.stretches):
            return False

        if self.decalSlots is None or \
        not isinstance(self.decalSlots, list) or \
        len(self.decalSlots) < NUM_DECAL_SLOTS or \
        not all(isinstance(x, int) for x in self.decalSlots):
            return False

        if self.onAddons is None or \
        not isinstance(self.onAddons, list) or \
        not all(isinstance(x, int) for x in self.onAddons):
            return False

        return True
