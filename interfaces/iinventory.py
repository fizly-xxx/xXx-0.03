from abc import ABC, abstractmethod

class IInventoryService(ABC):
    @abstractmethod
    async def get_inventory_and_balance(self):
        pass