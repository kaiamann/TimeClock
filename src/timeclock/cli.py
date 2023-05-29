"""A module that provides a CLI for tracking working hours"""

import argparse
import os
import re
from datetime import date as Date
from datetime import datetime as Datetime

import argcomplete
import holidays
import inquirer
import pycountry
import yaml
from pyfiglet import Figlet
from git import InvalidGitRepositoryError, GitError

from .storage import JSONStorage
from .timeclock import TimeClock
from .versioncontrol import VersionControl
from .utils import (format_date, format_datetime, format_duration, get_month, get_week,
                    parse_date, read_lines)

CONFIG_PATH = os.path.join(
    os.path.expanduser('~'),
    ".timeclock.yml"
)
EDITOR = os.environ.get('EDITOR', 'code')

class CLI:
    """A Command Line Interface that allows the user to track working hours.

    Also provides other functionalities, like exporting and summaries.
    """
    # TODO: pull params out of the dict into constructor signature
    def __init__(self, config: dict) -> None:

        # load config and crecreate objects
        data_dir = config['data_dir']
        filename = config['file_name']
        self.storage = JSONStorage(data_dir, filename)
        try:
            self.version_control = VersionControl(data_dir)
            self.version_control.fetch()
        except InvalidGitRepositoryError as error:
            self.version_control = None
            print(error)
            print("Git functionality disabled.")
        except GitError as error:
            print(error)

        self.argparser=initialize_parser(self)

        hours_per_day = config['hours_per_day']
        days_off_per_month = config['days_off_per_month']
        locale = config['locale']
        subdiv = None
        if 'locale_subdiv' in config:
            subdiv = config['locale_subdiv']

        self.timeclock = TimeClock(
            self.storage,
            hours_per_day,
            days_off_per_month,
            locale,
            subdiv
        )

    # Command line handlers

    def edit(self, args: dict)-> None:
        """Edit the storage directly with the chosen editor.

        Args:
            editor (str): The editor.
        """
        args = vars(self.argparser.parse_args())
        editor = args['editor']
        self.storage.edit(editor)


    def track(self, args: dict) -> None:
        """Routine to start or stop the time tracking.

        Args:
            args (dict): The arguments from the argparser.
        """
        del args
        if self.version_control and self.version_control.is_behind():
            try:
                self.version_control.pull()
            except:
                pass

        now = Datetime.now()
        if now.date() in self.timeclock.holidays:
            now = self.timeclock.next_workday(now)
            print("Today is a free day moving to " + format_date(now.date()))

        if self.timeclock.is_started():
            print("Enter description. Finish by pressing Ctrl+d")
            description = read_lines()
            start = self.timeclock.finish(now, description)

            formatted_date = format_date(now)
            time = now.strftime("%H:%M")
            print(f"{formatted_date}: Ending at {time}. Worked for: {format_duration(now-start)}")
        else:
            self.timeclock.start(now)

            formatted_date = format_date(now.date())
            time = format_datetime(now, True)
            print(f"{formatted_date}: Starting at {time}.")

        try:
            self.storage.save()
        except FileNotFoundError as error:
            print(error)
            return False


    # TODO: move this back into TimeClock and return an array containing the results
    def summary(self, args: dict) -> None:
        """Routine to print a summary for the chosen period.

        Args:
            args (dict): The arguments from the argparser
        """
        args = vars(self.argparser.parse_args())

        # handle date
        input_date = Date.today()
        if args['date']:
            input_date = Datetime.strptime(args['date'], '%d %B %Y').date()

        # default to day mode
        start = input_date
        end = input_date

        # set start end end for multi day modes
        if args['week']:
            start, end = get_week(input_date)
        if args['month']:
            start, end = get_month(input_date)

        # handle keywords
        keywords = []
        if args['keywords']:
            keywords = re.split(' ', args['keywords'])

        duration = self.timeclock.summary(start, end, keywords)
        tbd = self.timeclock.to_be_done(start, end)
        recent_holidays = self.timeclock.holidays_between(start, end)

        if duration > tbd:
            pass

        if start == end:
            print(f"Summary for {format_date(start)}:")

        else:
            print(f"Summary for {format_date(start)} - {format_date(end)}:")
            if len(recent_holidays) > 0:
                print(f"{len(recent_holidays)} holiday/s in this period:")
                for date, name in recent_holidays.items():
                    weekday = date.strftime("%a")
                    print(f"{weekday}: {format_date(date)} - {name}")

        print(f"Worked for: {format_duration(duration)}")
        print(f"To be done: {format_duration(tbd-duration)}")

    def export(self, args: dict) -> None:
        """Routine to export the data as csv.

        Args:
            args (dict): The arguments from the argparser
        """
        args = vars(self.argparser.parse_args())

        if self.timeclock.is_started():
            print("""Please finish the current work\
            session before trying to export.""")
            return

        # handle date
        input_date = Date.today()
        if args['date']:
            input_date = Datetime.strptime(args['date'], '%d %B %Y').date()

        # default to day mode
        start = input_date
        end = input_date
        filename = format_date(input_date)

        # set start end end for multi day modes
        if args['week']:
            start, end = get_week(input_date)
            filename = f"Week {start.isocalendar().week} {start.year}"
        if args['month']:
            start, end = get_month(input_date)
            filename = f"{Datetime.strftime(start,'%B %Y')}"

        # handle keywords
        keywords = []
        if args['keywords']:
            keywords = re.split(' ', args['keywords'])

        self.timeclock.export(filename, start, end, keywords)

    def ls(self, args: dict) -> None:
        """Routine to navigate the data in a directory-like structure

        Args:
            args (dict): The arguments from the argparser.

        Returns:
            _type_: _description_
        """

        args = vars(self.argparser.parse_args())

        # handle date
        date = Datetime.now().date()
        mode = None
        if args['date']:
            date, mode = parse_date(args['date'])

        # handle keywords
        keywords = []
        if args['keywords']:
            keywords = re.split(' ', args['keywords'])

        res = self.timeclock.list_dir(mode, date, keywords)
        print(res)
        return res

    def commit(self, args: dict) -> None:
        """Commit the changes.

        Args:
            args (dict): Args from the argparser
        """
        del args
        if self.version_control.is_behind():
            print("The repository seems to be behind the origin. Try pulling first")
        self.version_control.commit()

    def push(self, args: dict) -> None:
        """Push the changes.

        Args:
            args (dict): Args from the argparser
        """
        del args
        self.version_control.push()

    def pull(self, args: dict) -> None:
        """Pull from the remote."""
        del args
        self.version_control.pull()

def configure(args: dict=None) -> None:
    """Configures the TimeClock

    Asks the user for important configuration parameters:

    data_dir: The directory where the JSON file is stored
    file_name: The name of the JSON file
    work_hours_per_day: duh
    days_off_per_month: duh
    locale: The current locale of the user to fetch local holidays

    Args:
        args (dirct): The arguments from the argparser.
    """
    # print header if config is called for the first time
    if not args:
        print(Figlet(font="big").renderText("TimeClock"))

    locales = holidays.list_supported_countries()
    # filter out all the country codes that don't exist in pycountry
    country_codes = list(
        filter(lambda x: pycountry.countries.get(alpha_2=x), locales))
    # get the country names
    country_names = list(
        sorted(map(lambda x: pycountry.countries.get(alpha_2=x).name,
                   country_codes)))

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
                      choices=country_names,
                      ),
    ]
    config = inquirer.prompt(questions)

    # do nothing if no config
    if not config:
        return

    # get the country code from the human readable nam/
    country = pycountry.countries.get(name=config['locale'])
    country_code = country.alpha_2
    # save the code instead of the name
    config['locale'] = country_code

    # get the subdivs from the  holidays module
    subdiv_codes = locales[country.alpha_2]

    # filter the ones that are not in holiday subdivs
    if subdiv_codes:
        # get the name of subdiv type. E.g. "Kanton", "State", etc.
        subdiv_type = list(pycountry.subdivisions.get(
            country_code=country_code))[0].type

        # filter the ones that dont have a name...
        # TODO: some subdivs have a three letter code...
        # figure out what's up with that
        subdiv_codes = list(filter(lambda x: pycountry.subdivisions.get(
            code=f"{country_code}-{x}"), subdiv_codes))

        def get_name_for_code(code):
            name = pycountry.subdivisions.get(
                code=f"{country_code}-{code}").name
            return (name, code)

        subdiv_map = dict(map(get_name_for_code, subdiv_codes))
        subdiv_names = list(sorted(subdiv_map.keys()))

        questions = [
            inquirer.List('subdiv',
                          message=f"In which {subdiv_type} do you live?",
                          choices=subdiv_names,
                          )
        ]
        subdiv_config = inquirer.prompt(questions)

        if not subdiv_config:
            return

        config['locale_subdiv'] = subdiv_map[subdiv_config['subdiv']]

    # print(config)
    # dump to config.yml
    with open(CONFIG_PATH, "w+", encoding="utf-8") as file:
        yaml.dump(config, file)


def initialize_parser(cli: CLI):
    """Initialize the argument parser for a cli.

    Args:
        cli (CLI): The cli for which the parser should be initialized.
    
    Returns:
        argparser: The argparser.
    """
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
    summary_parser = subparsers.add_parser("summary")
    summary_parser.add_argument(
        '-w',
        '--week',
        action="store_true",
        help="""Provides a summary over the current week.
        Also works with -d flag for querying another week"""
    )
    summary_parser.add_argument(
        '-m',
        '--month',
        action="store_true",
        help="""Provides a summary over the current month.
        Also works with -d flag for querying another month"""
    )
    summary_parser.add_argument(
        '-d',
        '--date',
        help="""Provides a summary for a particular date.
        DATE has to be in d.MMMM.yyyy format. e.g. "11 November 2023".
        Defaults to the current day."""
    )
    summary_parser.add_argument(
        '-k',
        '--keywords',
        help='Adds a filter for the specified keywords'
    )
    summary_parser.set_defaults(func=cli.summary)

    # export
    export_parser = subparsers.add_parser("export")
    export_parser.add_argument(
        '-w',
        '--week',
        action="store_true",
        help="""Export the current week.
        Also works with -d flag for querying another week"""
    )
    export_parser.add_argument(
        '-m',
        '--month',
        action="store_true",
        help="""Export the current month.
        Also works with -d flag for querying another month"""
    )
    export_parser.add_argument(
        '-d',
        '--date',
        help="""Export a particular date.
        DATE has to be in d.MMMM.yyyy format. e.g. "11 November 2023".
        Defaults to the current day."""
    )
    export_parser.add_argument(
        '-k',
        '--keywords',
        help='Adds a filter for the specified keywords'
    )
    export_parser.set_defaults(func=cli.export)

    # edit
    edit_parser = subparsers.add_parser("edit")
    edit_parser.add_argument(
        '-e',
        '--editor',
        help="""Edit the JSON file storing the timeslots
        using the specified editor""",
        default=EDITOR
    )
    edit_parser.set_defaults(func=cli.edit)

    # init
    config_parser = subparsers.add_parser(
        "config",
        description="Configure the TimeClock."
    )
    config_parser.set_defaults(func=configure)

    # ls
    ls_parser = subparsers.add_parser("ls")
    ls_parser.add_argument(
        '-d',
        '--date',
        help='Browse the data in a directory structured manner'
    )
    ls_parser.add_argument(
        '-k',
        '--keywords',
        help='Adds a filter for the specified keywords'
    )
    ls_parser.set_defaults(func=cli.ls)

    # commit
    commit_parser = subparsers.add_parser(
        "commit",
        description="Commit the current data to the data directory."
    )
    commit_parser.set_defaults(func=cli.commit)

    # push
    push_parser = subparsers.add_parser("push")
    push_parser.set_defaults(func=cli.push)

    # pull
    pull_parser = subparsers.add_parser("pull")
    pull_parser.set_defaults(func=cli.pull)

    return argparser

def run():
    """Routine to run the CLI"""

    try:
        with open(CONFIG_PATH, mode='r', encoding="utf-8") as file:
            config = yaml.safe_load(file)

    except FileNotFoundError as err:
        print(err)
        print("The CLI is not configured yet.")
        if yes_no_question("Do you wish to configure it?"):
            configure()
            return
        print("No or invalid config. Aborting")
        return

    cli = CLI(config)

    argparser = cli.argparser

    argcomplete.autocomplete(argparser)

    # read the handler and execute
    args = argparser.parse_args()
    args.func(args)


def yes_no_question(question: str) -> bool:
    """Pose a yes/no question to the user.

    Args:
        question (str): The question to be asked.

    Returns:
        bool: True if the answer was yes, False otherwise.
    """
    choices = {
        'Yes': True,
        'No': False
    }
    questions = [
        inquirer.List('init',
                    message=question,
                    choices=choices)
    ]
    answer = inquirer.prompt(questions)
    return choices[answer['init']]

if __name__ == '__main__':
    run()
