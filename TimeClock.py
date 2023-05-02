from datetime import datetime, date, timedelta
import os
import json
import argparse
import sys
import csv
import re
import holidays
from subprocess import call
import pathlib


DEFAULT_PATH = os.path.join(
    "%s" % (os.path.expanduser('~')), "Documents", "Arbeitszeit")
DEFAULT_PATH = pathlib.Path(__file__).parent.resolve()
DEFAULT_FILENAME = "TimeClock.json"
HOURS_PER_DAY = 6
DAYS_OFF_PER_MONTH = 2.5


EDITOR = os.environ.get('EDITOR', 'code')
LOCALE = "DE"
local_holidays = holidays.country_holidays(LOCALE)


class TimeClock:
    def __init__(self, filepath: str = os.path.join(DEFAULT_PATH, DEFAULT_FILENAME)) -> None:
        self.filepath = filepath
        self.readData()

    def readData(self):
        try:
            f = open(self.filepath)
            self.data = json.load(f)
            return True
        except Exception:
            self.data = []
            return False

    def writeData(self, mode="w+", data: list = []):
        f = open(self.filepath, mode, encoding="utf-8")
        json.dump(data, f)

    def isStarted(self):
        return self.data and not 'end' in self.data[-1]

    def finish(self, end: datetime, description: str):
        self.data[-1]['end'] = formatDatetime(end)
        self.data[-1]['description'] = description

        start = datetimeFromString(self.data[-1]['start'])
        formattedDate = formatDate(end)
        time = end.strftime("%H:%M")

        print("%s: Ending at %s. Worked for: %s" %
              (formattedDate, time, end - start))

    def start(self, start: datetime):
        formattedDatetime = formatDatetime(start)
        period = {"start": formattedDatetime}
        self.data.append(period)

        formattedDate = formatDate(start)
        time = formatTime(start)
        print("%s: Starting at %s." % (formattedDate, time))
    
    def takeLeave(self, start: date, days: int):
        end = start + timedelta(days)

        formattedStart = formatDatetime(datetime.combine(date.start(), datetime.min.time()))
        formattedEnd = formatDatetime(end)
        period = {
            "start": formattedStart,
            "end": formattedEnd,
            "off": True
        }

        self.data.append(period)

        formattedDate = formatDate(start)
        time = formatTime(start)
        print("Taking days off from %s - %s" % (formattedStartDate, formattedEndDate))


    def track(self):
        now = datetime.now()
        if now.date() in local_holidays:
            now = findNextWorkday(now)
            print("Today is a free day moving to " + formatDate(now.date()))
            
        if self.isStarted():
            description = readStdin()
            self.finish(now, description)
        else:
            self.start(now)

        self.writeData(data=self.data)
    
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
            if (currentDay not in local_holidays) and (currentDay.weekday() not in [5,6]):
                duration += timedelta(hours=HOURS_PER_DAY)
            currentDay += timedelta(days=1)
        return duration

    def holidays(self, start: date, end: date):
        recentHolidays = {}
        currentDay = start
        while currentDay <= end:
            if currentDay in local_holidays:
                recentHolidays[currentDay] = (local_holidays.get(currentDay))
            currentDay += timedelta(days=1)
        
        return recentHolidays

    
    def updateSlot(self, dt: datetime, start: datetime, end: datetime = datetime.now(), description = ""):
        for i in range(len(self.data)):
            slot = self.data[i]
            slotStart = datetimeFromString(slot['start'])
            if slotStart == dt:
                self.data[i]['start'] = formatDatetime(start)
                self.data[i]['end'] = formatDatetime(end)
                self.data[i]['description'] = description
        
        self.writeData(data=self.data)


    def deleteSlot(self, start: datetime):
        pass

    def getSlot(self, start: str):
        for slot in self.data:
            if slot['start'] == start:
                return slot
        return None
        
    
    
    
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
        exportFilepath = os.path.join(DEFAULT_PATH, "%s.csv" % (monthName))

        exportData = self.getExportData(month)

        with open(exportFilepath, "w", newline='') as csvfile:
            fieldnames = ['day', 'start', 'end', 'duration', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for slot in exportData:
                writer.writerow(slot)

    def edit(self, editor: str):
        editor = editor if editor else EDITOR
        call([editor, self.filepath])


def hasKeywords(slot, keywords):
    # Filter for relevant keywords
    relevant = True
    for keyword in keywords:
        if not 'description' in slot or keyword not in slot['description']:
            relevant = False
            break
    return relevant

def findNextWorkday(d: datetime):
    while (d.weekday() in [5,6]) or (d.date() in local_holidays):
        d += timedelta(days=1)
    return d

def readStdin():
    print("Enter description. Finish by pressing Ctrl+d")
    message = ""
    for line in sys.stdin:
        message += line
    return message

# Date and duration formatting
def formatDuration(duration: timedelta):
    s = duration.total_seconds()
    sign = ""
    if s < 0:
        sign = "-"
        s = -s

    hours = divmod(s, 3600)[0]
    minutes = divmod(s, 60)[0] - hours * 60

    return "%s%0.f Hours %0.f Minutes" % (sign, hours, minutes)

def formatDate(date: date):
    return date.strftime("%d %B %Y")

def formatTime(date: datetime):
    return date.strftime("%H:%M")

def formatDatetime(date: datetime):
    return date.strftime("%d %B %Y %H:%M")

def datetimeFromString(string: str):
    return datetime.strptime(string, "%d %B %Y %H:%M")


# Command line handlers

def track(args):
    args = argparser.parse_args()
    config = vars(args)
    timeClock = TimeClock(config["file"])
    timeClock.track()

def getWeek(inputDate: date):
    start = inputDate - timedelta(days=inputDate.weekday())
    end = start + timedelta(days=6)
    return start, end

def getMonth(inputDate: date):
    start = inputDate - timedelta(days=inputDate.day-1)
    nextMonth = inputDate.replace(day=28) + timedelta(days=4)
    end = nextMonth - timedelta(days=nextMonth.day)
    return start, end

def summary(args):
    args = argparser.parse_args()
    config = vars(args)
    timeClock = TimeClock(config["file"])

    # handle date
    inputDate = date.today()
    if config['date']:
        inputDate = datetime.strptime(config['date'], '%d %B %Y').date()

    # default to day mode
    start = inputDate
    end = inputDate

    # set start end end for multi day modes
    if config['week']:
        start, end = getWeek(inputDate)
    if config['month']:
        start, end = getMonth(inputDate)

    # handle keywords
    keywords = []
    if config['keywords']:
        keywords = re.split(' ', config['keywords'])

    duration = timeClock.summary(start, end, keywords)
    tbd = timeClock.toBeDone(start, end)
    recentHolidays = timeClock.holidays(start, end)

    if duration > tbd:
        pass


    if start == end:
        print("Summary for %s:" % (formatDate(start)))

    else:
        print("Summary for %s - %s:" % (formatDate(start), formatDate(end)))
        if len(recentHolidays) > 0:
            print("%s holiday/s in this period:" % (len(recentHolidays)))
            for d, name in recentHolidays.items():
                weekday = d.strftime("%a")
                print("%s: %s - %s" % (weekday, formatDate(d), name))
    
    print("Worked for: %s" % (formatDuration(duration)))
    print("To be done: %s" % (formatDuration(tbd-duration)))


def export(args):
    args = argparser.parse_args()
    config = vars(args)
    timeClock = TimeClock(config["file"])

    if not timeClock.isStarted():
        month = datetime.strptime(
            config['month'], "%B %Y") if config['month'] else datetime.now()
        timeClock.exportMonth(month)
    else:
        print("Please finish the current work session before trying to export.")
    pass

def edit(args):
    args = argparser.parse_args()
    config = vars(args)
    timeClock = TimeClock(config["file"])
    timeClock.edit(config['editor'])


def ls(args):
    args = argparser.parse_args()
    config = vars(args)
    timeClock = TimeClock(config["file"])


    # handle date
    date = datetime.now().date()
    mode = None
    if config['date']:
        date, mode = parseDate(config['date'])

    # handle keywords
    keywords = []
    if config['keywords']:
        keywords = re.split(' ', config['keywords'])

    res = timeClock.ls(mode, date, keywords)
    print(res)
    return res

def parseDate(dateStr: str):
    if type(dateStr) != str:
        raise ValueError
    try:
        return datetime.strptime(dateStr, '%Y').date(), "year"
    except ValueError:
        pass

    try:
        return datetime.strptime(dateStr, '%B %Y').date(), "month"
    except ValueError:
        pass
    try:
        return datetime.strptime(dateStr, '%d %B %Y').date(), "day"
    except ValueError:
        pass
    try:
        return datetime.strptime(dateStr, '%d %B %Y %H:%M').date(), "slot"
    except ValueError:
        pass

    raise ValueError





if __name__ == '__main__':

    # for date, name in sorted(holidays.US(subdiv='CA', years=2014).items()):


    argparser = argparse.ArgumentParser(
        prog='timeClock',
        description='A time clock for keeping track of working hours.',
        epilog='Calling without arguments will start the tracking process'
    )

    argparser.add_argument(
        '-f',
        '--file',
        default=os.path.join(DEFAULT_PATH, DEFAULT_FILENAME),
        help='the path to the file where time clock information should be saved in. Defaults to %s' % (
            os.path.join(DEFAULT_PATH, DEFAULT_FILENAME))
    )
    argparser.set_defaults(func=track)

    subparsers = argparser.add_subparsers(
        help='refer to timeClock summary -h for further help')

    # create the parser for the "summary" command
    summaryParser = subparsers.add_parser("summary")
    summaryParser.add_argument(
        '-w',
        '--week',
        action="store_true",
        help='provides a summary over the current week. Also works with -d flag for querying another week'
    )
    summaryParser.add_argument(
        '-m',
        '--month',
        action="store_true",
        help='provides a summary over the current month. Also works with -d flag for querying another month'
    )
    summaryParser.add_argument(
        '-d',
        '--date',
        help='provides a summary for a particular date. Dates have to be in d.MMMM.yyyy format. e.g. "11 November 2023". Defaults to the current day.'
    )
    summaryParser.add_argument(
        '-k',
        '--keywords',
        help='Provides a summary for all slots that have particular keywords in their decription'
    )
    summaryParser.set_defaults(func=summary)

    # export
    exportParser = subparsers.add_parser("export")
    exportParser.add_argument(
        '-m',
        '--month',
        help='Exports a specific month to CSV. Specify month in "%B %Y" format. E.g. "December 2022"')

    # edit
    editParser = subparsers.add_parser("edit")
    editParser.add_argument(
        '-e',
        '--editor',
        help='Edit the JSON file storing the timeslots using the specefied editor'
    )
    editParser.set_defaults(func=edit)

    # ls
    lsParser = subparsers.add_parser("ls")
    lsParser.add_argument(
        '-d',
        '--date',
        help='Edit the JSON file storing the timeslots using the specefied editor'
    )
    lsParser.add_argument(
        '-k',
        '--keywords',
        help='Provides a summary for all slots that have particular keywords in their decription'
    )
    lsParser.set_defaults(func=ls)
    
    # read the handler and execute
    args = argparser.parse_args()
    args.func(args)
