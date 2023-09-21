"""Set up fixtures used by the tests"""

import os
from datetime import datetime as Datetime
from datetime import timedelta as Timedelta

import pytest

from timeclock.storage import JSONStorage, CSVStorage

DATA_DIR = os.path.dirname(__file__)
FILENAME = "Timeclock"

STORAGES = [JSONStorage, CSVStorage]

@pytest.fixture
def data_dir() -> str:
    """Get the data directory"""
    return DATA_DIR

@pytest.fixture
def filename() -> str:
    """Get the data filename"""
    return FILENAME

@pytest.fixture
def slots() -> list:
    """Generates a bunch of slots.

    Sums up to 110 hours.

    Returns:
        list: A list of slots
    """
    slot_list = []
    start = Datetime.now().replace(second=0, microsecond=0)
    for i in range(1,21):
        start += Timedelta(days=1)
        hours = i if i < 10 else 20-i
        end = start + Timedelta(hours=hours)
        description = "odd" if i % 2 == 1 else "even"
        slot = {
            'start': start,
            'end': end,
            'description': description
        }
        slot_list.append(slot)
    return slot_list

@pytest.fixture(params=STORAGES)
def initialized_storage(slots, request): # pylint: disable=W0621
    """Build an initialized Storage"""
    storage = request.param(DATA_DIR, FILENAME)
    for slot in slots:
        storage.create_slot(slot['start'])
        storage.edit_slot(slot['start'], slot['start'], slot['end'], slot['description'])#
    return storage

@pytest.fixture(params=STORAGES)
def empty_storage(request):
    """Build an empty Storage"""
    return request.param(DATA_DIR, FILENAME)
