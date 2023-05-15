"""Does Stuff."""
from datetime import(
    datetime as Datetime,
    date as Date,
    timedelta as Timedelta
)
import os
import csv
import holidays
from .storage import Storage
from .utils import format_datetime, format_date, format_duration, read_stdin, has_keywords, datetime_from_string

class TimeClock:
    """A class for tracking working hours."""

    def __init__(self,
                 storage: Storage,
                 hours_per_day: int,
                 days_off_per_month: int,
                 locale: str,
                 subdiv: str | None = None,
                 ) -> None:
        """Initilize the TimeClock object.

        Args:
            storage (Storage): Storage for data handling.
            hoursPerDay (int): The work pensum per day in hours.
            daysOffPerMonth (int): Description of the work.
            locale (str): The locale, where the user is located.
            subdiv (str | None, optional): The locale subdivision. Defaults to None.
        """
        # load config and copy values
        self.storage = storage
        self.hours_per_day = hours_per_day
        self.days_off_per_month = days_off_per_month
        self.locale = locale
        self.subdiv = subdiv

        # get the holidays for the locale
        self.holidays = holidays.country_holidays(locale, subdiv=subdiv)

    # -------------------
    # -- Time Tracking --
    # -------------------

    def track(self) -> None:
        """Track working hours.

        Starts tracking time if no slot is open.
        Closes the current open slot otherwise.
        """
        now = Datetime.now()
        if now.date() in self.holidays:
            now = self._next_workday(now)
            print("Today is a free day moving to " + format_date(now.date()))

        if self.is_started():
            description = read_stdin()
            self.finish(now, description)
        else:
            self.start(now)

        self.storage.save()

    def start(self, start: Datetime) -> None:
        """Start the time tracking.

        Args:
            start (Datetime): The point in time where tracking should begin.
        """
        self.storage.create_slot(start)
        formatted_date = format_date(start.date())
        time = format_datetime(start, True)
        print(f"{formatted_date}: Starting at {time}.")

    def finish(self, end: Datetime, description: str) -> None:
        """Finish the time tracking.

        Args:
            end (Datetime): The point in time where tracking should stop.
            description (str): The description of what has been done.
        """
        start = self.storage.get_last_slot()['start']
        self.storage.edit_slot(start, start, end, description)

        formatted_date = format_date(end)
        time = end.strftime("%H:%M")

        print(f"{formatted_date}: Ending at {time}. Worked for: {end-start}")

    def is_started(self) -> bool:
        """Check if there is an open slot that needs to be closed.

        Returns:
            bool: True if there is an open slot False otherwise.
        """
        last_slot = self.storage.get_last_slot()
        return last_slot and 'end' not in last_slot

    # -------------
    # -- Summary --
    # -------------

    def summary(self, start: Date, end: Date, keywords: list = None) -> Timedelta:
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
        for slot in self.storage.get_slots_between(start, end, keywords):
            if not has_keywords(slot, keywords):
                continue
            duration += slot['end'] - slot['start']

        return duration

    def to_be_done(self, start: Date, end: Date) -> Timedelta:
        """Get the amount of time to be done in the given timeframe.

        Args:
            start (Date): The start of the timeframe.
            end (Date): The end of the timeframe.

        Returns:
            Timedelta: The amount of time to still be worked.
        """
        duration = Timedelta()
        current_day = start
        while current_day <= end:
            # leave the day out if holiday or weekend
            if (current_day not in self.holidays) and (current_day.weekday() not in [5, 6]):
                duration += Timedelta(hours=self.hours_per_day)
            current_day += Timedelta(days=1)
        return duration

    def holidays_between(self, start: Date, end: Date) -> list:
        """Get the holidays in the given timeframe.

        Args:
            start (Date): The start of the timeframe.
            end (Date): The end of the timeframe.

        Returns:
            list: The list of holidays.
        """
        recent_holidays = {}
        current_day = start
        while current_day <= end:
            if current_day in self.holidays:
                recent_holidays[current_day] = self.holidays.get(current_day)
            current_day += Timedelta(days=1)

        return recent_holidays

    # ----------------
    # -- Navigation --
    # ----------------

    def ls(self, mode: str | None, date: Date, keywords: list = None) -> None:
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

        for slot in self.storage.data:
            if not has_keywords(slot, keywords):
                continue

            start_datetime = datetime_from_string(slot["start"])

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

    # ------------
    # -- Export --
    # ------------

    def _getExportData(self, start: Datetime, end: Datetime) -> list:
        csvData = []
        for slot in self.storage.get_slots_between(start, end):
            start = slot["start"]
            end = slot["end"]
            slotDict = {
                "day": start.strftime("%d.%m.%Y"),
                "start": start.strftime("%H:%M"),
                "end": end.strftime("%H:%M"),
                "duration": format_duration(end - start),
                "description": slot['description'] if "description" in slot else ""
            }
            csvData.append(slotDict)
        return csvData

    def exportMonth(self, datetime: Datetime = Datetime.now()) -> None:
        """Attempt to export some data into a csv file.

        Args:
            month (Datetime, optional): A reference date. Defaults to Datetime.now().
        """
        month = datetime.strftime("%B %Y")
        path = os.path.join(self.storage, "%s.csv" % month)

        # TODO: fix this
        data = self._getExportData(datetime)

        with open(path, "w", newline='') as csvfile:
            fieldnames = ['day', 'start', 'end', 'duration', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for slot in data:
                writer.writerow(slot)

    # -------------
    # -- Helpers --
    # -------------

    def _next_workday(self, datetime: Datetime):
        while (datetime.weekday() in [5, 6]) or (datetime.date() in self.holidays):
            datetime += Timedelta(days=1)
        return datetime
