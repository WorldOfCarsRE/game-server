from ai.suit.SuitGlobals import suitDepts

leftLegUpper = 1
leftLegLower = 2
leftLegFoot = 4
rightLegUpper = 8
rightLegLower = 16
rightLegFoot = 32
torsoLeftShoulder = 64
torsoRightShoulder = 128
torsoChest = 256
torsoHealthMeter = 512
torsoPelvis = 1024
leftArmUpper = 2048
leftArmLower = 4096
leftArmHand = 8192
rightArmUpper = 16384
rightArmLower = 32768
rightArmHand = 65536
upperTorso = torsoLeftShoulder

PartsPerSuitBitmasks = (131071,
 130175,
 56447,
 56411)

PartsQueryMasks = (leftLegFoot + leftLegLower + leftLegUpper,
 rightLegFoot + rightLegLower + rightLegUpper,
 torsoPelvis + torsoHealthMeter + torsoChest + torsoRightShoulder + torsoLeftShoulder,
 leftArmHand + leftArmLower + leftArmUpper,
 rightArmHand + rightArmLower + rightArmUpper)

def getNextPart(parts, partIndex, dept):
    dept = dept2deptIndex(dept)
    needMask = PartsPerSuitBitmasks[dept] & PartsQueryMasks[partIndex]
    haveMask = parts[dept] & PartsQueryMasks[partIndex]
    nextPart = ~needMask | haveMask
    nextPart = nextPart ^ nextPart + 1
    nextPart = nextPart + 1 >> 1
    return nextPart

def isSuitComplete(parts, dept):
    dept = dept2deptIndex(dept)
    for p in range(len(PartsQueryMasks)):
        if getNextPart(parts, p, dept):
            return 0

    return 1

def dept2deptIndex(dept):
    if type(dept) == str:
        dept = suitDepts.index(dept)
    return dept