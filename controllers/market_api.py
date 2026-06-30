class MarketApiMixin:
    def fetch_sales(self, handshake):
        async def _coro():
            lots = await self.shared_bot.market.get_active_lots()
            lots_data = [{"id": str(lot.id), "def_id": lot.itemDefinitionId,
                          "name": self.skins_service.get_name(lot.itemDefinitionId),
                          "price": f"{float(lot.price):.2f}"} for lot in lots]
            return {"success": True, "sales": lots_data}
        return self._run_safely_in_bot_loop(_coro())

    def cancel_sale(self, handshake, sale_id):
        async def _coro():
            self._log_to_ui('INFO', f'Скасування лоту {sale_id}...')
            result = await self.shared_bot.market.cancel_order(sale_id)
            self._log_to_ui('OK', f'Лот {sale_id} скасовано')
            return {"success": True, "result": result}
        return self._run_safely_in_bot_loop(_coro())

    def sell_item(self, handshake, item_uid, price=None):
        async def _coro():
            await self.shared_bot.market.sell_item(item_uid, price, use_pricing_service=False)
            self._log_to_ui('OK', f'Предмет виставлено за {price} G')
            return {"success": True}
        return self._run_safely_in_bot_loop(_coro())

    def get_smart_sell_price(self, handshake, item_def_id):
        async def _coro():
            return await self.shared_bot.market.get_smart_sell_price(item_def_id)
        return self._run_safely_in_bot_loop(_coro())

    def fetch_prices(self, handshake, item_def_id):
        async def _coro():
            lot_price, request_price = await self.shared_bot.market.get_prices(int(item_def_id))
            return {"success": True, "lot_price": float(lot_price), "request_price": float(request_price)}
        return self._run_safely_in_bot_loop(_coro())