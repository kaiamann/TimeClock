"""Does Stuff."""
from datetime import datetime, date, timedelta
import os
import csv
import holidays
from storage import Storage
from utils import format_datetime, format_date, format_duration, read_stdin, has_keywords, datetime_from_string

class TimeClock:
    """A class for tracking working hours."""

    def __init__(self,
                 storage: Storage,
                 hoursPerDay: int,
                 daysOffPerMonth: int,
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
        self.hoursPerDay = hoursPerDay
        self.daysOffPerMonth = daysOffPerMonth
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
        now = datetime.now()
        if now.date() in self.holidays:
            now = self.__findNextWorkday(now)
            print("Today is a free day moving to " + format_date(now.date()))

        if self.isStarted():
            description = read_stdin()
            self.finish(now, description)
        else:
            self.start(now)

        self.storage.save()

    def start(self, start: datetime) -> None:
        """Start the time tracking.

        Args:
            start (datetime): The point in time where tracking should begin.
        """
        self.storage.create_slot(start)
        formattedDate = format_date(start.date())
        time = format_datetime(start, True)
        print("%s: Starting at %s." % (formattedDate, time))

    def finish(self, end: datetime, description: str) -> None:
        """Finish the time tracking.

        Args:
            end (datetime): The point in time where tracking should stop.
            description (str): The description of what has been done.
        """
        start = self.storage.get_last_slot()['start']
        self.storage.edit_slot(start, start, end, description)

        formattedDate = format_date(end)
        time = end.strftime("%H:%M")

        print("%s: Ending at %s. Worked for: %s" %
              (formattedDate, time, end - start))

    def isStarted(self) -> bool:
        """Check if there is an open slot that needs to be closed.

        Returns:
            bool: True if there is an open slot False otherwise.
        """
        lastSlot = self.storage.get_last_slot()
        return lastSlot and 'end' not in lastSlot

    # -------------
    # -- Summary --
    # -------------

    def summary(self, start: date, end: date, keywords: list = []) -> timedelta:
        """Get the amount of time that has been worked in the given timeframe.

        Args:
            start (date): The start of the timeframe.
            end (date): The end of the timeframe.
            keywords (list, optional): Keywords that have to be contained in the slots descriptions to be counted. Defaults to [].

        Returns:
            timedelta: The amount of time worked.
        """
        duration = timedelta()
        for slot in self.storage.get_slots_between(start, end, keywords):
            if not has_keywords(slot, keywords):
                continue
            duration += slot['end'] - slot['start']

        return duration

    def toBeDone(self, start: date, end: date) -> timedelta:
        """Get the amount of time to be done in the given timeframe.

        Args:
            start (date): The start of the timeframe.
            end (date): The end of the timeframe.

        Returns:
            timedelta: The amount of time to still be worked.
        """
        duration = timedelta()
        currentDay = start
        while currentDay <= end:
            # leave the day out if holiday or weekend
            if (currentDay not in self.holidays) and (currentDay.weekday() not in [5, 6]):
                duration += timedelta(hours=self.hoursPerDay)
            currentDay += timedelta(days=1)
        return duration

    def holidaysBetween(self, start: date, end: date) -> list:
        """Get the holidays in the given timeframe.

        Args:
            start (date): The start of the timeframe.
            end (date): The end of the timeframe.

        Returns:
            list: The list of holidays.
        """
        recentHolidays = {}
        currentDay = start
        while currentDay <= end:
            if currentDay in self.holidays:
                recentHolidays[currentDay] = self.holidays.get(currentDay)
            currentDay += timedelta(days=1)

        return recentHolidays

    # ----------------
    # -- Navigation --
    # ----------------

    # TODO: move this to storage
    def ls(self, mode: str | None, date: date, keywords: list = []) -> None:
        """Attempt to provide a navigatable interface though the data.

        Args:
            mode (str | None): either year, month or day.
            date (date): A reference date.
            keywords (list, optional): Keywords to filter. Defaults to [].
        """
        # maps the input type to the correct values
        valMap = {
            'year': '%B %Y',  # if we are given a year we display its months
            'month': '%d %B %Y',  # if we are given a month we display its days
            'day': '%d %B %Y %H:%M',  # if day we return its slots
            'slot': None
        }
        res = []

        for slot in self.storage.data:
            if not has_keywords(slot, keywords):
                continue

            startDatetime = datetime_from_string(slot["start"])

            refVal = None
            checkVal = None
            # default to year
            val = startDatetime.strftime("%Y")

            if mode in valMap:
                refVal = getattr(date, mode, None)
                checkVal = getattr(startDatetime, mode, None)

                # return the slots if the input is a day

                if mode == 'slot':
                    refVal = date.strftime(valMap['day'])
                    checkVal = startDatetime.strftime(valMap['day'])
                    if checkVal == refVal:
                        return slot
                    else:
                        continue

                val = startDatetime.strftime(valMap[mode])
                if mode == 'day':
                    refVal = date.strftime(valMap['month'])
                    checkVal = startDatetime.strftime(valMap['month'])
                    val = slot
                if mode == 'month':
                    refVal = date.strftime(valMap['year'])
                    checkVal = startDatetime.strftime(valMap['year'])

            if val not in res and checkVal == refVal:
                res.append(val)

        return res

    # ------------
    # -- Export --
    # ------------

    def _getExportData(self, start: datetime, end: datetime) -> list:
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

    def exportMonth(self, date: datetime = datetime.now()) -> None:
        """Attempt to export some data into a csv file.

        Args:
            month (datetime, optional): A reference date. Defaults to datetime.now().
        """
        month = date.strftime("%B %Y")
        path = os.path.join(self.storage, "%s.csv" % month)

        # TODO: fix this
        data = self._getExportData(date)

        with open(path, "w", newline='') as csvfile:
            fieldnames = ['day', 'start', 'end', 'duration', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for slot in data:
                writer.writerow(slot)

    # -------------
    # -- Helpers --
    # -------------

    def __findNextWorkday(self, d: datetime):
        while (d.weekday() in [5, 6]) or (d.date() in self.holidays):
            d += timedelta(days=1)
        return d
