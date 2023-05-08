"""A module that takes care of storing working hours in slots.

Provides a general interface, as well as a JSON implementation.
"""

from typing_extensions import override
from utils import datetimeFromString, formatDatetime, hasKeywords
from datetime import date, datetime
import json
import os
from abc import ABC, abstractmethod
from subprocess import call

EDITOR = os.environ.get('EDITOR', 'code')


class Storage(ABC):
    """An interface that takes care of storing working hours in slots."""

    @abstractmethod
    def __init__(self, dataDir: str, filename: str) -> None:
        """Initialize the storage.

        Args:
            dataDir (str): The path to the directory in which
            the file should be stored.
            filename (str): The name of the data file.
        """
        super().__init__()

    def load(self) -> bool:
        """Load the data from the data file.

        Returns:
            bool: True if successful, False otherwise.
        """
        pass

    def save(self) -> bool:
        """Save the data to the data file.

        Returns:
            bool: True if successful, false otherwise.
        """
        pass

    def createSlot(self, start: datetime) -> None:
        """Create a new slot.

        Args:
            start (datetime): The start time.
        """
        pass

    def getSlot(self, start: datetime) -> dict | None:
        """Get a specific slot.

        Args:
            start (datetime): The start time.

        Returns:
            dict|None: The slot with the specified start time, None otherwise.
        """
        pass

    def editSlot(self,
                 oldStart: datetime,
                 newStart: datetime,
                 end: datetime,
                 description: str) -> bool:
        """Edit a specific slot.

        Args:
            oldStart (datetime): The start time of the slot to be edited.
            newStart (datetime): The new start time.
            end (datetime): The new end time.
            description (str): The new description.

        Returns:
            bool: True if successful, false otherwise.
        """
        pass

    def deleteSlot(self, start: datetime) -> bool:
        """Delete a specific slot.

        Args:
            start (datetime): The start time of the slot to be deleted.

        Returns:
            bool: True if successful, False otherwise.
        """
        pass

    def getLastSlot(self) -> dict | None:
        """Get the newest slot in the dataset.

        Returns:
            dict|None: The newest slot, or None if data is empty.
        """
        pass

    def getSlotsBetween(self, start: date, end: date, keyword=[]) -> list:
        """Get all slots in a speficic timeframe.

        Args:
            start (date): The start of the timeframe.
            end (date): The end of the timeframe.
            keyword (list, optional): Keywords that have to be contained
            by the slots. Defaults to [].

        Returns:
            list: The list of slots in the timeframe.
        """
        pass


class JSONStorage(Storage):
    """An impementation of the Storage interface that
    uses a JSON file to store working hours."""

    @override
    def __init__(self, dataDir: str, fileName: str) -> None:
        self.dataDir = dataDir
        self.filename = fileName

        self.dataPath = os.path.join(dataDir, fileName)
        self.data = []
        self.load()

    @override
    def load(self) -> bool:
        try:
            f = open(self.dataPath)
            self.data = json.load(f)
            return True
        except Exception:
            self.data = []
            return False

    @override
    def save(self, mode="w+") -> bool:
        try:
            f = open(self.dataPath, mode, encoding="utf-8")
            json.dump(self.data, f)
            return True
        except FileNotFoundError:
            print("Error writing data")
            return False

    @override
    def createSlot(self, start: datetime) -> None:
        formattedDatetime = formatDatetime(start)
        slot = {"start": formattedDatetime}
        self.data.append(slot)

    @override
    def getSlot(self, start: datetime) -> dict | None:
        for slot in self.data:
            if slot['start'] == start:
                return slot
        return None

    @override
    def editSlot(self,
                 dt: datetime,
                 start: datetime,
                 end: datetime,
                 description: str
                 ):
        for i in range(len(self.data)):
            slot = self.data[i]
            slotStart = datetimeFromString(slot['start'])
            if slotStart == dt:
                self.data[i]['start'] = formatDatetime(start)
                self.data[i]['end'] = formatDatetime(end)
                self.data[i]['description'] = description
                return True
        return False

    @override
    def deleteSlot(self, start: datetime):
        for slot in self.data:
            slotStart = datetimeFromString(slot['start'])
            if start == slotStart:
                self.data.remove(slot)
                return True
        return False

    @override
    def getLastSlot(self):
        if not self.data:
            return None

        slot = self.data[-1]

        parsedSlot = {}
        parsedSlot['start'] = datetimeFromString(slot["start"])
        if "end" in slot:
            parsedSlot['end'] = datetimeFromString(slot["end"])

        if "description" in slot:
            parsedSlot['description'] = slot['description']

        return parsedSlot

    @override
    def getSlotsBetween(self,
                        start: datetime,
                        end: datetime,
                        keywords: list = []) -> list:
        slots = []
        for slot in self.data:
            if not hasKeywords(slot, keywords):
                continue

            slotStart = datetimeFromString(slot["start"])
            slotStartDate = slotStart.date()

            slotEnd = datetime.now()
            if "end" in slot:
                slotEnd = datetimeFromString(slot["end"])

            if slotStartDate >= start and slotStartDate <= end:
                parsedSlot = {}
                parsedSlot['start'] = slotStart
                parsedSlot['end'] = slotEnd
                parsedSlot['description'] = slot['description']
                slots.append(parsedSlot)
        return slots

    @override
    def edit(self, editor: str):
        editor = editor if editor else EDITOR
        call([editor, self.dataPath])
