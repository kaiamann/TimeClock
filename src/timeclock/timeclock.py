"""Module that allows tracking of working hours."""

from datetime import datetime as Datetime
from datetime import timedelta as Timedelta

import holidays

from .storage import Storage
from .utils import datetime_from_string


class TimeClock:
    """A class for tracking working hours."""

    def __init__(
        self,
        storage: Storage,
        holiday_storage: Storage,
        hours_per_day: int,
        days_off_per_month: int,
        locale: str,
        subdiv: str | None = None,
    ) -> None:
        """Initialize the TimeClock object.

        Args:
            storage (Storage): Storage for data handling.
            hours_per_day (int): The workload per day in hours.
            days_off_per_month (int): Description of the work.
            locale (str): The locale, where the user is located.
            subdiv (str | None, optional): The locale subdivision. Defaults to None.
        """
        # load config and copy values
        self.storage: Storage = storage
        self.holiday_storage: Storage = holiday_storage
        self.hours_per_day: int = hours_per_day
        self.days_off_per_month: int = days_off_per_month
        self.locale: str = locale
        self.subdiv: str | None = subdiv

        # get the holidays for the locale
        self.holidays = holidays.country_holidays(locale, subdiv=subdiv)

    # -------------------
    # -- Time Tracking --
    # -------------------

    def start(self, start: Datetime) -> None:
        """Start the time tracking.

        Args:
            start: The point in time where tracking should begin.
        """
        self.storage.create_slot(start)

    def finish(self, end: Datetime, description: str) -> Datetime:
        """Finish the time tracking.

        Args:
            end: The point in time where tracking should stop.
            description: The description of what has been done.

        Returns:
            Datetime: The start Datetime when the slot was started.
        """
        start = self.storage.get_last_slot().start
        self.storage.edit_slot(start, start, end, description)
        return start

    def is_started(self) -> bool:
        """Check if there is an open slot that needs to be closed.

        Returns:
            bool: True if there is an open slot False otherwise.
        """
        last_slot = self.storage.get_last_slot()
        return not last_slot.end

    # -------------
    # -- Summary --
    # -------------

    def summary(
        self,
        start: Datetime,
        end: Datetime,
        keywords: list | None = None,
    ) -> Timedelta:
        """Get the amount of time that has been worked in the given timeframe.

        Args:
            start: The start of the timeframe.
            end: The end of the timeframe.
            keywords: Keywords that have to be
            contained in the slots descriptions to be counted. Defaults to [].

        Returns:
            Timedelta: The amount of time worked.
        """
        if not keywords:
            keywords = []
        duration = Timedelta()
        for slot in self.storage.get_slots_between(start, end, keywords):
            if not slot.has_keywords(keywords):
                continue
            slot_end = slot.end if slot.end else Datetime.now().astimezone()
            duration += min(slot_end, end) - max(slot.start, start)
        return duration

    def to_be_done(self, start: Datetime, end: Datetime) -> Timedelta:
        """Get the amount of time to be done in the given timeframe.

        Args:
            start: The start of the timeframe.
            end: The end of the timeframe.

        Returns:
            Timedelta: The amount of time to still be worked.
        """
        duration = Timedelta()
        current_day = start
        vacations = self.holiday_storage.get_slots_between(start, end)

        while current_day < end:
            # See if we're on vacation on this day
            is_vacation = False
            for vacation in vacations:
                if vacation.start <= current_day <= vacation.end:
                    is_vacation = True

            # leave the day out if holiday or weekend or on vacation
            if (
                current_day.date() in self.holidays
                or current_day.weekday() in [5, 6]
                or is_vacation
            ):
                pass
            else:
                duration += Timedelta(hours=self.hours_per_day)
            current_day += Timedelta(days=1)
            current_day = current_day.astimezone()
        return duration

    def free_days_between(self, start: Datetime, end: Datetime) -> dict:
        """Get the holidays in the given timeframe.

        Args:
            start: The start of the timeframe.
            end: The end of the timeframe.

        Returns:
            dict: The list of holidays.
        """

        vacations = self.holiday_storage.get_slots_between(start, end)

        recent_holidays = {}
        current_day = start
        while current_day <= end:
            # See if we're on vacation on this day
            for vacation in vacations:
                # Skip if we're on a weekend.
                if current_day.weekday() in [5, 6]:
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

    def list_dir(
        self, mode: str | None, date: Datetime, keywords: list | None = None
    ) -> None:
        """Attempt to provide a navigatable interface though the data.

        Args:
            mode: either year, month or day.
            date: A reference Datetime.
            keywords: Keywords to filter. Defaults to [].
        """
        if not keywords:
            keywords = []
        # maps the input type to the correct values
        val_map = {
            "year": "%B %Y",  # if we are given a year we display its months
            "month": "%d %B %Y",  # if we are given a month we display its days
            "day": "%d %B %Y %H:%M",  # if day we return its slots
            "slot": None,
        }
        res = []

        for slot in self.storage.data:
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

                if mode == "slot":
                    ref_val = date.strftime(val_map["day"])
                    check_val = start_datetime.strftime(val_map["day"])
                    if check_val == ref_val:
                        return slot
                    continue

                val = start_datetime.strftime(val_map[mode])
                if mode == "day":
                    ref_val = date.strftime(val_map["month"])
                    check_val = start_datetime.strftime(val_map["month"])
                    val = slot
                if mode == "month":
                    ref_val = date.strftime(val_map["year"])
                    check_val = start_datetime.strftime(val_map["year"])

            if val not in res and check_val == ref_val:
                res.append(val)

        return res

    # -------------
    # -- Helpers --
    # -------------

    def next_workday(self, datetime: Datetime) -> Datetime:
        """Find the next free workday.

        Args:
            datetime: The date from which should be searched.

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
            start: The start of the vacation
            end: The end of the vacation
        """
        self.holiday_storage.create_slot(start)
        self.holiday_storage.edit_slot(start, start, end, description)
        self.holiday_storage.save()
