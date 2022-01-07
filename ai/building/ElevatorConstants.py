ELEVATOR_NORMAL = 0
ELEVATOR_VP     = 1
ELEVATOR_MINT   = 2
ELEVATOR_CFO    = 3
ELEVATOR_CJ     = 4
ELEVATOR_OFFICE = 5
ELEVATOR_STAGE  = 6
ELEVATOR_BB     = 7
ELEVATOR_COUNTRY_CLUB   = 8

REJECT_NOREASON = 0
REJECT_SHUFFLE = 1
REJECT_MINLAFF = 2
REJECT_NOSEAT = 3
REJECT_PROMOTION = 4
REJECT_BLOCKED_ROOM = 5
REJECT_NOT_YET_AVAILABLE = 6
REJECT_BOARDINGPARTY = 7
REJECT_NOTPAID = 8

MAX_GROUP_BOARDING_TIME = 6.0

ElevatorData = {
    ELEVATOR_NORMAL : { "openTime"  : 2.0,
                        "closeTime" : 2.0,
                        "countdown" : 15.0,
                        },
    ELEVATOR_VP     : { "openTime"  : 4.0,
                        "closeTime" : 4.0,
                        "countdown" : 30.0,
                        },
    ELEVATOR_MINT   : { "openTime"  : 2.0,
                        "closeTime" : 2.0,
                        "countdown" : 15.0,
                        },
    ELEVATOR_OFFICE : { "openTime"  : 2.0,
                        "closeTime" : 2.0,
                        "countdown" : 15.0,
                        },
    ELEVATOR_CFO    : { "openTime"  : 3.0,
                        "closeTime" : 3.0,
                        "countdown" : 30.0
                        },
    ELEVATOR_CJ     : { "openTime"  : 4.0,
                        "closeTime" : 4.0,
                        "countdown" : 30.0,
                        },
    ELEVATOR_STAGE : { "openTime"  : 4.0,
                        "closeTime" : 4.0,
                        "countdown" : 42.0,
                        },
    ELEVATOR_BB     : { "openTime"  : 4.0,
                        "closeTime" : 4.0,
                        "countdown" : 30.0,
                        },
    ELEVATOR_COUNTRY_CLUB : { "openTime"  : 2.0,
                        "closeTime" : 2.0,
                        "countdown" : 15.0,
                        },    
    }

TOON_BOARD_ELEVATOR_TIME = 1.0
TOON_EXIT_ELEVATOR_TIME = 1.0
TOON_VICTORY_EXIT_TIME = 1.0
SUIT_HOLD_ELEVATOR_TIME = 1.0
SUIT_LEAVE_ELEVATOR_TIME = 2.0
INTERIOR_ELEVATOR_COUNTDOWN_TIME = 90
