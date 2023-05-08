from datetime import timedelta, datetime, date


def readStdin():
    import sys
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


def getWeek(inputDate: date):
    start = inputDate - timedelta(days=inputDate.weekday())
    end = start + timedelta(days=6)
    return start, end


def getMonth(inputDate: date):
    start = inputDate - timedelta(days=inputDate.day-1)
    nextMonth = inputDate.replace(day=28) + timedelta(days=4)
    end = nextMonth - timedelta(days=nextMonth.day)
    return start, end


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


def hasKeywords(slot, keywords):
    # Filter for relevant keywords
    relevant = True
    for keyword in keywords:
        if 'description' not in slot or keyword not in slot['description']:
            relevant = False
            break
    return relevant
