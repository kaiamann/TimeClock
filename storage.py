from utils import datetimeFromString, formatDatetime
from datetime import date, datetime
import json
import os
from abc import ABC, abstractmethod
from subprocess import call


EDITOR = os.environ.get('EDITOR', 'code')

class Storage(ABC):
    @abstractmethod
    def __init__(self, dataDir: str, filename: str) -> None:
        super().__init__()
    
    def load(self):
        pass

    def save(self):
        pass

    def createSlot(self, start: datetime):
        pass

    def getSlot(self, start: datetime):
        pass

    def editSlot(self, oldStart: datetime, newStart: datetime, end: datetime, description: str):
        pass

    def deleteSlot(self, start: datetime):
        pass

    def getLastSlot(self):
        pass

    def getSlotsBetween(self, start: date, end: date, keyword=[]):
        pass


class JSONStorage(Storage):
        
    def __init__(self, dataDir: str, fileName: str) -> None:
        self.dataDir = dataDir
        self.filename = fileName

        self.dataPath = os.path.join(dataDir, fileName)
        self.data = []
        self.load()

    def load(self):
        try:
            f = open(self.dataPath)
            self.data = json.load(f)
            return True
        except Exception:
            self.data = []
            return False
    
    def save(self, mode="w+"):
        try:
            f = open(self.dataPath, mode, encoding="utf-8")
            json.dump(self.data, f)
            return True
        except FileNotFoundError:
            print("Error writing data")
            return False


    def createSlot(self, start: datetime):
        pass

    def getSlot(self, start: datetime):
        for slot in self.data:
            if slot['start'] == start:
                return slot
        return None

    def editSlot(self, dt: datetime, start: datetime, end: datetime, description: str):
        for i in range(len(self.data)):
            slot = self.data[i]
            slotStart = datetimeFromString(slot['start'])
            if slotStart == dt:
                self.data[i]['start'] = formatDatetime(start)
                self.data[i]['end'] = formatDatetime(end)
                self.data[i]['description'] = description
                return True
        return False

    def deleteSlot(self, start: datetime):
        for slot in self.data:
            slotStart = datetimeFromString(slot['start'])
            if start == slotStart:
                self.data.remove(slot)
                return True
        return False

    def get(start: datetime, end: datetime, keywords:list=[]):
        pass

    def getLastSlot(self):
        return self.data[-1]

    def edit(self, editor: str):
        editor = editor if editor else EDITOR
        call([editor, self.dataPath])
        