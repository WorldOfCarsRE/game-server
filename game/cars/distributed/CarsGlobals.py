ZONE_3_INTEREST_HANDLE = 1
LOBBIES_INTEREST_HANDLE = 2
REQUIRED_ZONE_INTEREST_HANDLE = 3
ZONE_INTEREST_HANDLE = 4
DUNGEON_INTEREST_HANDLE = 5
DEFAULT_DUNGEON_ZONE = 6
TUTORIAL_LOBBY_INTEREST_HANDLE = DEFAULT_DUNGEON_ZONE
YARD_INTEREST_HANDLE = 69

OTP_DO_ID_CARS_SHARD_MANAGER = 4757

# Everything from this zone up to the top of the available range is
# reserved for the dynamic zone pool.  Note that our effective maximum
# zone may be less than DynamicZonesEnd, depending on the assignment
# of available doIds--we must be careful not to overlap.
DynamicZonesBegin =    61000
DynamicZonesEnd =      (1 << 20)
