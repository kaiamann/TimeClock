import json
import csv

from tempfile import TemporaryFile
from abc import ABC, abstractmethod

class Serializer(ABC):
    format: str = None

    @abstractmethod
    def deserialize(self, data: str) -> dict|list:
        """Read data from a file

        Args:
            path (str): Path to the file

        Returns:
            list: The data as a list.
        """

    @abstractmethod
    def serialize(self, data: dict|list) -> str:
        """Write data to serialize

        Args:
            data (dict|list): The data to write
        """

    @staticmethod
    def get_serializer(format: str):
        for handler in __class__.__subclasses__():
            if handler.storage_format == format:
                return handler.__class__
        return None


class JSONSerializer(Serializer):
    """A Storage implementation that a JSON file."""

    format = "json"

    def deserialize(self, data: str) -> dict|list:
        return json.loads(data)

    def serialize(self, data: dict|list) -> str:
        return json.dumps(data)


class CSVSerializer(Serializer):
    """Implementation of Storage using a CSV file."""

    format = "csv"

    def __init__(self, column_names) -> None:
        self.column_names = column_names

    def deserialize(self, data: str) -> list[dict]:
        deserialized = []
        with TemporaryFile(mode="w+", encoding="utf-8") as file:
            file.write(data)
            file.seek(0)
            dialect = csv.Sniffer().sniff(file.read(1024))
            file.seek(0)
            reader = csv.reader(file, dialect)
            for row in reader:
                print("row", row)
                print("fieldnames", self.column_names)
                # Skip header
                if row == self.column_names:
                    continue
                slot_data = {}
                for i, key in enumerate(self.column_names):
                    if row[i]:
                        slot_data[key] = row[i]
                deserialized.append(slot_data)
        return deserialized

    def serialize(self, data: list|dict) -> str:
        if isinstance(data, dict):
            data = [data]

        with TemporaryFile(mode="w+", encoding="utf-8") as file:
            writer = csv.DictWriter(file, self.column_names)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
            file.seek(0)
            return file.read()