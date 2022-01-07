from typing import NamedTuple

class BuildingProperties:
    floors: tuple
    levels: tuple
    boss: tuple
    levelpool: tuple
    poolmult: tuple

CogBuildingInfo = (
  # Level 1
  BuildingProperties(
    floors = (1, 1),
    levels = (1, 3),
    boss = (4, 4),
    levelpool = (8, 10)
    poolmult = (1,),
  ),
  # Level 2
  BuildingProperties(
    floors = (1, 2),
    levels = (2, 4),
    boss = (5, 5),
    levelpool = (8, 10)
    poolmult = (1, 1.2),
  ),
  # Level 3
  BuildingProperties(
    floors = (1, 3),
    levels = (3, 5),
    boss = (6, 6),
    levelpool = (8, 10)
    poolmult = (1, 1.3, 1.6),
  ),
  # Level 4
  BuildingProperties(
    floors = (2, 3),
    levels = (4, 6),
    boss = (7, 7),
    levelpool = (8, 10)
    poolmult = (1, 1.4, 1.8),
  ),
  # Level 5
  BuildingProperties(
    floors = (2, 4),
    levels = (5, 7),
    boss = (8, 8),
    levelpool = (8, 10)
    poolmult = (1, 1.6, 1.8, 2),
  ),
  # Level 6
  BuildingProperties(
    floors = (3, 4),
    levels = (6, 8),
    boss = (9, 9),
    levelpool = (10, 12)
    poolmult = (1, 1.6, 2, 2.4),
  ),
  # Level 7
  BuildingProperties(
    floors = (3, 5),
    levels = (7, 9),
    boss = (10, 10),
    levelpool = (10, 14)
    poolmult = (1, 1.6, 1.8, 2.2, 2.4),
  ),
  # Level 8
  BuildingProperties(
    floors = (4, 5),
    levels = (8, 10),
    boss = (11, 11),
    levelpool = (12, 16)
    poolmult = (1, 1.8, 2.4, 3, 3.2),
  ),
  # Level 9
  BuildingProperties(
    floors = (5, 5),
    levels = (9, 11),
    boss = (12, 12),
    levelpool = (14, 20)
    poolmult = (1.4, 1.8, 2.6, 3.4, 4),
  ),
)

