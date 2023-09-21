"""A module that takes care of storing working hours in slots.

Provides a general interface, as well as a JSON implementation.
"""

import csv
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from subprocess import call

from .utils import datetime_from_string, format_datetime, has_keywords

EDITOR = os.environ.get('EDITOR', 'code')

class InvalidStorageException(Exception):
    """Error indicating that the storage is badly configured."""

class Storage(ABC):
    """An interface that takes care of storing working hours in slots."""

    def __init__(self, data_dir: str, filename: str) -> None:
        """Initialize the storage.

        Args:
            data_dir (str): The path to the directory in which
            the file should be stored.
            filename (str): The name of the data file.

        Raises:
            InvalidStorageException: When the file is not loadable.
        """
        super().__init__()
        self.data_dir = data_dir
        self.filename = filename

        self.data_path = os.path.join(data_dir, filename)
        self.data = []
        if not os.path.exists(self.data_path):
            self.init_dir()
        self.load()

    def init_dir(self):
        """Initialize the storage directory and put an empty stoage file into it"""
        # create the dir if it does not exist yet
        os.makedirs(self.data_dir, exist_ok=True)
        # create an empty file there
        self.save()

    @abstractmethod
    def load(self) -> bool:
        """Load the data from the data file.

        Returns:
            bool: True if successful, False otherwise.
        """

    @abstractmethod
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
        formatted_start = format_datetime(start)
        slot = {"start": formatted_start}
        self.data.append(slot)

    def get_slot(self, start: datetime) -> dict | None:
        """Get a specific slot.

        Args:
            start (datetime): The start time.

        Returns:
            dict|None: The slot with the specified start time, None otherwise.
        """
        for slot in self.data:
            start_datetime = datetime_from_string(slot['start'])
            parsed_slot = {}
            parsed_slot['start'] = start_datetime
            if start_datetime == start:
                if 'end' in slot:
                    parsed_slot['end'] = datetime_from_string(slot['end'])
                if 'description' in slot:
                    parsed_slot['description'] = slot['description']
                return parsed_slot
        return None

    def edit_slot(self,
                  old_start: datetime,
                  new_start: datetime,
                  end: datetime,
                  description: str) -> bool:
        """Edit a specific slot.

        Args:
            old_start (datetime): The start time of the slot to be edited.
            new_start (datetime): The new start time.
            end (datetime): The new end time.
            description (str): The new description.

        Returns:
            bool: True if successful, false otherwise.
        """
        for i, slot in enumerate(self.data):
            slot_start = datetime_from_string(slot['start'])
            if slot_start == old_start:
                self.data[i]['start'] = format_datetime(new_start)
                self.data[i]['end'] = format_datetime(end)
                self.data[i]['description'] = description
                return True
        return False

    @abstractmethod
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
        for slot in self.data:
            slot_start = datetime_from_string(slot['start'])
            if start == slot_start:
                self.data.remove(slot)
                return True
        return False

    def get_last_slot(self) -> dict | None:
        """Get the newest slot in the dataset.

        Returns:
            dict|None: The newest slot, or None if data is empty.
        """
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

    def get_slots_between(self, start: datetime, end: datetime, keywords=None) -> list:
        """Get all slots in a speficic timeframe.

        Args:
            start (date): The start of the timeframe.
            end (date): The end of the timeframe.
            keyword (list, optional): Keywords that have to be contained
            by the slots. Defaults to [].

        Returns:
            list: The list of slots in the timeframe.
        """
        slots = []
        for slot in self.data:
            if not has_keywords(slot, keywords):
                continue

            slot_start = datetime_from_string(slot["start"])

            slot_end = datetime.now()
            if "end" in slot:
                slot_end = datetime_from_string(slot["end"])

            if end >= slot_start >= start:
                parsed_slot = {}
                parsed_slot['start'] = slot_start
                parsed_slot['end'] = slot_end
                if 'description' in slot:
                    parsed_slot['description'] = slot['description']
                slots.append(parsed_slot)
        return slots

class JSONStorage(Storage):
    """A Storage implementation that a JSON file."""

    def __init__(self, data_dir: str, filename: str) -> None:
        filename = f"{filename}.json"
        super().__init__(data_dir, filename)

    def load(self) -> bool:
        try:
            with open(self.data_path, "r", encoding="utf-8") as file:
                self.data = json.load(file)
            return True
        except json.decoder.JSONDecodeError as err:
            message = f"{self.data_path} is not a valid JSON file."
            raise InvalidStorageException(message) from err

    def save(self, mode="w+") -> bool:
        with open(self.data_path, mode, encoding="utf-8") as file:
            json.dump(self.data, file)
            return True

    def edit(self, editor: str):
        call([editor, self.data_path])


class CSVStorage(Storage):
    """Implementation of Storage using a CSV file."""

    def __init__(self, data_dir: str, filename: str) -> None:
        filename = f"{filename}.csv"
        self.fieldnames = ['start', 'end', 'description']
        super().__init__(data_dir, filename)

    def load(self) -> bool:
        with open(self.data_path, "r", encoding="utf-8") as file:
            reader = csv.reader(file, self.fieldnames)
            for row in reader:
                if row == self.fieldnames:
                    continue
                slot = {}
                for i, key in enumerate(self.fieldnames):
                    if row[i]:
                        slot[key] = row[i]
                self.data.append(slot)
            return True

    def save(self, mode="w+") -> bool:
        with open(self.data_path, mode, encoding="utf-8") as file:
            writer = csv.DictWriter(file, self.fieldnames)
            writer.writeheader()
            writer.writerows(self.data)
            return True

    def edit(self, editor: str) -> None:
        pass
