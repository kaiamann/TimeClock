"""A module that takes care of storing working hours in slots.

Provides a general interface, as well as a JSON implementation.
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import date, datetime
from subprocess import call
from typing_extensions import override
from utils import datetime_from_string, format_datetime, has_keywords

EDITOR = os.environ.get('EDITOR', 'code')


class InvalidStorageException(Exception):
    """Error indicating that the storage is badly configured."""


class Storage(ABC):
    """An interface that takes care of storing working hours in slots."""

    @abstractmethod
    def __init__(self, data_dir: str, filename: str) -> None:
        """Initialize the storage.

        Args:
            dataDir (str): The path to the directory in which
            the file should be stored.
            filename (str): The name of the data file.
        
        Raises:
            InvalidStorageException: When the file is not loadable.
        """
        super().__init__()

    def load(self) -> bool:
        """Load the data from the data file.

        Returns:
            bool: True if successful, False otherwise.
        """

    def save(self) -> bool:
        """Save the data to the data file.

        Returns:
            bool: True if successful, false otherwise.
        """

    def create_slot(self, start: datetime) -> None:
        """Create a new slot.

        Args:
            start (datetime): The start time.
        """

    def get_slot(self, start: datetime) -> dict | None:
        """Get a specific slot.

        Args:
            start (datetime): The start time.

        Returns:
            dict|None: The slot with the specified start time, None otherwise.
        """

    def edit_slot(self,
                  old_start: datetime,
                  new_start: datetime,
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

    def edit(self, editor: str) -> None:
        """Directly edit the storage with an editor.

        Args:
            editor (string): The editor to be used.
        """

    def delete_slot(self, start: datetime) -> bool:
        """Delete a specific slot.

        Args:
            start (datetime): The start time of the slot to be deleted.

        Returns:
            bool: True if successful, False otherwise.
        """

    def get_last_slot(self) -> dict | None:
        """Get the newest slot in the dataset.

        Returns:
            dict|None: The newest slot, or None if data is empty.
        """

    def get_slots_between(self, start: date, end: date, keywords=None) -> list:
        """Get all slots in a speficic timeframe.

        Args:
            start (date): The start of the timeframe.
            end (date): The end of the timeframe.
            keyword (list, optional): Keywords that have to be contained
            by the slots. Defaults to [].

        Returns:
            list: The list of slots in the timeframe.
        """


class JSONStorage(Storage):
    """A Storage implementation that a JSON file."""

    @override
    def __init__(self, dataDir: str, fileName: str) -> None:
        self.data_dir = dataDir
        self.filename = fileName

        self.data_path = os.path.join(dataDir, fileName)
        self.data = []
        try:
            self.load()
        except FileNotFoundError:
            # create the dir if it does not exist yet
            os.makedirs(self.data_dir, exist_ok=True)
            # create an empty file there
            self.save()
        except json.decoder.JSONDecodeError as err:
            message = f"{self.data_path} is not a valid JSON file."
            raise InvalidStorageException(message) from err

    @override
    def load(self) -> bool:
        with open(self.data_path, "r", encoding="utf-8") as file:
            self.data = json.load(file)
            return True
        return False

    @override
    def save(self, mode="w+") -> bool:
        try:
            with open(self.data_path, mode, encoding="utf-8") as file:
                json.dump(self.data, file)
                return True
        except FileNotFoundError:
            print("Error writing data")
            return False

    @override
    def create_slot(self, start: datetime) -> None:
        formatted_start = format_datetime(start)
        slot = {"start": formatted_start}
        self.data.append(slot)

    @override
    def get_slot(self, start: datetime) -> dict | None:
        for slot in self.data:
            if slot['start'] == start:
                return slot
        return None

    @override
    def edit_slot(self,
                  old_start: datetime,
                  new_start: datetime,
                  end: datetime,
                  description: str
                  ):
        for i, slot in enumerate(self.data):
            slot_start = datetime_from_string(slot['start'])
            if slot_start == old_start:
                self.data[i]['start'] = format_datetime(new_start)
                self.data[i]['end'] = format_datetime(end)
                self.data[i]['description'] = description
                return True
        return False

    @override
    def delete_slot(self, start: datetime):
        for slot in self.data:
            slot_start = datetime_from_string(slot['start'])
            if start == slot_start:
                self.data.remove(slot)
                return True
        return False

    @override
    def get_last_slot(self):
        if not self.data:
            return None

        slot = self.data[-1]

        parsed_slot = {}
        parsed_slot['start'] = datetime_from_string(slot["start"])
        if "end" in slot:
            parsed_slot['end'] = datetime_from_string(slot["end"])

        if "description" in slot:
            parsed_slot['description'] = slot['description']

        return parsed_slot

    @override
    def get_slots_between(self,
                          start: datetime,
                          end: datetime,
                          keywords: list = None) -> list:
        slots = []
        for slot in self.data:
            if not has_keywords(slot, keywords):
                continue

            slot_start = datetime_from_string(slot["start"])
            slot_start_date = slot_start.date()

            slot_end = datetime.now()
            if "end" in slot:
                slot_end = datetime_from_string(slot["end"])

            if slot_start_date >= start and slot_start_date <= end:
                parsed_slot = {}
                parsed_slot['start'] = slot_start
                parsed_slot['end'] = slot_end
                if 'description' in slot:
                    parsed_slot['description'] = slot['description']
                slots.append(parsed_slot)
        return slots

    @override
    def edit(self, editor: str):
        editor = editor if editor else EDITOR
        call([editor, self.data_path])
