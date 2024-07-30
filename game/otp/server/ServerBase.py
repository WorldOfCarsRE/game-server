class ServerBase:
    def __init__(self):
        self.serverType = config.GetString('server-type', 'dev')

    def isProdServer(self):
        return self.serverType == 'prod'
