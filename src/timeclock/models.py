"""A module that takes care of storing working hours in slots.

Provides a general interface, as well as a JSON implementation.
"""

import os
import inspect
from datetime import datetime, timedelta
from typing import Self

# TODO: move this somewhere else preferably into the UserConfig
EDITOR = os.environ.get("EDITOR", "code")

class Model:
    """Base model class"""
    id: int

    def __init__(self, id: int = None):
        self.id = id

    def __eq__(self, other: "Model"):
        if self.__class__ != other.__class__:
            raise TypeError(f"Cannot compare {type(self)} to {type(other)}")
        return vars(self) == vars(other)

    @staticmethod
    def template() -> bool:
        """If set to True create a table for this model"""
        return False

    @staticmethod
    def auto_increment():
        """Return a list of column names that should be auto-incremented"""
        return ["id"]

    @staticmethod
    def primary():
        """Return a list of primary keys"""
        return ["id"]

    @staticmethod
    def unique() -> list[str]:
        """Return a list of unique keys"""
        return []

    @classmethod
    def get_annotations(cls):
        """Get the annotations for this class including those from superclasses."""
        annotations = {}
        for thing in inspect.getmro(cls):
            try:
                annotations.update(thing.__annotations__)
            except AttributeError:
                pass
        return annotations

    def save(self):
        self.objects.save(self)

    def __repr__(self):
        return str(vars(self))


# -------------
# --- Users ---
# -------------

class UserSettings(Model):
    """Class for keeping user settings"""
    locale: str
    locale_subdiv: str

    def __init__(
        self, locale: str, id: int = None, locale_subdiv: str = None,
    ) -> None:
        super().__init__(id)
        self.locale = locale
        self.locale_subdiv = locale_subdiv

class User(Model):
    """Class representing a user"""
    name: str
    email: str
    settings: UserSettings

    def __init__(
        self, name: str, id: int = None, email: str = None, settings: UserSettings = None
    ) -> None:
        super().__init__(id)
        self.name = name
        self.email = email
        self.settings = settings

    @staticmethod
    def unique():
        return ["name"]


class Employer(User):
    """Class representing an employer"""

# -----------------
# --- Timeslots ---
# -----------------

class Slot(Model):
    """Class representing a slot"""

    start: datetime
    end: datetime
    description: str

    def __init__(
        self, start: datetime, id: int = None, end: datetime = None, description: str = None
    ) -> None:
        super().__init__(id)
        self.start = start
        self.end = end
        self.description = description

    @staticmethod
    def template():
        return True

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

    def contains(self, date: datetime) -> bool:
        """Check if a specific datetime is contained in this slot.

        Args:
            date (datetime): The date to be checked.

        Returns:
            bool: True if this slot contains the date, False otherwise.
        """
        return (
            self.start <= date <= self.end if self.end else datetime.now().astimezone()
        )

class Project(Slot):
    name: str
    active: bool

    def __init__(self, name: str, active: bool = False, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = name
        self.active = active

    @classmethod
    def get_active_contract(cls):
        query = f"SELECT id FROM {cls.__name__} WHERE active=1"
        cursor = cls.objects.storage.direct_query(query)
        active_dict = cursor.fetchone()
        if not active_dict:
            return None
        return cls.objects.get_by_id(active_dict["id"])

    def deactivate(self) -> None:
        self.active = False
        self.save()

    def activate(self) -> None:
        active = self.__class__.get_active_contract() # type: Project
        if active:
            active.deactivate()
        self.active = True
        self.save()

    @staticmethod
    def template():
        return False

    @property
    def slots(self) -> list[Self]:
        return [ slot for slot in ProjectSlot.objects.all() if slot.project.name == self.name ]

class ProjectSlot(Slot):
    project: Project

    def __init__(self, project: Project, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project

    @staticmethod
    def template():
        return False


class Contract(Project):
    user: User
    employer: Employer
    hours_per_week: float
    days_off_per_month: float
    work_days: list[int]

    def __init__(
        self,
        user: User,
        employer: Employer = None,
        hours_per_week: float = 8.0,
        days_off_per_month: float = 0,
        work_days: list[int] = list(range(0, 5)),
        *args,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.employer = employer
        self.hours_per_week = hours_per_week
        self.days_off_per_month = days_off_per_month
        self.work_days = work_days

    @staticmethod
    def template():
        return False

    def get_hours_per_day(self) -> float:
        return self.hours_per_week / len(self.work_days)

    @property
    def slots(self) -> list[Self]:
        return [ slot for slot in ContractSlot.objects.all() if slot.contract.name == self.name ]


class ContractSlot(Slot):
    contract: Contract

    def __init__(self, contract: Contract, start: datetime, end: datetime = None, description: str = None, id: int = None):
        super().__init__(start=start, end=end, description=description, id=id)
        self.contract = contract

    @staticmethod
    def template():
        return False

class Vacation(ContractSlot):
    pass