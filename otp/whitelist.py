from panda3d.core import VirtualFileSystem, Filename, DSearchPath
from bisect import bisect_left
from .networking import Service
import xml.etree.ElementTree as ET

class WhiteList(Service):

    def __init__(self):
        Service.__init__(self)

        vfs = VirtualFileSystem.getGlobalPtr()

        filename = Filename('chat_whitelist.xml')
        speedchat = Filename('speedchat.xml')

        searchPath = DSearchPath()
        searchPath.appendDirectory(Filename('etc/assets'))

        if not vfs.resolveFilename(filename, searchPath) or not vfs.resolveFilename(speedchat, searchPath):
            self.log.error('Failed to find chat data!')
            return

        data = vfs.readFile(filename, 1)
        wordlist = data.split(b'\n')

        self.words = []
        for line in wordlist:
            self.words.append(line.strip(b'\n\r').lower())

        phrases = vfs.readFile(speedchat, 1)
        tree = ET.ElementTree(ET.fromstring(phrases))
        root = tree.getroot()

        self.phrases = []

        for tags in root.findall('.//entry'):
            self.phrases.append(tags.text)

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

        cleanMesssage = message

        if message in self.phrases:
            # Our message is a SpeedChat phrase, allow it
            return cleanMesssage, modifications

        for word in words:
            if word and not self.isWord(word):
                modifications.append((offset, offset + len(word) - 1))

            offset += len(word) + 1

        for modStart, modStop in modifications:
            cleanMesssage = cleanMesssage[:modStart] + '*' * (modStop - modStart + 1) + cleanMesssage[modStop + 1:]

        return cleanMesssage, modifications
