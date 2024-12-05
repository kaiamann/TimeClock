from datetime import datetime, timedelta
from timeclock.storage import Storage
from timeclock.models import User, Slot, UserSettings, Contract


file_path = " test.sqlite"

storage = Storage(file_path=file_path)

# Test User
def insert_user():
    user_settings = UserSettings(locale="de", locale_subdiv="by")
    user = User(name="Kai", email="wtf", settings=user_settings)
    user.save()
    return user

def rename_user(user: User):
    user.name = "Tomate"
    user.save()
    return user

def insert_contract(user: User):
    start = datetime.now()
    end = start + timedelta(days=365)
    contract = Contract(user, name="CDI", start=start, end=end)
    contract.save()
    return contract

def change_existing_user():
    user = User.objects.get_by_id(1)
    match user.email:
        case "wtf":
            user.email = "ftw"
        case "ftw":
            user.email = "wtf"
    user.save()

def get_contract(id: int) -> Contract:
    return Contract.objects.get_by_id(id)

def toggle_contract(contract: Contract):
    contract.active = not contract.active
    contract.save()
    return contract

# insert_user()
user = change_existing_user()
# contract = insert_contract(user)
contract = get_contract(4)

# toggle_contract(contract)
contract.activate()
contract.deactivate()

print(Contract.get_active_contract())