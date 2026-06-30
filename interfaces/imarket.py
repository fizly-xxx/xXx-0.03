from abc import ABC, abstractmethod

class IMarketService(ABC):
    @abstractmethod
    async def get_prices(self, item_def_id: int): pass
    @abstractmethod
    async def sell_item(self, unique_item_uid: int, price: float): pass
    @abstractmethod
    async def cancel_order(self, market_request_id): pass
    @abstractmethod
    async def buy_item(self, item_def_id: int, price: float): pass
    @abstractmethod
    async def get_active_lots(self): pass # <-- ДОДАЙ ЦЕ