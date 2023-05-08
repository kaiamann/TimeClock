from datetime import datetime, date, timedelta
import os
import csv
import holidays
from storage import Storage
from utils import *

# TODO: store the config file in the correct canonical location
CONFIG_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "config.yml")

# DEFAULT_PATH = os.path.expanduser('~')
# DEFAULT_FILENAME = "TimeClock.json"

class TimeClock:
    # TODO: pull params out of the dict into constructor signature
    def __init__(self, 
                 storage: Storage,
                 hoursPerDay: int, 
                 daysOffPerMonth: int,
                 locale: str,
                 subdiv: str|None = None,
                 ) -> None:
        # load config and copy values
        self.storage = storage
        self.hoursPerDay = hoursPerDay
        self.daysOffPerMonth = daysOffPerMonth
        self.locale = locale
        self.subdiv = subdiv

        # get the holidays for the locale
        self.holidays = holidays.country_holidays(locale, subdiv=subdiv)

    def isStarted(self):
        lastSlot = self.storage.getLastSlot()
        return lastSlot and not 'end' in lastSlot

    def finish(self, end: datetime, description: str):
        start = datetimeFromString(self.storage.getLastSlot()['start'])
        print(self.storage.editSlot(start, start, end, description))

        formattedDate = formatDate(end)
        time = end.strftime("%H:%M")

        print("%s: Ending at %s. Worked for: %s" %
              (formattedDate, time, end - start))

    def start(self, start: datetime):
        formattedDatetime = formatDatetime(start)
        slot = {"start": formattedDatetime}
        self.data.append(slot)

        formattedDate = formatDate(start)
        time = formatTime(start)
        print("%s: Starting at %s." % (formattedDate, time))

    def track(self):
        now = datetime.now()
        if now.date() in self.holidays:
            now = self.findNextWorkday(now)
            print("Today is a free day moving to " + formatDate(now.date()))
            
        if self.isStarted():
            description = readStdin()
            self.finish(now, description)
        else:
            self.start(now)

        self.storage.save()
    
    def summary(self, start: date, end: date, keywords: list = []):
        duration = timedelta()

        for slot in self.data:
            if not hasKeywords(slot, keywords):
                continue

            slotStart = datetimeFromString(slot["start"])
            slotStartDate = slotStart.date()

            slotEnd = datetime.now()

            if "end" in slot:
                slotEnd = datetimeFromString(slot["end"])

            if slotStartDate >= start and slotStartDate <= end:
                duration += slotEnd - slotStart
        
        return duration
    
    def toBeDone(self, start: date, end: date):
        duration = timedelta()
        currentDay = start
        while currentDay <= end:
            # leave the day out if holiday or weekend
            if (currentDay not in self.holidays) and (currentDay.weekday() not in [5,6]):
                duration += timedelta(hours=self.hoursPerDay)
            currentDay += timedelta(days=1)
        return duration

    def recentHolidays(self, start: date, end: date):
        recentHolidays = {}
        currentDay = start
        while currentDay <= end:
            if currentDay in self.holidays:
                recentHolidays[currentDay] = (self.holidays.get(currentDay))
            currentDay += timedelta(days=1)
        
        return recentHolidays

    def ls(self, mode: str|None, date: date, keywords : list = []):
        # maps the input type to the correct values 
        valMap = {
            'year' : '%B %Y', # if we are given a year we display its months
            'month': '%d %B %Y', # if we are given a month we display its days
            'day' : '%d %B %Y %H:%M', # if we are given a day we return its slots
            'slot': None
        }
        res = []

        for slot in self.data:
            if not hasKeywords(slot, keywords):
                continue

            startDatetime = datetimeFromString(slot["start"])

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

    def getExportData(self, month: datetime):
        csvData = []
        for slot in self.data:
            startDatetime = datetimeFromString(slot["start"])
            endDatetime = datetimeFromString(slot["end"])
            if (startDatetime.month == month.month and startDatetime.year == month.year):
                slotDict = {
                    "day": startDatetime.strftime("%d.%m.%Y"),
                    "start": startDatetime.strftime("%H:%M"),
                    "end": endDatetime.strftime("%H:%M"),
                    "duration": formatDuration(endDatetime - startDatetime),
                    "description": slot['description'] if "description" in slot else ""
                }
                csvData.append(slotDict)

        return csvData

    def exportMonth(self, month: datetime = datetime.now()):
        monthName = month.strftime("%B %Y")
        exportFilepath = os.path.join(self.dataDir, "%s.csv" % (monthName))

        exportData = self.getExportData(month)

        with open(exportFilepath, "w", newline='') as csvfile:
            fieldnames = ['day', 'start', 'end', 'duration', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for slot in exportData:
                writer.writerow(slot)


    def findNextWorkday(self, d: datetime):
        while (d.weekday() in [5,6]) or (d.date() in self.holidays):
            d += timedelta(days=1)
        return d


def hasKeywords(slot, keywords):
    # Filter for relevant keywords
    relevant = True
    for keyword in keywords:
        if not 'description' in slot or keyword not in slot['description']:
            relevant = False
            break
    return relevant
