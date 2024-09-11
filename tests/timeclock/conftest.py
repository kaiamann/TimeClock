import pytest
import os

from timeclock import all_subclasses
from timeclock.models import Model, ContractSlot, Contract, Project, User, Employer
from timeclock.storage import Storage
from datetime import datetime, timedelta

@pytest.fixture
def storage():
    file_name = "test.sqlite"
    yield Storage(file_name)
    # os.remove(file_name)

@pytest.fixture(params=[Employer, ContractSlot, ProjectSlot, ])
def example_models(request):
    builder_function = f"example_{request.param.__name__}_list"
    if builder_function in globals():
        return globals()[builder_function]()
    return []
    # raise NotImplementedError(f"Implement {builder_function}!")

@pytest.fixture
def example_contracts():
    return example_Contract_list()

def example_ContractSlot_list():
    slots = []
    start = datetime(year=2023, month=12, day=31, hour=12, minute=12)
    arguments = {
        "start": start,
        "end": start + timedelta(hours=2),
        "description": "test"
    }

    current_arguments = {}
    for contract in example_Contract_list():
        current_arguments["contract"] = contract
        for key, value in arguments.items():
            current_arguments[key] = value
            slots.append(ContractSlot(**current_arguments))

    return slots


def example_Contract_list():

    user = User(name="Test User")
    employer = Employer(name="Test Employer")

    # First test contract
    start = datetime(year=2023, month=12, day=31, hour=12, minute=12)
    arguments = {
        "name": "something",
        "user": user,
        "start": start,
        "end": start + timedelta(hours=2),
        "description": "Test Description",
        "employer": employer,
        "hours_per_week": 3.5,
        "days_off_per_month": 2.3,
        "work_days": list(range(0, 5)),
    }

    contracts = []
    contracts.append(Contract(**arguments))

    return contracts

def example_Employer_list():
    pass

def example_Project_list():
    projects = []

    # First test contract
    start = datetime(year=2023, month=12, day=31, hour=12, minute=12)
    arguments = {
        "name": "Test Name",
        "start": start,
        "end": start + timedelta(hours=2),
        "description": "Test Description",
    }

    projects.append(Project(**arguments))

    return projects
