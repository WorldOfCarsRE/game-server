from typing import Dict, List, Tuple

# These values are from https://pixarcars.fandom.com/wiki/The_World_of_Cars_Online#Rewards
REWARDS = {
    'spRace_ccs': {
        1: (320, 640),
        2: (240, 480),
        3: (160, 320),
        4: (80, 160)
    },
    'mpRace_ccs': {
        1: (336, 672),
        2: (252, 504),
        3: (168, 336),
        4: (84, 168)
    },
    'spRace_rh': {
        1: (480, 960),
        2: (360, 720),
        3: (240, 480),
        4: (120, 240)
    },
    'mpRace_rh': {
        1: (504, 1008),
        2: (378, 756),
        3: (252, 504),
        4: (126, 252)
    },
    'spRace_wb': {
        1: (200, 400),
        2: (150, 300),
        3: (100, 200),
        4: (50, 100)
    },
    'mpRace_wb': {
        1: (210, 420),
        2: (157, 315),
        3: (105, 210),
        4: (52, 105)
    },
    'spRace_ffr': {
        1: (400, 800),
        2: (300, 600),
        3: (210, 420),
        4: (120, 240)
    },
    'mpRace_ffr': {
        1: (420, 840),
        2: (315, 630),
        3: (240, 480),
        4: (126, 252)
    }
}

def getRewardsForTrack(name, place) -> Tuple[int, int]:
    places = REWARDS.get(name)
    if not places:
        print(f"RaceGlobals: Missing rewards for track name: {name}")
        return (0, 0)
    rewards = places.get(place)
    if not rewards:
        print(f"RaceGlobals: Missing rewards for place {place} of track {name}")
        return (0, 0)
    return rewards
