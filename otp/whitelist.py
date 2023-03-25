from panda3d.core import VirtualFileSystem, Filename, DSearchPath
from bisect import bisect_left
from .networking import Service

class WhiteList(Service):

    def __init__(self):
        vfs = VirtualFileSystem.getGlobalPtr()

        filename = Filename('chat_whitelist.xml')

        searchPath = DSearchPath()
        searchPath.appendDirectory(Filename('etc/assets'))

        if not vfs.resolveFilename(filename, searchPath):
            self.service.log.error('Failed to find whitelist data!')
            return

        data = vfs.readFile(filename, 1)
        wordlist = data.split(b'\n')

        self.words = []
        for line in wordlist:
            self.words.append(line.strip(b'\n\r').lower())

        self.words.sort()
        self.numWords = len(self.words)

    def cleanText(self, text):
        text = text.strip('.,?!')
        text = text.lower().encode('utf-8')
        return text

    def isWord(self, text):
        text = self.cleanText(text)
        i = bisect_left(self.words, text)
        if i == self.numWords:
            return False
        return self.words[i] == text

    def filterWhiteList(self, message):
        modifications = []
        words = message.split(' ')
        offset = 0

        for word in words:
            if word and not self.isWord(word):
                modifications.append((offset, offset + len(word) - 1))

            offset += len(word) + 1

        cleanMesssage = message

        for modStart, modStop in modifications:
            cleanMesssage = cleanMesssage[:modStart] + '*' * (modStop - modStart + 1) + cleanMesssage[modStop + 1:]

        return cleanMesssage, modifications
