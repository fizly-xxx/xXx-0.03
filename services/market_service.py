from typing import Optional, Tuple, List, Any
import asyncio
import traceback

from interfaces.imarket import IMarketService
from services.pricing_service import PricingService
from Astandy import StandClient
from Astandy.generated.services import (
    GetTradeRequest, CreateSaleRequest,
    CancelRequestRequest, CreatePurchaseRequestRequest, GetPlayerOpenRequestsRequest, GetTradeOpenSaleRequestsRequest
)


def _safe_float(v, default: float = 0.0) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return default


class MarketService(IMarketService):
    def __init__(self, client: StandClient, pricing_service: PricingService = None):
        self.client = client
        self.pricing = pricing_service or PricingService()

    def set_pricing_config(self, config: dict):
        self.pricing.set_config(config)

    async def get_prices(self, item_def_id: int) -> Tuple[float, float]:
        """Отримує ціни лота та запиту одним махом (Оптимізовано)"""
        try:
            req = GetTradeRequest()
            req.id = int(item_def_id)
            
            # Ставимо таймаут 3 секунди, щоб не зависало
            raw = await asyncio.wait_for(
                self.client.send_request(*self.client.raw.MarketplaceRemoteService.getTrade2Request(req)),
                timeout=3.0
            )
            res = self.client.raw.MarketplaceRemoteService.getTrade2Response(raw)
            
            if hasattr(res, 'trade') and res.trade:
                lot = getattr(res.trade, 'salesPrice', 0.0)
                # Шукаємо запит покупця (topRequestPrice або purchasesPrice)
                bid = getattr(res.trade, 'topRequestPrice', getattr(res.trade, 'purchasesPrice', 0.0)) 
                
                # Якщо сервер віддав 0, ставимо 0.01 для безпеки бота
                lot_price = float(lot) if lot > 0 else 0.01
                request_price = float(bid) if bid > 0 else 0.01
                
                return lot_price, request_price
            
            return 0.01, 0.01
        except Exception as e:
            print(f"Помилка парсингу цін: {e}")
            return 0.01, 0.01

    async def get_active_lots(self) -> List[Any]:
        request = GetPlayerOpenRequestsRequest()
        raw = await self.client.send_request(*self.client.raw.MarketplaceRemoteService.getPlayerOpenRequests2Request(request))
        res = self.client.raw.MarketplaceRemoteService.getPlayerOpenRequests2Response(raw)
        return getattr(res, 'openRequests', [])

    async def sell_item(self, unique_item_uid: int, price: Optional[float] = None, use_pricing_service: bool = True) -> bool:
        if price is None and use_pricing_service:
            try:
                lot_price, request_price = await self.get_prices(unique_item_uid)
                price = self.pricing.calculate_price(lot_price, request_price)
            except Exception:
                price = self.pricing.calculate_price(None, None)
        elif price is None:
            price = 0.01

        request = CreateSaleRequest()
        request.itemId = int(unique_item_uid)
        request.price = float(price)
        try:
            raw = await self.client.send_request(*self.client.raw.MarketplaceRemoteService.createSaleRequest(request))
            _ = self.client.raw.MarketplaceRemoteService.createSaleResponse(raw)
            return True
        except Exception as e:
            print(f"❌ Помилка виставлення на продаж: {e}")
            traceback.print_exc()
            raise

    async def cancel_order(self, market_request_id):
        request = CancelRequestRequest()
        request.requestId = str(market_request_id)
        raw = await self.client.send_request(*self.client.raw.MarketplaceRemoteService.cancelRequest2Request(request))
        _ = self.client.raw.MarketplaceRemoteService.cancelRequest2Response(raw)
        return True

    async def buy_item(self, item_def_id: int, price: Optional[float] = None, use_pricing_service: bool = True):
        if price is None and use_pricing_service:
            price = self.pricing.calculate_price()
        elif price is None:
            price = 0.01
        request = CreatePurchaseRequestRequest()
        request.itemDefinitionId = item_def_id
        request.price = float(price)
        request.quantity = 1
        raw = await self.client.send_request(*self.client.raw.MarketplaceRemoteService.createPurchaseRequest2Request(request))
        res = self.client.raw.MarketplaceRemoteService.createPurchaseRequest2Response(raw)
        return getattr(res, 'purchaseRequestId', getattr(getattr(res, 'request', None), 'id', None))

    async def get_smart_sell_price(self, item_def_id: int) -> dict:
        """Отримує лоти з ринку і повертає смарт-ціну"""
        try:
            lots_req = GetTradeOpenSaleRequestsRequest()
            lots_req.id = int(item_def_id)
            raw = await self.client.send_request(
                *self.client.raw.MarketplaceRemoteService.getTradeOpenSaleRequests2Request(lots_req)
            )
            res = self.client.raw.MarketplaceRemoteService.getTradeOpenSaleRequests2Response(raw)
            
            lots = getattr(res, 'requests', getattr(res, 'openRequests', getattr(res, 'sales', [])))
            prices = sorted([float(lot.price) for lot in lots if hasattr(lot, 'price')])

            if not prices:
                return {"success": False, "error": "Ринок порожній"}

            # Викликаємо логіку з нашого PricingService
            smart_price = self.pricing.calculate_smart_sell_price(prices)
            return {"success": True, "price": smart_price, "lowest": prices[0]}
            
        except Exception as e:
            return {"success": False, "error": str(e)}