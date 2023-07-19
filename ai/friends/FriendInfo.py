class FriendInfo:
    def __init__(self,
    avatarName: str = '',
    openChatEnabledYesNo: int = 1,
    openChatFriendshipYesNo: int = 0,
    sublocation: str = '',
    playerName: str = '',
    avatarId: int = 0,
    onlineYesNo: int = 1,
    timestamp: int = 0,
    wlChatEnabledYesNo: int = 0,
    location: str = ''):
        self.avatarName = avatarName
        self.openChatEnabledYesNo = openChatEnabledYesNo
        self.openChatFriendshipYesNo = openChatFriendshipYesNo
        self.sublocation = sublocation
        self.playerName = playerName
        self.avatarId = avatarId
        self.onlineYesNo = onlineYesNo
        self.timestamp = timestamp
        self.wlChatEnabledYesNo = wlChatEnabledYesNo
        self.location = location
