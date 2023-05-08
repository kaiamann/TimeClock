from datetime import datetime, date
import os
import argparse
import holidays
from subprocess import call
import re
import yaml
import pycountry
import inquirer
import pyfiglet
import versioncontrol
from timeclock import TimeClock
from storage import JSONStorage
from utils import parseDate, getWeek, getMonth, formatDate, formatDuration

# TODO: store the config file in the correct canonical location
CONFIG_PATH = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), "config.yml")
EDITOR = os.environ.get('EDITOR', 'code')

# DEFAULT_PATH = os.path.expanduser('~')
# DEFAULT_FILENAME = "TimeClock.json"


class CLI:
    """A Command Line Interface that allows the user to track working hours.

    Also provides other functionalities, like exporting and summaries.
    """
    # TODO: pull params out of the dict into constructor signature

    def __init__(self, config: dict) -> None:
        self.storage = "storage"
        self.versionControl = versioncontrol.VersionControl()

        # load config and crecreate objects
        dataDir = config['data_dir']
        fileName = config['file_name']
        storage = JSONStorage(dataDir, fileName)

        hoursPerDay = config['hours_per_day']
        daysOffPerMonth = config['days_off_per_month']
        locale = config['locale']
        subdiv = config['locale_subdiv']
        self.timeClock = TimeClock(
            storage, hoursPerDay, daysOffPerMonth, locale, subdiv)

    @staticmethod
    def buildFromConfig(configPath: str = CONFIG_PATH):
        try:
            f = open(configPath, mode='r', encoding="utf-8")
            config = yaml.safe_load(f)
            return CLI(config)
        except FileNotFoundError:
            return None

    def setArgparser(self, argparser: argparse.ArgumentParser):
        self.argparser = argparser

    # Command line handlers

    def edit(self, editor: str):
        editor = editor if editor else EDITOR
        call([editor, self.dataPath])

    def track(self, args):
        self.timeClock.track()

    def summary(self, args):
        """Routine to print a summary for the chosen period

        Args:
            args (dict): The arguments from the argparser
        """
        args = vars(self.argparser.parse_args())

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

        duration = self.timeClock.summary(start, end, keywords)
        tbd = self.timeClock.toBeDone(start, end)
        recentHolidays = self.timeClock.holidaysBetween(start, end)

        if duration > tbd:
            pass

        if start == end:
            print("Summary for %s:" % (formatDate(start)))

        else:
            print("Summary for %s - %s:" %
                  (formatDate(start), formatDate(end)))
            if len(recentHolidays) > 0:
                print("%s holiday/s in this period:" % (len(recentHolidays)))
                for d, name in recentHolidays.items():
                    weekday = d.strftime("%a")
                    print("%s: %s - %s" % (weekday, formatDate(d), name))

        print("Worked for: %s" % (formatDuration(duration)))
        print("To be done: %s" % (formatDuration(tbd-duration)))

    def export(self, args):
        args = vars(self.argparser.parse_args())
        timeClock = TimeClock.buildFromConfig()

        if not timeClock.isStarted():
            month = datetime.strptime(
                args['month'], "%B %Y") if args['month'] else datetime.now()
            timeClock.exportMonth(month)
        else:
            print("""Please finish the current work
            session before trying to export.""")
        pass

    def ls(self, args):
        args = vars(self.argparser.parse_args())

        # handle date
        date = datetime.now().date()
        mode = None
        if args['date']:
            date, mode = parseDate(args['date'])

        # handle keywords
        keywords = []
        if args['keywords']:
            keywords = re.split(' ', args['keywords'])

        res = self.timeClock.ls(mode, date, keywords)
        print(res)
        return res

    def commit(self, args):
        pass

    def push(self, args):
        pass


def init(args=None):
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
    countryCodes = list(
        filter(lambda x: pycountry.countries.get(alpha_2=x), locales))
    # get the country names
    countryNames = list(
        sorted(map(lambda x: pycountry.countries.get(alpha_2=x).name,
                   countryCodes)))

    questions = [
        inquirer.Path('data_dir',
                      message="In which directory should the data be stored?",
                      default=os.path.join(os.path.expanduser(
                          '~'), "Documents", "TimeClock") + os.path.sep
                      ),
        inquirer.Path('file_name',
                      message="What shoud the file be named?",
                      default="TimeClock.json"
                      ),
        inquirer.List('hours_per_day',
                      message="How many hours to you work per day?",
                      choices=range(1, 9, 1),
                      default=8
                      ),
        inquirer.List('days_off_per_month',
                      message="How many days do you have off per month?",
                      choices=list(map(lambda x: x/2, range(0, 7, 1))),
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
    countryCode = country.alpha_2
    # save the code instead of the name
    config['locale'] = countryCode

    # get the subdivs from the  holidays module
    subdivCodes = locales[country.alpha_2]

    # filter the ones that are not in holiday subdivs
    if subdivCodes:
        # get the name of subdiv type. E.g. "Kanton", "State", etc.
        subdivType = list(pycountry.subdivisions.get(
            country_code=countryCode))[0].type

        # filter the ones that dont have a name...
        # TODO: some subdivs have a three letter code...
        # figure out what's up with that
        subdivCodes = list(filter(lambda x: pycountry.subdivisions.get(
            code="%s-%s" % (countryCode, x)), subdivCodes))

        def f(code):
            name = pycountry.subdivisions.get(
                code="%s-%s" % (countryCode, code)).name
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


def initParser(cli: CLI):
    # for date, name in sorted(holidays.US(subdiv='CA', years=2014).items()):
    argparser = argparse.ArgumentParser(
        prog='timeClock',
        description='A time clock for keeping track of working hours.',
        epilog='Calling without arguments will start the tracking process.'
    )

    argparser.set_defaults(func=cli.track)

    subparsers = argparser.add_subparsers(
        help='refer to timeClock summary -h for further help')

    # create the parser for the "summary" command
    summaryParser = subparsers.add_parser("summary")
    summaryParser.add_argument(
        '-w',
        '--week',
        action="store_true",
        help="""Provides a summary over the current week.
        Also works with -d flag for querying another week"""
    )
    summaryParser.add_argument(
        '-m',
        '--month',
        action="store_true",
        help="""Provides a summary over the current month.
        Also works with -d flag for querying another month"""
    )
    summaryParser.add_argument(
        '-d',
        '--date',
        help="""Provides a summary for a particular date.
        DATE has to be in d.MMMM.yyyy format. e.g. "11 November 2023".
        Defaults to the current day."""
    )
    summaryParser.add_argument(
        '-k',
        '--keywords',
        help='Adds a filter for the specified keywords'
    )
    summaryParser.set_defaults(func=cli.summary)

    # export
    exportParser = subparsers.add_parser("export")
    exportParser.add_argument(
        '-m',
        '--month',
        help="""Exports a specific month to CSV.
        The month has to be in "%B %Y" format.
        E.g. 'December 2022'""")

    # edit
    editParser = subparsers.add_parser("edit")
    editParser.add_argument(
        '-e',
        '--editor',
        help="""Edit the JSON file storing the timeslots
        using the specefied editor"""
    )
    editParser.set_defaults(func=cli.edit)

    # init
    initParser = subparsers.add_parser(
        "init",
        description="Initialize the TimeClock config."
    )
    initParser.set_defaults(func=init)

    # ls
    lsParser = subparsers.add_parser("ls")
    lsParser.add_argument(
        '-d',
        '--date',
        help='Browse the data in a directory structured manner'
    )
    lsParser.add_argument(
        '-k',
        '--keywords',
        help='Adds a filter for the specified keywords'
    )
    lsParser.set_defaults(func=cli.ls)

    # commit
    commitParser = subparsers.add_parser(
        "commit",
        description="Commit the current data to the data directory."
    )
    commitParser.set_defaults(func=cli.commit)

    # push
    pushParser = subparsers.add_parser("push")
    pushParser.set_defaults(func=cli.push)

    return argparser


if __name__ == '__main__':
    cli = CLI.buildFromConfig()

    if not cli:
        yesNo = {
            'Yes': True,
            'No': False
        }

        print("The CLI is not initialized yet.")
        questions = [
            inquirer.List('init',
                          message="Do you wish to initialize?",
                          choices=yesNo)
        ]
        answer = inquirer.prompt(questions)
        if yesNo[answer['init']]:
            init()
        else:
            print("No or invalid config. Aborting")
    else:
        argparser = initParser(cli)
        cli.setArgparser(argparser)

        # read the handler and execute
        args = argparser.parse_args()
        args.func(args)
