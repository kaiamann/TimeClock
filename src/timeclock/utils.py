"""A module containing various helper methods"""
import os
try:
    import readline
except ImportError:
    readline = None
from datetime import (
    timedelta as Timedelta,
    datetime as Datetime,
    date as Date,
)

histfile = os.path.expanduser(os.path.join(os.path.expanduser('~'), ".timeclock_history"))
HISTFILE_SIZE = 100

def read_line() -> str:
    """Read user input from stdin.

    Returns:
        str: The user input.
    """

    if readline and os.path.exists(histfile):
        readline.read_history_file(histfile)

    string = input()

    if readline:
        readline.set_history_length(HISTFILE_SIZE)
        readline.write_history_file(histfile)

    return string


# Date and duration formatting

def format_duration(duration: Timedelta) -> str:
    """Format a duration into a human readable string.

    Args:
        duration (Timedelta): The duration to be formatted.

    Returns:
        str: The formatted duration.
    """
    sec = duration.total_seconds()
    sign = ""
    if sec < 0:
        sign = "-"
        sec = -sec

    hours = divmod(sec, 3600)[0]
    minutes = divmod(sec, 60)[0] - hours * 60

    return f"{sign}{hours:.0f} Hours {minutes:.0f} Minutes"


def format_date(date: Date) -> str:
    """Format a date into a human readable string.

    Args:
        date (Date): The date to be formatted.

    Returns:
        str: The formatted date.
    """
    return date.strftime("%d %B %Y")


def format_datetime(datetime: Datetime, time: bool = False) -> str:
    """Format a datetime into a human readable string.

    Args:
        datetime (Datetime): The datetime to be formatted.
        time (bool, optional): If true also prints the time. Defaults to False.

    Returns:
        str: The formatted datetime.
    """
    if time:
        return datetime.strftime("%H:%M")
    return datetime.strftime("%d %B %Y %H:%M %Z")


def datetime_from_string(string: str) -> Datetime:
    """Parse a string into a datetime object.

    Args:
        string (str): The string to be parsed.

    Returns:
        Datetime: The datetime object.
    """
    try:
        return Datetime.strptime(string, "%d %B %Y %H:%M %Z").astimezone()
    except ValueError:
        return Datetime.strptime(string, "%d %B %Y %H:%M").astimezone()

def date_from_string(string: str) -> Datetime:
    """Parse a string into a date object.

    Args:
        string (str): The string to be parsed.

    Returns:
        Date: The date object.
    """
    return Datetime.strptime(string, "%d %B %Y").astimezone()

def get_time_max(datetime: Datetime) -> Datetime:
    """Get the end of a day.

    Args:
        datetime (Datetime): A day.

    Returns:
        Datetime: The end of the given day.
    """
    return datetime.replace(hour=23, minute=59, second=59, microsecond=999999)

def get_time_min(datetime: Datetime) -> Datetime:
    """Get the beginning of a day.

    Args:
        datetime (Datetime): A day.

    Returns:
        Datetime: The beginning of the day.
    """
    return datetime.replace(hour=0, minute=0, second=0, microsecond=0)

def get_week(datetime: Datetime) -> tuple[Datetime, Datetime]:
    """Get the start and end of the week for a particular date.

    Args:
        date (Date): The reference date.

    Returns:
        (Date, Date): A tuple of dates containing (start,end) dates of the week.
    """
    start = datetime - Timedelta(days=datetime.weekday())
    end = start + Timedelta(days=6)
    return get_time_min(start), get_time_max(end)

def get_month(datetime: Datetime) -> tuple[Datetime, Datetime]:
    """Get the start and end of the month for a particular date.

    Args:
        date (Date): The reference date.

    Returns:
        (Date, Date): A tuple of dates containing (start,end) dates of the month.
    """
    start = get_time_min(datetime - Timedelta(days=datetime.day-1)).astimezone()
    # make sure we're in the next month
    next_month = datetime.replace(day=28) + Timedelta(days=4)
    end = get_time_max(next_month - Timedelta(days=next_month.day)).astimezone()
    return start, end


def parse_date(string: str) -> tuple[Datetime, str]:
    """Parses a string into a datetime object.

    Also returns which type of format the string was in.

    Args:
        string (str): The string to be parsed.

    Raises:
        ValueError: When the string could not be parsed.

    Returns:
        (Datetime, str): The parsed datetime, along with the type.
    """
    if not isinstance(string, str):
        raise ValueError
    try:
        return Datetime.strptime(string, '%Y').date(), "year"
    except ValueError:
        pass
    try:
        return Datetime.strptime(string, '%B %Y').date(), "month"
    except ValueError:
        pass
    try:
        return Datetime.strptime(string, '%d %B %Y').date(), "day"
    except ValueError:
        pass
    try:
        return Datetime.strptime(string, '%d %B %Y %H:%M').date(), "slot"
    except ValueError:
        pass

    raise ValueError
