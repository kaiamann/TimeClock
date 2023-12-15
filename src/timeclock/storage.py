"""A module that takes care of storing working hours in slots.

Provides a general interface, as well as a JSON implementation.
"""

import csv
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from subprocess import call

from .utils import datetime_from_string, format_datetime

EDITOR = os.environ.get('EDITOR', 'code')

class Slot:
    """Class representing a slot"""

    def __init__(self, start: datetime, end: datetime = None, description: str = None) -> None:
        self.start = start
        self.end = end
        self.description = description


    def as_dict(self) -> dict:
        """Convert this slot to a dict.

        Returns:
            dict: This slot as a dict.
        """
        data = vars(self)
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = format_datetime(value)
            data['description'] = self.description
        return data

    def duration(self) -> timedelta:
        """Compute the duration of this slot.

        Returns:
            timedelta: The duration.
        """
        end = datetime.now().astimezone()
        if self.end:
            end = self.end
        return end - self.start

    def has_keywords(self, keywords: list) -> bool:
        """Check if this slot's description contains keywords.

        Args:
            keywords (list): A list of keywords to check for.

        Returns:
            bool: True if the description contains one of the keywords, False otherwise.
        """
        if not keywords:
            return True
        # Filter for relevant keywords
        relevant = True
        for keyword in keywords:
            if not self.description or keyword not in self.description:
                relevant = False
                break
        return relevant

    def lies_within(self, start: datetime, end: datetime) -> bool:
        """Check if this slot lies within a certain timeframe.

        Args:
            start (datetime): The start of the timeframe.
            end (datetime): The end of the timeframe.

        Returns:
            bool: True if this slot starts or ends within the given timeframe, False otherwise.
        """
        slot_end = self.end or datetime.now().astimezone()
        if start <= self.start <= end or start <= slot_end <= end:
            return True
        return False

class Contract(Slot):

    def __init__(self, start: datetime, end: datetime = None, description: str = None, hours_per_day: float = 8, days_off_per_month: float = 0, working_days: list[int] = range(0,5)) -> None:
        super.__init__(start, end, description)
        self.hours_per_day = hours_per_day
        self.days_off_per_month = days_off_per_month
        self.working_days = working_days


def slot_from_dict(start: str = None, end: str = None, description: str = None) -> Slot:
    """Create a new slot from a dict.

    Args:
        start (str, optional): The start. Defaults to None.
        end (str, optional): The end. Defaults to None.
        description (str, optional): The description. Defaults to None.

    Returns:
        _type_: _description_
    """
    start = datetime_from_string(start)
    end = datetime_from_string(end) if end else None
    return Slot(start, end, description)

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
        self.data = [] # type: list[Slot]
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

    def add_slot(self, slot: Slot) -> None:
        """Create a new slot.

        Args:
            start (datetime): The start time.
        """
        self.data.append(slot)

    def get_slot(self, start: datetime) -> Slot | None:
        """Get a specific slot.

        Args:
            start (datetime): The start time.

        Returns:
            dict|None: The slot with the specified start time, None otherwise.
        """
        for slot in self.data:
            if start == slot.start:
                return slot
        return None

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
            if start == slot.start:
                self.data.remove(slot)
                return True
        return False

    def get_first_slot(self) -> Slot | None:
        """Get the newest slot in the dataset.

        Returns:
            dict|None: The oldest slot, or None if data is empty.
        """
        if not self.data:
            return None

        return self.data[0]

    def get_last_slot(self) -> Slot | None:
        """Get the newest slot in the dataset.

        Returns:
            dict|None: The newest slot, or None if data is empty.
        """
        if not self.data:
            return None

        return self.data[-1]

    def get_slots_between(self, start: datetime, end: datetime, keywords=None) -> list[Slot]:
        """Get all slots in a specific timeframe.

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
            if not slot.has_keywords(keywords):
                continue

            if slot.lies_within(start, end):
                slots.append(slot)
        return slots

class JSONStorage(Storage):
    """A Storage implementation that a JSON file."""

    def __init__(self, data_dir: str, filename: str) -> None:
        filename = f"{filename}.json"
        super().__init__(data_dir, filename)

    def load(self) -> bool:
        try:
            with open(self.data_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                for slot_data in data:
                    self.data.append(slot_from_dict(**slot_data))
            return True
        except json.decoder.JSONDecodeError as err:
            message = f"{self.data_path} is not a valid JSON file."
            raise InvalidStorageException(message) from err

    def save(self, mode="w+") -> bool:
        with open(self.data_path, mode, encoding="utf-8") as file:
            data = []
            for slot in self.data:
                data.append(slot.as_dict())
            json.dump(data, file)
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
                # Skip header
                if row == self.fieldnames:
                    continue
                slot_data = {}
                for i, key in enumerate(self.fieldnames):
                    if row[i]:
                        slot_data[key] = row[i]
                print(slot_data)
                self.data.append(slot_from_dict(**slot_data))
            return True

    def save(self, mode="w+") -> bool:
        with open(self.data_path, mode, encoding="utf-8") as file:
            writer = csv.DictWriter(file, self.fieldnames)
            writer.writeheader()
            for slot in self.data:
                writer.writerow(slot.as_dict())
            return True

    def edit(self, editor: str) -> None:
        pass
