from timeclock.query import Query, QueryType, Attribute
from timeclock.models import Slot
from timeclock.storage import Storage

class TestQuery:
    def test_slot_query(self):
        file_path = "/home/kai/Documents/timeclock.sqlite"
        storage = Storage(file_path=file_path)
        storage.direct_query("SELECT * FROM Vacation")
        objects = Slot.objects.all()
        for obj in objects:
            print(obj)
        assert True
