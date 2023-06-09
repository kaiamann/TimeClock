"""A module containing various helper methods"""
import sys
from datetime import (
    timedelta as Timedelta,
    datetime as Datetime,
    date as Date,
)

def read_lines() -> str:
    """Read user input from stdin.

    Returns:
        str: The user iput.
    """
    lines = []
    for line in sys.stdin:
        lines.append(line.strip())

    return "\n".join(lines)


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
        date (Date): The date to be formatte.

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
    return datetime.strftime("%d %B %Y %H:%M")


def datetime_from_string(string: str) -> Datetime:
    """Parse a string into a datetime object.

    Args:
        string (str): The string to be parsed.

    Returns:
        Datetime: The datetime object.
    """
    return Datetime.strptime(string, "%d %B %Y %H:%M")


def get_week(date: Date) -> tuple[Date, Date]:
    """Get the start and end of the week for a particular date.

    Args:
        date (Date): The reference date.

    Returns:
        (Date, Date): A tuple of dates containing (start,end) dates of the week.
    """
    start = date - Timedelta(days=date.weekday())
    end = start + Timedelta(days=6)
    return start, end


def get_month(date: Date) -> tuple[Date, Date]:
    """Get the start and end of the month for a particular date.

    Args:
        date (Date): The reference date.

    Returns:
        (Date, Date): A tuple of dates containing (start,end) dates of the month.
    """
    start = date - Timedelta(days=date.day-1)
    # make sure we're in the next month
    next_month = date.replace(day=28) + Timedelta(days=4)
    end = next_month - Timedelta(days=next_month.day)
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


def has_keywords(slot: dict, keywords: list|None) -> bool:
    """Check if the description of a slot contains the requested keywords.

    Args:
        slot (dict): The slot.
        keywords (list): The keywords

    Returns:
        bool: True if description contains the keywords, false otherwise.
    """
    if not keywords:
        return True
    # Filter for relevant keywords
    relevant = True
    for keyword in keywords:
        if 'description' not in slot or keyword not in slot['description']:
            relevant = False
            break
    return relevant
