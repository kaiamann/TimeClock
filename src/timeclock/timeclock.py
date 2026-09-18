"""Module that allows tracking of working hours."""

from datetime import datetime as Datetime
from datetime import timedelta as Timedelta

import holidays

from .storage import Storage
from .utils import datetime_from_string


class TimeClock:
    """A class for tracking working hours.

    Attributes:
        storage: Storage for data handling.
        holiday_storage: Storage for holiday data.
        hours_per_day: The workload per day in hours.
        days_off_per_month: Description of the work.
        locale: The locale, where the user is located.
        subdiv: The locale subdivision. Defaults to None.
    """

    def __init__(
        self,
        storage: Storage,
        holiday_storage: Storage,
        hours_per_day: float,
        days_off_per_month: float,
        locale: str,
        subdiv: str | None = None,
    ) -> None:
        self.storage: Storage = storage
        self.holiday_storage: Storage = holiday_storage
        self.hours_per_day: float = hours_per_day
        self.days_off_per_month: float = days_off_per_month
        self.locale: str = locale
        self.subdiv: str | None = subdiv

        # Get the holidays for the locale.
        self.holidays: holidays.HolidayBase = holidays.country_holidays(
            locale, subdiv=subdiv
        )

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
        last_slot = self.storage.get_last_slot()
        if not last_slot:
            raise Exception("There is started Slot to finish!")
        start = last_slot.start
        _ = self.storage.edit_slot(start, start, end, description)
        return start

    def is_started(self) -> bool:
        """Check if there is an open slot that needs to be closed.

        Returns:
            bool: True if there is an open slot, False otherwise.
        """
        last_slot = self.storage.get_last_slot()
        if not last_slot:
            return False
        return not last_slot.end

    # -------------
    # -- Summary --
    # -------------

    def summary(
        self,
        start: Datetime,
        end: Datetime,
        keywords: list[str] | None = None,
    ) -> Timedelta:
        """Get the amount of time that has been worked in the given timeframe.

        Args:
            start: The start of the timeframe.
            end: The end of the timeframe.
            keywords: Keywords that have to be contained in the slots descriptions.

        Returns:
            Timedelta: The amount of time worked.
        """
        duration = Timedelta()
        slots = self.storage.get_slots_between(start, end, keywords)
        for slot in slots:
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
            # See if we're on vacation on this day.
            is_vacation = False
            for vacation in vacations:
                if vacation.end and vacation.start <= current_day <= vacation.end:
                    is_vacation = True

            is_holiday = current_day.date() in self.holidays
            is_weekend = current_day.weekday() in [5, 6]
            if not is_holiday and not is_weekend and not is_vacation:
                duration += Timedelta(hours=self.hours_per_day)
            current_day += Timedelta(days=1)
            current_day = current_day.astimezone()
        return duration

    def free_days_between(
        self, start: Datetime, end: Datetime
    ) -> dict[Datetime, str | None]:
        """Get the holidays in the given timeframe.

        Args:
            start: The start of the timeframe.
            end: The end of the timeframe.

        Returns:
            dict: The list of holidays.
        """

        vacations = self.holiday_storage.get_slots_between(start, end)

        recent_holidays: dict[Datetime, str | None] = {}
        current_day = start
        while current_day <= end:
            # See if we're on vacation on this day
            for vacation in vacations:
                # Skip if we're on a weekend.
                if current_day.weekday() in [5, 6]:
                    continue
                if vacation.end and vacation.start <= current_day <= vacation.end:
                    recent_holidays[current_day] = vacation.description
                    continue

            if current_day in self.holidays:
                recent_holidays[current_day] = self.holidays.get(current_day)
            current_day += Timedelta(days=1)
            current_day = current_day.astimezone()

        return recent_holidays

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
        _ = self.holiday_storage.edit_slot(start, start, end, description)
        _ = self.holiday_storage.save()
