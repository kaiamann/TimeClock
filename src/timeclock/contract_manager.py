from .models import UserSettings, Contract, User
from .timeclock import TimeClock
from .storage import Storage, Manager


class ContractManager:
    config: UserSettings
    storage: Storage
    timeclock: TimeClock

    def __init__(self, config: UserSettings, storage: Storage) -> None:
        self.config = config
        self.storage = storage
        self.timeclock = TimeClock()

    def activate_contract(self, contract: Contract):
        self.contracts.remove(contract)
        timeclock = TimeClock(
            slots=[],
            vacations=[],
            contract=contract,
            holidays={}
        )
        self.storage.create(contract)

    def get_slots_for_contract(contract: Contract):
        pass


    # def add_contract(self, contract) -> None:
    #     self.contracts.append(contract)


    def add_contract(self, start: Datetime, end: Datetime, description: str, hours_per_week: float, days_off_per_month: float, working_days: list[int]):
        """Add a new contract to the contracts.

        Args:
            date (start): The start of the contract
            date (end): The end of the contract
            description (str): The description for the contract
            hours_per_week (float): The amount of hours to work per week
            days_off_per_month (float): The amount of vacation days per week
            working_days (list[int]): The working days of the week
        """
        contract = Contract(start, end, description, hours_per_week, days_off_per_month, working_days)
        self.storage.add_slot(contract)
        self.storage.save()

