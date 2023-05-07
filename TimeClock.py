from datetime import datetime, date, timedelta
import os
import json
import argparse
import sys
import csv
import re
import holidays
from subprocess import call
import yaml
import pycountry
import inquirer
import pyfiglet
import git


# TODO: store the config file in the correct canonical location
CONFIG_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "config.yml")
EDITOR = os.environ.get('EDITOR', 'code')

# DEFAULT_PATH = os.path.expanduser('~')
# DEFAULT_FILENAME = "TimeClock.json"

class TimeClock:
    # TODO: pull params out of the dict into constructor signature
    def __init__(self, config: dict) -> None:
        # load config and copy values
        self.dataDir = config['data_dir']
        self.filename = config['file_name']
        self.hoursPerDay = config['hours_per_day']
        self.daysOffPerMonth = config['days_off_per_month']

        # see if there was a subdiv
        subdiv = config['locale_subdiv'] if 'locale_subdiv' in config else None
        # get the holidays for the locale
        self.holidays = holidays.country_holidays(config['locale'], subdiv=subdiv)

        # assemble the full path for more conventient usage
        self.dataPath = os.path.join(self.dataDir, self.filename)

        self.repo = getGitRepoWithRemote(self.dataDir)

        # load data from the JSON
        self.readData()

    @staticmethod
    def buildFromConfig(configPath: str = CONFIG_PATH):
        f = open(configPath, mode='r', encoding="utf-8")
        config = yaml.safe_load(f)
        return TimeClock(config)

    def readData(self):
        try:
            f = open(self.dataPath)
            self.data = json.load(f)
            return True
        except Exception:
            self.data = []
            return False

    def writeData(self, mode="w+", data: list = []):
        try:
            f = open(self.dataPath, mode, encoding="utf-8")
            json.dump(data, f)
        except FileNotFoundError as e:
            print(e)


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
        if now.date() in self.holidays:
            now = self.findNextWorkday(now)
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
    
    def commit(self):
        # get changed files
        changedFiles = list(item.a_path for item in self.repo.index.diff(None))
        if len(changedFiles) < 1:
            print("Nothing to commit. Aborting")
            return

        if isBehind(self.repo):
            print("Your repo seems to be behind the remote. Please pull first.")

        # add modified files
        self.repo.index.add(changedFiles)
        # and commit
        self.repo.index.commit("Added working hours for %s" % (formatDate(date.today())))
        print(self.repo.head.commit.message)

    def push(self):
        self.repo.git.push()
    
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
        exportFilepath = os.path.join(self.dataDir, "%s.csv" % (monthName))

        exportData = self.getExportData(month)

        with open(exportFilepath, "w", newline='') as csvfile:
            fieldnames = ['day', 'start', 'end', 'duration', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for slot in exportData:
                writer.writerow(slot)

    def edit(self, editor: str):
        editor = editor if editor else EDITOR
        call([editor, self.dataPath])


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

def getGitRepoWithRemote(path: str):
    remote = None
    try:
        repo = git.Repo(path)
    except git.InvalidGitRepositoryError:
        print("%s is not a git repository. Git functionality not available." % (path))
        return repo

    # also check if there is a remote
    if not repo.remotes:
        print("The git repository at %s does not seem to have a remote. Git functionality not available." % (path))
        return repo

    remote = repo.remotes[0]
    # fetch from remote
    remote.fetch()

    return repo

def isBehind(repo: git.Repo):
    # see if we're behind the remote
    commits_behind = repo.iter_commits('main..origin/main')
    return sum(1 for _ in commits_behind) > 0


# Command line handlers

def track(args):
    timeClock = TimeClock.buildFromConfig()
    timeClock.track()

def commit(args):
    timeClock = TimeClock.buildFromConfig()
    timeClock.commit()

def push(args):
    timeClock = TimeClock.buildFromConfig()
    timeClock.push()

def summary(args):
    """Routine to print a summary for the chosen period

    Args:
        args (dict): The arguments from the argparser
    """
    args = vars(argparser.parse_args())
    timeClock = TimeClock.buildFromConfig()

    # handle date
    inputDate = date.today()
    if args['date']:
        inputDate = datetime.strptime(args['date'], '%d %B %Y').date()

    # default to day mode
    start = inputDate
    end = inputDate

    # set start end end for multi day modes
    if args['week']:
        start, end = getWeek(inputDate)
    if args['month']:
        start, end = getMonth(inputDate)

    # handle keywords
    keywords = []
    if args['keywords']:
        keywords = re.split(' ', args['keywords'])

    duration = timeClock.summary(start, end, keywords)
    tbd = timeClock.toBeDone(start, end)
    recentHolidays = timeClock.recentHolidays(start, end)

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
    args = vars(argparser.parse_args())
    timeClock = TimeClock.buildFromConfig()

    if not timeClock.isStarted():
        month = datetime.strptime(args['month'], "%B %Y") if args['month'] else datetime.now()
        timeClock.exportMonth(month)
    else:
        print("Please finish the current work session before trying to export.")
    pass

def edit(args):
    """Routine to edit the JSON file with the chosen editor

    Args:
        args (dict): The args from the argparser
    """
    args = vars(argparser.parse_args())
    timeClock = TimeClock.buildFromConfig()
    timeClock.edit(args['editor'])


def ls(args):
    args = vars(argparser.parse_args())
    timeClock = TimeClock.buildFromConfig()

    # handle date
    date = datetime.now().date()
    mode = None
    if args['date']:
        date, mode = parseDate(args['date'])

    # handle keywords
    keywords = []
    if args['keywords']:
        keywords = re.split(' ', args['keywords'])

    res = timeClock.ls(mode, date, keywords)
    print(res)
    return res


def init(args):
    """Initializes the TimeClock

    Asks the user for important configuration parameters:

    data_dir: The directory where the JSON file is stored
    file_name: The name of the JSON file
    work_hours_per_day: duh
    days_off_per_month: duh
    locale: The current locale of the user to fetch local holidays

    Args:
        args (dirct): The arguments from the argparser
    """
    # print header
    figlet = pyfiglet.Figlet(font="big")
    print(figlet.renderText("TimeClock"))

    locales = holidays.list_supported_countries()
    # filter out all the country codes that don't exist in pycountry
    countryCodes = list(filter(lambda x: pycountry.countries.get(alpha_2=x), locales))
    # get the country names
    countryNames = list(sorted(map(lambda x: pycountry.countries.get(alpha_2=x).name, countryCodes)))

    questions = [
        inquirer.Path('data_dir',
                        message= "In which directory should the data be stored?",
                        default= os.path.join(os.path.expanduser('~'),"Documents","TimeClock") + os.path.sep
                    ),
        inquirer.Path('file_name',
                        message= "What shoud the file be named?",
                        default= "TimeClock.json"
                    ),
        inquirer.List('hours_per_day',
                        message="How many hours to you work per day?",
                        choices=range(1,9,1),
                        default=8
                    ),
        inquirer.List('days_off_per_month',
                        message="How many days do you have off per month?",
                        choices=list(map(lambda x: x/2, range(0,7,1))),
                        default=3
                    ),
        inquirer.List('locale',
                        message="Where do you live?",
                        choices=countryNames,
                    ),
        ]
    config = inquirer.prompt(questions)

    # do nothing if no config
    if not config:
        return
    
    # get the country code from the human readable name
    country = pycountry.countries.get(name=config['locale'])
    countryCode= country.alpha_2
    # save the code instead of the name
    config['locale'] = countryCode

    # get the subdivs from the  holidays module
    subdivCodes = locales[country.alpha_2]

    # filter the ones that are not in holiday subdivs
    if subdivCodes:
        # get the name of subdiv type. E.g. "Kanton", "State", etc.
        subdivType = list(pycountry.subdivisions.get(country_code=countryCode))[0].type

        # filter the ones that dont have a name...
        # TODO: some subdivs have a three letter code... figure out what's up with that
        subdivCodes = list(filter(lambda x: pycountry.subdivisions.get(code="%s-%s" % (countryCode, x)),subdivCodes))
        def f(code):
            name = pycountry.subdivisions.get(code="%s-%s" % (countryCode, code)).name
            return (name, code)

        subdivMap = dict(map(f, subdivCodes))
        subdivNames = list(sorted(subdivMap.keys()))

        questions = [
            inquirer.List('subdiv',
                            message="In which %s do you live?" % (subdivType),
                            choices=subdivNames,
                        )
        ]
        subdivConfig = inquirer.prompt(questions)

        if not subdivConfig:
            return
        
        config['locale_subdiv'] = subdivMap[subdivConfig['subdiv']]
        
    print(config)
    # dump to config.yml
    f = open(CONFIG_PATH, "w+", encoding="utf-8")
    yaml.dump(config, f)


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

def getWeek(inputDate: date):
    start = inputDate - timedelta(days=inputDate.weekday())
    end = start + timedelta(days=6)
    return start, end

def getMonth(inputDate: date):
    start = inputDate - timedelta(days=inputDate.day-1)
    nextMonth = inputDate.replace(day=28) + timedelta(days=4)
    end = nextMonth - timedelta(days=nextMonth.day)
    return start, end


if __name__ == '__main__':

    # for date, name in sorted(holidays.US(subdiv='CA', years=2014).items()):
    argparser = argparse.ArgumentParser(
        prog='timeClock',
        description='A time clock for keeping track of working hours.',
        epilog='Calling without arguments will start the tracking process'
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

    # init
    initParser = subparsers.add_parser("init")
    initParser.add_argument(
        '-i',
        '--init',
        help='Initialize the TimeClock'
    )
    initParser.set_defaults(func=init)

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


    # commit
    commitParser = subparsers.add_parser("commit")
    commitParser.set_defaults(func=commit)

    # push
    pushParser = subparsers.add_parser("push")
    pushParser.set_defaults(func=push)
    
    # read the handler and execute
    args = argparser.parse_args()
    args.func(args)
