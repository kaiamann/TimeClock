from datetime import datetime, timedelta
from timeclock.storage import Storage
from timeclock.models import User, Slot, UserSettings, Contract


file_path = "/home/kai/Documents/timeclock.sqlite"

storage = Storage(file_path=file_path)

# Test User
user_settings = UserSettings(locale="de", locale_subdiv="by")
user = User(name="Kai", email="wtf", settings=user_settings)

# storage.insert(user)
# print(user.id)

# storage.connection.execute("""
# CREATE TABLE Contract2 (
#     ContractID INTEGER PRIMARY KEY AUTOINCREMENT,
#     EmployeeID INTEGER,
#     StartDate DATE,
#     EndDate DATE,
# );

# CREATE TRIGGER NoOverlappingContracts
# BEFORE INSERT ON Contract2
# FOR EACH ROW
# BEGIN
#     SELECT CASE
#         WHEN (
#             EXISTS (
#                 SELECT 1 FROM Contract2 c
#                 WHERE c.EmployeeID = NEW.EmployeeID
#                 AND (
#                     (NEW.StartDate BETWEEN c.StartDate AND c.EndDate)
#                     OR (NEW.EndDate BETWEEN c.StartDate AND c.EndDate)
#                     OR (c.StartDate BETWEEN NEW.StartDate AND NEW.EndDate)
#                     OR (c.EndDate BETWEEN NEW.StartDate AND NEW.EndDate)
#                 )
#             )
#         ) THEN
#             RAISE(FAIL, 'Overlapping contracts are not allowed');
#     END;
# END;
# """)
# storage.connection.commit()

# start = datetime.now()

# contract = Contract(
#     name="CDI",
#     user=user,
#     start=start,
#     end=start + timedelta(days=1)
#     )
# storage.insert(contract)
# storage.connection.commit()


# storage.close()


# Create test


# Create test slots
# start = datetime.now()
# for i in range(0, 10):
#     start += timedelta(hours=1)
#     end = start + timedelta(hours=1)
#     slot = Slot(start, end, f"Slot {i}")
#     storage.insert_slot(slot)








# lastSlot = cursor.execute("SELECT end FROM slot ORDER BY start DESC").fetchone()
# now = lastSlot[0] if lastSlot else datetime.now()
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












# def print_slots(slots):
#     for slot in slots:
#         print(" - ".join(map(lambda x: x.strftime("%d.%m.%Y, %H:%M:%S") if isinstance(x, datetime) else x, slot)))

# all_slots = cursor.execute('SELECT start, end, description FROM slot ORDER BY start').fetchall()
# print("All Slots:")
# print_slots(all_slots)

# first_one = all_slots[0][0]
# start = first_one + timedelta(minutes=30)
# end = start + timedelta(hours=2)

# print("start:", start)
# print("end:", end)

# data = {
#     "start": start,
#     "end": end
# }

# if first_one:
#     print("Trying query")
#     results = cursor.execute('SELECT MAX(start, :start) AS "start [datetime]", MIN(end, :end) AS "end [datetime]" FROM slot WHERE start BETWEEN :start AND :end OR end BETWEEN :start AND :end ORDER BY start', data).fetchall()
#     print(f"Found {len(results)} slots")
#     print_slots(results)

# connection.close()


test_array = [1,2,3,4,5,6]

test_dict = {
    "test1": "test5",
    "test2": "test6",
    "test3": "test7",
    "test4": "test8",
}
if "test1" in test_dict:
    print("yes")