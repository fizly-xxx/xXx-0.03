import asyncio
import logging
import time

class TradingEngine:
    def __init__(self, market_service, config: dict):
        self.market = market_service
        self.config = config
        self.logger = logging.getLogger('TradingEngine')
        
        self.last_request_price = None
        self.last_lot_price = None
        self.my_current_price = None  
        self.active_purchase_requests = []
        
        self.item_def_id = int(config.get('skin', 0))
        self.on_log = None
        
        self.is_armed = False
        self.purchase_task = None

        # --- ЗМІННІ ДЛЯ АНТИ-БАЙТУ ---
        self.same_price_count = 0
        self.last_seen_request = 0
        self.pause_until = 0
        
    def arm(self, config: dict, on_log):
        self.config = config
        self.item_def_id = int(config.get('skin', 0))
        self.on_log = on_log
        self.last_request_price = None
        self.last_lot_price = None
        self.my_current_price = None
        self.is_armed = True
        self._log('OK', f'🎯 Снайпер АКТИВОВАНО! Режим: {self.market.pricing.get_mode().upper()}')
        
    async def disarm(self):
        self.is_armed = False
        if self.purchase_task and not self.purchase_task.done():
            self.purchase_task.cancel()
            
        for req_id in list(self.active_purchase_requests):
            try:
                await self.market.cancel_order(req_id)
            except: pass
            
        self.active_purchase_requests.clear()
        self.my_current_price = None
        self._log('WARN', '🛑 Снайпер зупинений.')

    def process_prices(self, lot_price: float, request_price: float):
        if not self.is_armed:
            return

        # 1. Перевірка чи ми не на паузі
        if time.time() < getattr(self, 'pause_until', 0):
            return

        # ЗАХИСТ ВІД САМОПЕРЕБИВУ:
        if self.my_current_price is not None and abs(request_price - self.my_current_price) < 0.001:
            self.last_lot_price = lot_price
            self.last_request_price = request_price
            return
            
        calculated_price = round(self.market.pricing.calculate_price(lot_price, request_price), 2)
        price_is_valid = calculated_price < lot_price
        
        is_first_run = (self.last_request_price is None)
        
        # --- ФІКС: ПЕРШИЙ ЗАПУСК ---
        if is_first_run:
            self.last_lot_price = lot_price
            self.last_request_price = request_price
            self._log('INFO', f'📡 Моніторинг ринку розпочато. Топ: ${request_price:.2f}')
            return
            
        # --- ЛОГІКА ПЕРЕБИВАННЯ ---
        # Реагуємо, якщо конкурент підняв ціну
        if request_price > self.last_request_price:
            
            # --- ПРАВИЛЬНИЙ АНТИ-БАЙТ ---
            if request_price == getattr(self, 'last_seen_request', 0):
                self.same_price_count += 1
            else:
                self.same_price_count = 1
                self.last_seen_request = request_price

            if self.same_price_count >= 3:
                self._log('WARN', f'🔄 Виявлено байт на {request_price}! Сон 10 сек.')
                self.pause_until = time.time() + 10
                self.same_price_count = 0
                if self.purchase_task and not self.purchase_task.done():
                    self.purchase_task.cancel()
                self.last_request_price = request_price # Оновлюємо, щоб не спамило
                return
            # ----------------------------

            self._log('WARN', f'📈 Конкурент перебив! Ринок: ${request_price:.2f}')
            
            if self.purchase_task and not self.purchase_task.done():
                self.purchase_task.cancel()

            if price_is_valid:
                self.purchase_task = asyncio.create_task(
                    self._execute_purchase_cycle(calculated_price, immediate=False)
                )
            else:
                self._log('ERR', f'⚠️ Невигідно перебивати (${calculated_price:.2f} >= ${lot_price:.2f})')
        
        # Оновлюємо пам'ять
        self.last_lot_price = lot_price
        self.last_request_price = request_price

    async def _execute_purchase_cycle(self, target_price: float, immediate: bool = False):
        req_id = None
        try:
            # 1. Trade Delay
            if not immediate:
                delay_sec = self.market.pricing.get_delay() / 1000.0
                await asyncio.sleep(delay_sec)
            
            if not self.is_armed: return
            
            # 2. Виставлення ордера
            self._log('INFO', f'🛒 Ставимо ордер: ${target_price:.2f}...')
            req_id = await self.market.buy_item(self.item_def_id, target_price, use_pricing_service=False)
            
            if req_id:
                self.active_purchase_requests.append(req_id)
                self.my_current_price = target_price 
                self._log('OK', f'✅ ВИСТАВЛЕНО: ${target_price:.2f} (ID: {req_id})')
                
                # 3. Order Hold 
                hold_sec = float(self.config.get('orderHold', 3600)) / 1000.0
                await asyncio.sleep(hold_sec)
                
                # 4. Скасування по таймеру (БЕЗПЕЧНЕ)
                if req_id in self.active_purchase_requests:
                    await self._safe_cancel(req_id)
                    if self.my_current_price == target_price:
                        self.my_current_price = None
                    self._log('INFO', f'⏱️ Час вийшов. Ордер {req_id} знято.')
            
        except asyncio.CancelledError:
            if req_id and req_id in self.active_purchase_requests:
                # Використовуємо shield (через create_task), щоб скасування не перервалось під час перебиву
                asyncio.create_task(self._safe_cancel(req_id))
                self.my_current_price = None
                self._log('INFO', f'🗑️ Старий ордер {req_id} видалено для перебиву.')
        except Exception as e:
            self._log('ERR', f'❌ Помилка: {e}')
            self.my_current_price = None

    def _log(self, msg_type: str, message: str):
        if self.on_log: self.on_log(msg_type, message)

    async def _safe_cancel(self, req_id):
        """Гарантована відміна з 3 спробами"""
        for _ in range(3):
            try:
                await self.market.cancel_order(req_id)
                if req_id in self.active_purchase_requests:
                    self.active_purchase_requests.remove(req_id)
                return
            except Exception as e:
                self._log('ERR', f'Помилка відміни {req_id}, повторюю... ({e})')
                await asyncio.sleep(0.3)