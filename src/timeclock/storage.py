"""A module that takes care of storing working hours in slots.

Provides a general interface, as well as a JSON implementation.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import csv
from datetime import datetime, timedelta
import json
import os
import subprocess
import sys
from typing import override

from .utils import datetime_from_string, format_datetime

EDITOR = os.environ.get("EDITOR", "vim")


class Slot:
    """Class representing a slot"""

    def __init__(
        self,
        start: datetime,
        end: datetime | None = None,
        description: str | None = None,
    ) -> None:
        self.start: datetime = start
        self.end: datetime | None = end
        self.description: str | None = description

    def to_dict(self) -> dict[str, str]:
        """Convert this slot to a dict.

        Returns:
            dict: This slot as a dict.
        """
        data: dict[str, str] = {}
        if self.start:
            data["start"] = format_datetime(self.start)
        if self.end:
            data["end"] = format_datetime(self.end)
        if self.description:
            data["description"] = self.description
        return data

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> Slot:
        """Create a Slot from dict."""
        start = (
            datetime_from_string(data["start"])
            if "start" in data and data["start"]
            else None
        )
        if not start:
            raise Exception(
                f"Cannot create a Slot without a start date! {json.dumps(data, indent=2)}"
            )
        end = (
            datetime_from_string(data["end"]) if "end" in data and data["end"] else None
        )
        description = (
            data["description"]
            if "description" in data and data["description"]
            else None
        )
        return Slot(start, end, description)

    def duration(self) -> timedelta:
        """Compute the duration of this slot.

        Returns:
            timedelta: The duration.
        """
        end = datetime.now().astimezone()
        if self.end:
            end = self.end
        return end - self.start

    def has_keywords(self, keywords: list[str]) -> bool:
        """Check if this slot's description contains keywords.

        Args:
            keywords: A list of keywords to check for.

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
            start: The start of the timeframe.
            end: The end of the timeframe.

        Returns:
            bool: True if this slot starts or ends within the given timeframe, False otherwise.
        """
        slot_end = self.end or datetime.now().astimezone()
        if start <= self.start <= end or start <= slot_end <= end:
            return True
        return False


class InvalidStorageException(Exception):
    """Error indicating that the storage is badly configured."""


class Storage(ABC):
    """An interface that takes care of storing working hours in slots."""

    def __init__(self, data_dir: str, filename: str) -> None:
        """Initialize the storage.

        Args:
            data_dir: The path to the directory in which
            the file should be stored.
            filename: The name of the data file.

        Raises:
            InvalidStorageException: When the file is not loadable.
        """
        super().__init__()
        self.data_dir: str = data_dir
        self.filename: str = filename

        self.data_path: str = os.path.join(data_dir, filename)
        self.data: list[Slot] = []
        if not os.path.exists(self.data_path):
            self.init_dir()
        _ = self.load()

    def init_dir(self):
        """Initialize the storage directory and put an empty storage file into it"""
        # Create the dir if it does not exist yet
        os.makedirs(self.data_dir, exist_ok=True)
        # Create an empty file there
        _ = self.save()

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
            start: The start time.
        """
        self.data.append(Slot(start=start))

    def get_slot(self, start: datetime) -> Slot | None:
        """Get a specific slot.

        Args:
            start: The start time.

        Returns:
            dict|None: The slot with the specified start time, None otherwise.
        """
        for slot in self.data:
            if start == slot.start:
                return slot
        return None

    def edit_slot(
        self, old_start: datetime, new_start: datetime, end: datetime, description: str
    ) -> bool:
        """Edit a specific slot.

        Args:
            old_start: The start time of the slot to be edited.
            new_start: The new start time.
            end: The new end time.
            description: The new description.

        Returns:
            bool: True if successful, false otherwise.
        """
        for slot in self.data:
            if slot.start == old_start:
                slot.start = new_start
                slot.end = end
                slot.description = description
                return True
        return False

    @abstractmethod
    def edit(self, editor: str) -> None:
        """Directly edit the storage with an editor.

        Args:
            editor: The editor to be used.
        """

    def delete_slot(self, start: datetime) -> bool:
        """Delete a specific slot.

        Args:
            start: The start time of the slot to be deleted.

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

    def get_slots_between(
        self,
        start: datetime,
        end: datetime,
        keywords: list[str] | None = None,
    ) -> list[Slot]:
        """Get all slots in a specific timeframe.

        Args:
            start: The start of the timeframe.
            end: The end of the timeframe.
            keywords: Keywords to filter by.

        Returns:
            list: The list of Slots in the timeframe.
        """
        slots: list[Slot] = []
        for slot in self.data:
            if not keywords or slot.has_keywords(keywords):
                continue

            if slot.lies_within(start, end):
                slots.append(slot)
        return slots


class JSONStorage(Storage):
    """A Storage implementation that uses a JSON file."""

    def __init__(self, data_dir: str, filename: str) -> None:
        filename = f"{filename}.json"
        super().__init__(data_dir, filename)

    @override
    def load(self) -> bool:
        try:
            with open(self.data_path, "r", encoding="utf-8") as file:
                data: list[dict[str, str]] = json.load(file)
                for slot_data in data:
                    self.data.append(Slot.from_dict(slot_data))
            return True
        except json.decoder.JSONDecodeError as err:
            message = f"{self.data_path} is not a valid JSON file."
            raise InvalidStorageException(message) from err

    @override
    def save(self, mode: str = "w+") -> bool:
        with open(self.data_path, mode, encoding="utf-8") as file:
            data: list[dict[str, str]] = []
            for slot in self.data:
                data.append(slot.to_dict())
            json.dump(data, file, indent=2)
            return True

    @override
    def edit(self, editor: str) -> None:
        _ = subprocess.call([editor, self.data_path])


class CSVStorage(Storage):
    """Implementation of Storage using a CSV file."""

    def __init__(self, data_dir: str, filename: str) -> None:
        self.fieldnames: list[str] = ["start", "end", "description"]
        super().__init__(data_dir, f"{filename}.csv")

    @override
    def load(self) -> bool:
        with open(self.data_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                self.data.append(Slot.from_dict(row))
            return True

    @override
    def save(self, mode: str = "w+") -> bool:
        with open(self.data_path, mode, encoding="utf-8") as file:
            writer = csv.DictWriter(file, self.fieldnames)
            writer.writeheader()
            for slot in self.data:
                writer.writerow(slot.to_dict())
            return True

    @override
    def edit(self, editor: str) -> None:
        if sys.platform == "darwin":  # macOS
            _ = subprocess.call(("open", self.filename))
        elif os.name == "nt":  # Windows
            os.startfile(self.filename)
        elif sys.platform.startswith("linux"):
            _ = subprocess.call(("xdg-open", self.filename))
