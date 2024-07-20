import os
import subprocess
import sys
import random

NUM_DISTRICTS = 2

districtNames = [
    'Alignment',
    'Axle',
    'Backfire'
]

cutDistrictNames = random.sample(districtNames, NUM_DISTRICTS)

startingNum = 200000000
minObjIdBase = 200100000
maxObjIdBase = 200149999

isWindows = sys.platform == 'win32'

os.chdir('startup/win32' if isWindows else 'startup/unix')

for index, elem in enumerate(cutDistrictNames):
    subprocess.shell = True

    districtName = str(cutDistrictNames[index])

    os.environ['DISTRICT_NAME'] = districtName
    os.environ['BASE_CHANNEL'] = str(startingNum)
    os.environ['MIN_OBJ_ID'] = str(minObjIdBase)
    os.environ['MAX_OBJ_ID'] = str(maxObjIdBase)

    os.system('start cmd /c districtStarter.bat' if isWindows else f'screen -dmS "{districtName}" ./districtStarter.sh')

    startingNum = startingNum + 1000000
    minObjIdBase = minObjIdBase + 1000000
    maxObjIdBase = maxObjIdBase + 1000000
