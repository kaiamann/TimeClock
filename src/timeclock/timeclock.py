"""Module that allows tracking of working hours."""
import os

from datetime import datetime as Datetime
from datetime import timedelta as Timedelta

from .models import Slot, Contract, Vacation
from .utils import datetime_from_string


class TimeClock:
    """A class for tracking working hours."""

    slots: list[Slot]
    vacations: list[Slot]

    def __init__(self, slots: list[Slot], vacations: list[Vacation], contract: Contract = None) -> None:
        """Initialize the TimeClock"""
        # load config and copy values
        self.slots = slots
        self.vacations = vacations
        self.contract = contract
        self.holidays = {}

    @property
    def slots(self):
        return self._slots

    @slots.setter
    def slots(self, value: list[Slot]):
        self._slots = value

    @property
    def vacations(self):
        return self._vacations

    @property
    def holidays(self):
        return self._holidays

    @property
    def contract(self):
        return self._contract


    def init_dir(self):
        """Initialize the storage directory and put an empty stoage file into it"""
        # create the dir if it does not exist yet
        os.makedirs(self.data_dir, exist_ok=True)
        # create an empty file there
        self.save()

    # -------------------
    # -- Time Tracking --
    # -------------------

    def start(self, start: Datetime) -> None:
        """Start the time tracking.

        Args:
            start (Datetime): The point in time where tracking should begin.
        """

        self.slots.append(Slot(start=start))

    def finish(self, end: Datetime, description: str) -> Datetime:
        """Finish the time tracking.

        Args:
            end (Datetime): The point in time where tracking should stop.
            description (str): The description of what has been done.

        Returns:
            Datetime: The start Datetime when the slot was started.
        """
        last_slot = self.slots[-1]
        last_slot.end = end
        last_slot.description = description
        return last_slot.start

    def is_started(self) -> bool:
        """Check if there is an open slot that needs to be closed.

        Returns:
            bool: True if there is an open slot False otherwise.
        """
        last_slot = self.slots.get_last_slot()
        return not last_slot.end

    # -------------
    # -- Summary --
    # -------------

    def summary(self, start: Datetime, end: Datetime, keywords: list = None) -> Timedelta:
        """Get the amount of time that has been worked in the given timeframe.

        Args:
            start (Date): The start of the timeframe.
            end (Date): The end of the timeframe.
            keywords (list, optional): Keywords that have to be
            contained in the slots descriptions to be counted. Defaults to [].

        Returns:
            Timedelta: The amount of time worked.
        """
        if not keywords:
            keywords = []
        duration = Timedelta()
        for slot in self.slots.get_slots_between(start, end):
            if not slot.has_keywords(keywords):
                continue
            slot_end = slot.end if slot.end else Datetime.now().astimezone()
            duration += min(slot_end, end) - max(slot.start, start)
        return duration

    def to_be_done(self, start: Datetime, end: Datetime) -> Timedelta:
        """Get the amount of time to be done in the given timeframe.

        Args:
            start (Date): The start of the timeframe.
            end (Date): The end of the timeframe.

        Returns:
            Timedelta: The amount of time to still be worked.
        """
        duration = Timedelta()
        current_day = start
        vacations = self.vacations.get_slots_between(start, end)

        while current_day < end:
            # See if we're on vacation on this day
            is_vacation = False
            for vacation in vacations:
                if vacation.start <= current_day <= vacation.end:
                    is_vacation = True

            # leave the day out if holiday or weekend or on vacation
            if current_day.date() in self.holidays or current_day.weekday() not in self.contract.work_days or is_vacation:
                pass
            else:
                duration += Timedelta(hours=self.contract.get_hours_per_day())
            current_day += Timedelta(days=1)
            current_day = current_day.astimezone()
        return duration

    def free_days_between(self, start: Datetime, end: Datetime) -> dict:
        """Get the holidays in the given timeframe.

        Args:
            start (Date): The start of the timeframe.
            end (Date): The end of the timeframe.

        Returns:
            list: The list of holidays.
        """

        vacations = self.vacations.get_slots_between(start, end)

        recent_holidays = {}
        current_day = start
        while current_day <= end:
            # See if we're on vacation on this day
            for vacation in vacations:
                # Skip if we're on a weekend.
                if current_day.weekday() in [5,6]:
                    continue
                if vacation.start <= current_day <= vacation.end:
                    recent_holidays[current_day] = vacation.description
                    continue

            if current_day in self.holidays:
                recent_holidays[current_day] = self.holidays.get(current_day)
            current_day += Timedelta(days=1)
            current_day = current_day.astimezone()

        return recent_holidays

    # ----------------
    # -- Navigation --
    # ----------------

    def list_dir(self, mode: str | None, date: Datetime, keywords: list|None = None) -> None:
        """Attempt to provide a navigatable interface though the data.

        Args:
            mode (str | None): either year, month or day.
            date (Date): A reference Date.
            keywords (list, optional): Keywords to filter. Defaults to [].
        """
        if not keywords:
            keywords = []
        # maps the input type to the correct values
        val_map = {
            'year': '%B %Y',  # if we are given a year we display its months
            'month': '%d %B %Y',  # if we are given a month we display its days
            'day': '%d %B %Y %H:%M',  # if day we return its slots
            'slot': None
        }
        res = []

        for slot in self.slots.data:
            if not slot.has_keywords(keywords):
                continue

            start_datetime = datetime_from_string(slot.startstart)

            ref_val = None
            check_val = None
            # default to year
            val = start_datetime.strftime("%Y")

            if mode in val_map:
                ref_val = getattr(date, mode, None)
                check_val = getattr(start_datetime, mode, None)

                # return the slots if the input is a day

                if mode == 'slot':
                    ref_val = date.strftime(val_map['day'])
                    check_val = start_datetime.strftime(val_map['day'])
                    if check_val == ref_val:
                        return slot
                    continue

                val = start_datetime.strftime(val_map[mode])
                if mode == 'day':
                    ref_val = date.strftime(val_map['month'])
                    check_val = start_datetime.strftime(val_map['month'])
                    val = slot
                if mode == 'month':
                    ref_val = date.strftime(val_map['year'])
                    check_val = start_datetime.strftime(val_map['year'])

            if val not in res and check_val == ref_val:
                res.append(val)

        return res

    # -------------
    # -- Helpers --
    # -------------

    def next_workday(self, datetime: Datetime) -> Datetime:
        """Find the next free workday.

        Args:
            datetime (Datetime): The date from which shoul be searched.

        Returns:
            Datetime: The next free workday.
        """
        # take the next day as long as the current day is a holiday or weekend
        while (datetime.weekday() in [5, 6]) or (datetime.date() in self.holidays):
            datetime += Timedelta(days=1)
        return datetime

    def take_vacation(self, start: Datetime, end: Datetime, description: str):
        """Add vacation slot to the to the holidays.

        Args:
            datetme (start): The start of the vacation
            datetime (end): The end of the vacation
            str (description): The descripton for the vacation
        """
        vacation = Slot(start, end, description)
        self.vacations.add_slot(vacation)
        self.vacations.save()

