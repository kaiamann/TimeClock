import sqlite3
from datetime import datetime, timedelta, timezone
from timeclock.storage import Slot


def adapt_datetime_iso(val: datetime):
    print("adapt")
    return val.astimezone(timezone.utc).isoformat()

def convert_datetime(val):
    return datetime.fromisoformat(val.decode()).astimezone()

sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter(datetime.__name__, convert_datetime)

connection = sqlite3.connect("app.sqlite", detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

connection.execute('''
    CREATE TABLE Contract (
        ContractID INTEGER PRIMARY KEY,
        EmployeeID INTEGER,
        EmployerID INTEGER,
        StartDate DATE,
        EndDate DATE,
        -- Other contract-related fields
        UNIQUE (EmployeeID, EmployerID, StartDate, EndDate),
        FOREIGN KEY (EmployeeID) REFERENCES Employee(EmployeeID),
        FOREIGN KEY (EmployerID) REFERENCES Employer(EmployerID)
    )
''')

connection.execute('PRAGMA foreign_keys = ON;')
cursor = connection.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS slot(start datetime PRIMARY KEY, end datetime, description)")


def insert_slot(slot: Slot):
    cursor.execute("INSERT INTO slot VALUES(?, ?, ?)", slot.as_dict())
    connection.commit()

# now = cursor.execute("SELECT end FROM slot ORDER BY start DESC").fetchone()[0] or datetime.now()
# then = now + timedelta(hours=1)

# data = [(now, then, "some Description")]
# cursor.executemany("INSERT INTO slot VALUES(?, ?, ?)", data)
# connection.commit()

# ALTERNATIVE INSERTION METHOD
# This is the named style used with executemany():
# data = (
#     {"name": "C", "year": 1972},
#     {"name": "Fortran", "year": 1957},
#     {"name": "Python", "year": 1991},
#     {"name": "Go", "year": 2009},
# )
# cur.executemany("INSERT INTO lang VALUES(:name, :year)", data)


def print_slots(slots):
    for slot in slots:
        print(" - ".join(map(lambda x: x.strftime("%d.%m.%Y, %H:%M:%S") if isinstance(x, datetime) else x, slot)))

all_slots = cursor.execute('SELECT start, end, description FROM slot ORDER BY start').fetchall()
print("All Slots:")
print_slots(all_slots)

first_one = all_slots[0][0]
start = first_one + timedelta(minutes=30)
end = start + timedelta(hours=2)

print("start:", start)
print("end:", end)

data = {
    "start": start,
    "end": end
}

if first_one:
    print("Trying query")
    results = cursor.execute('SELECT MAX(start, :start) AS "start [datetime]", MIN(end, :end) AS "end [datetime]" FROM slot WHERE start BETWEEN :start AND :end OR end BETWEEN :start AND :end ORDER BY start', data).fetchall()
    print(f"Found {len(results)} slots")
    print_slots(results)

connection.close()
