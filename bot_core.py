import asyncio
from Astandy import StandClient
from services.inventory_service import InventoryService
from services.market_service import MarketService
from services.pricing_service import PricingService
from services.trading_engine import TradingEngine

class GameBot:
    # ТЕПЕР МИ ПЕРЕДАЄМО ВСІ ЗАЛЕЖНОСТІ ЧЕРЕЗ АРГУМЕНТИ
    def __init__(self, handshake: str, client: StandClient, pricing: PricingService, 
                 inventory: InventoryService, market: MarketService, 
                 trading_engine: TradingEngine, config: dict = None):
        self.handshake = handshake
        self.client = client
        self.pricing = pricing
        self.inventory = inventory
        self.market = market
        self.trading_engine = trading_engine
        
        self.config = config or {}
        self.is_running = False

    async def start(self):
        """Запуск клієнта"""
        await self.client.start()

    async def stop(self):
        """Зупинка клієнта"""
        if self.is_running:
            await self.trading_engine.stop()
            self.is_running = False
        await self.client.stop()
    
    async def start_trading(self, on_log=None, on_price_update=None):
        """Запускає торговельний engine"""
        self.is_running = True
        await self.trading_engine.start(self.handshake, on_log, on_price_update)