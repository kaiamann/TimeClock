"""Test suite for the storage module"""
from datetime import datetime as Datetime
from datetime import timedelta as Timedelta

import os
import pytest

from timeclock.storage import Storage

@pytest.fixture(autouse=True)
def delete_data(data_dir: str, filename: str):
    """Delete the test datafile"""
    yield
    os.remove(os.path.join(data_dir, filename))

@pytest.mark.usefixtures("delete_data")
class TestEmptyStorage:
    """Tests for an emtpty storage."""

    def test_init(self, empty_storage: Storage):
        """Test that the data file exists.

        Args:
            empty_json_storage (Storage): The  Storage.
        """
        assert os.path.exists(empty_storage.data_path)

    def test_save(self, empty_storage: Storage):
        """Test that the storage handles save correctly.

        Args:
            empty_json_storage (Storage): The  Storage.
        """
        assert empty_storage.save()

    def test_load(self, empty_storage: Storage):
        """Test that the storage handles empty load correctly.

        Args:
            empty_json_storage (Storage): The  Storage
        """
        assert empty_storage.load()

    def test_get_slot(self, empty_storage: Storage):
        """Test that the storage returns None when a non existing slot is requested.

        Args:
            empty_json_storage (Storage): The  Storage.
        """
        datetime = Datetime.now()
        assert empty_storage.get_slot(datetime) is None

    def test_delete_slot(self, empty_storage: Storage):
        """Test that the storage returns False when a non existing slot is deleted.

        Args:
            empty_json_storage (Storage): The  Storage.
        """
        datetime = Datetime.now()
        assert not empty_storage.delete_slot(datetime)

    def test_get_last_slot(self, empty_storage: Storage):
        """Test that the storage returns None when requesting the last slot on empty dataset.

        Args:
            empty_json_storage (Storage): The  Storage.
        """
        assert empty_storage.get_last_slot() is None

    def test_get_slots_between(self, empty_storage: Storage):
        """Test that the storage returns an empty list requesting multiple slots on empty dataset.

        Args:
            empty_json_storage (Storage): The  Storage.
        """
        start = Datetime.now()
        end = start + Timedelta(hours=1)
        assert empty_storage.get_slots_between(start, end) == []


@pytest.mark.usefixtures("delete_data")
class TestInitializedStorage:
    """Tests for an initialized storage."""

    def test_init(self, initialized_storage: Storage):
        """Test that the data file exists.

        Args:
            initialized_storage (Storage): The Storage.
        """
        assert os.path.exists(initialized_storage.data_path)

    def test_save(self, initialized_storage: Storage):
        """Test that the storage handles save correctly.

        Args:
            initialized_storage (Storage): The Storage.
        """
        assert initialized_storage.save()

    def test_load(self, initialized_storage: Storage):
        """Test that the storage handles empty load correctly.

        Args:
            initialized_storage (Storage): The Storage
        """
        assert initialized_storage.load()

    def test_get_slot(self, initialized_storage: Storage):
        """Test that the storage returns None when a non existing slot is requested.

        Args:
            initialized_storage (Storage): The Storage.
        """
        datetime = Datetime.now()
        assert initialized_storage.get_slot(datetime) is None

    def test_delete_slot(self, initialized_storage: Storage):
        """Test that the storage returns False when a non existing slot is deleted.

        Args:
            initialized_storage (Storage): The Storage.
        """
        datetime = Datetime.now()
        assert not initialized_storage.delete_slot(datetime)

    def test_get_last_slot(self, initialized_storage: Storage):
        """Test that the storage returns None when requesting the last slot on empty dataset.

        Args:
            initialized_storage (Storage): The Storage.
        """
        assert initialized_storage.get_last_slot() is not None

    def test_get_slots_between(self, slots, initialized_storage: Storage):
        """Test that the storage returns an empty list requesting multiple slots on empty dataset.

        Args:
            initialized_storage (Storage): The Storage.
        """

        start = slots[0]['start']
        end = slots[-1]['end']
        get_slots = initialized_storage.get_slots_between(start, end)
        print(get_slots)
        print(slots)
        assert len(initialized_storage.data) == len(slots)
        # assert len(slots) == len(get_slots)
        assert slots == get_slots
