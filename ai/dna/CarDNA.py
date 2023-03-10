class CarDNA(object):
    def __init__(
        self,
        carName = 'Tia,Spark,driver',
        carNumber = 83,
        logoBackgroundId = 0,
        logoBackgroundColor = 1004143,
        logoFontId = 0,
        logoFontColor = 16777215,
        gender = 0,
        careerType = -1,
        chassis = 5502,
        color = 20201,
        eyeColor = 10102,
        wheel = 30601,
        tire = 30502,
        detailing = 0,
        profileBackgroundId = 0,
        stretches = [],
        decalSlots = [
            0,    -1,     0,     0,
            -1,     0,     0,    -1,
            0,     0,     0,     0,
            51103, 51103, 51104, 51104
        ],
        onAddons = [],
        costumeId = 0):
        self.carName = carName
        self.carNumber = carNumber
        self.logoBackgroundId = logoBackgroundId
        self.logoBackgroundColor = logoBackgroundColor
        self.logoFontId = logoFontId
        self.logoFontColor = logoFontColor
        self.gender = gender
        self.careerType = careerType
        self.chassis = chassis
        self.color = color
        self.eyeColor = eyeColor
        self.wheel = wheel
        self.tire = tire
        self.detailing = detailing
        self.profileBackgroundId = profileBackgroundId
        self.stretches = stretches
        self.decalSlots = decalSlots
        self.onAddons = onAddons
        self.costumeId = costumeId

