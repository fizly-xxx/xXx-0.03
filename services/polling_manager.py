import asyncio
import traceback
from services.telegram_service import TelegramService

class PollingManager:
    def __init__(self, api):
        # Передаємо посилання на головний Api, щоб мати доступ до UI та конфігів
        self.api = api 
        self.running = False
        self.shared_bot = None
        self.last_balance = None
        self.last_items_ids = set()

    def start(self):
        """Запускає поллінг"""
        if self.running: return True
        self.running = True
        asyncio.run_coroutine_threadsafe(self._loop(), self.api.orchestrator.loop)
        self.api._log_to_ui('INFO', '🔁 Запущено авто-оновлення цін (1s) і балансу (30s)')
        return True

    def stop(self):
        """Зупиняє поллінг"""
        self.running = False
        self.api._log_to_ui('INFO', '⏹ Оновлення цін зупинено')
        return False

    async def _loop(self):
        """Головний цикл Оркестратора поллінгу"""
        if not await self._connect(): 
            return
            
        seconds_counter = 0
        failure_count = 0
        
        while self.running:
            try:
                cfg = self.api.load_config()
                base_sleep = float(cfg.get('uiDelay', 0.200))
                
                # 1. Швидкий тік: ціни та трейдинг
                await self._tick_trading(cfg)
                
                # 2. Повільний тік: інвентар та Телеграм
                seconds_counter += 1
                if seconds_counter >= 100:  
                    seconds_counter = 0
                    await self._tick_inventory(cfg)

                failure_count = 0
                await asyncio.sleep(base_sleep)

            except Exception as e:
                failure_count += 1
                self.api._log_to_ui('ERR', f'Помилка мережі: {e}')
                if failure_count >= 6:
                    self.api._log_to_ui('ERR', f'Зупинено після {failure_count} помилок.')
                    break
                await asyncio.sleep(min(30.0, base_sleep * (2 ** (failure_count - 1))))

        # При виході з циклу - відключаємось
        if self.shared_bot:
            await self.shared_bot.stop()
            self.shared_bot = None
            
            # ---> ДОДАЙ ЦЕЙ РЯДОК: очищаємо посилання в головному Api <---
            self.api.shared_bot = None 
            
        self.running = False

    # ---------------------------------------------------------
    # ВНУТРІШНІ МЕТОДИ (Розділена логіка)
    # ---------------------------------------------------------
    async def _connect(self) -> bool:
        """Очікує робочий токен та вибраний скін для підключення бота"""
        while self.running:
            config = self.api.load_config()
            handshake = config.get('handshake')
            skin = config.get('skin')
            
            # Чекаємо, поки будуть обидва параметри
            if handshake and skin and str(skin) != '—':
                self.shared_bot = self.api._create_bot_instance(handshake, config)
                self.api.shared_bot = self.shared_bot 
                
                try:
                    await self.shared_bot.start()
                    # Тестовий запит для перевірки валідності хендшейку
                    items, gold = await self.shared_bot.inventory.get_inventory_and_balance()
                    
                    self.last_balance = float(gold)
                    self.last_items_ids = {item.id for item in items}
                    self._update_balance_ui(gold)
                    self.api._log_to_ui('OK', f'💰 Баланс: {gold:.2f} G. Пулінг цін активовано!')
                    return True
                except Exception as e:
                    # Якщо хендшейк неробочий — очищаємо бота і чекаємо
                    self.api._log_to_ui('ERR', f'❌ Помилка реєстрації/підключення: {e}')
                    if self.shared_bot:
                        await self.shared_bot.stop()
                    self.shared_bot = None
                    self.api.shared_bot = None
                    
                    # Затримка перед наступною спробою, щоб не спамити
                    await asyncio.sleep(5)
            else:
                # Якщо даних ще немає, просто спимо у фоні
                await asyncio.sleep(2)
                
        return False

    async def _tick_trading(self, cfg: dict):
        """Перевіряє ціни на ринку і керує снайпером"""
        try:
            item_def_id = int(cfg.get('skin') or 0)
            if item_def_id == 0: 
                return # Виходимо, якщо ID скіна нульовий
        except Exception: return

        current_tab = getattr(self.api, 'active_tab', 'home')
        is_idle_mode = (current_tab != 'home' and not self.api.bot_running)

        if not is_idle_mode and self.shared_bot:
            if self.api.bot_running:
                self.shared_bot.pricing.set_config(cfg)
                if self.shared_bot.trading_engine:
                    self.shared_bot.trading_engine.config = cfg 
                if not self.shared_bot.trading_engine.is_armed:
                    self.shared_bot.trading_engine.arm(cfg, on_log=self.api._log_to_ui)
            elif not self.api.bot_running and self.shared_bot.trading_engine.is_armed:
                await self.shared_bot.trading_engine.disarm()

            lot_price, request_price = await self.shared_bot.market.get_prices(item_def_id)
            calculated = self.shared_bot.pricing.calculate_price(lot_price, request_price)
            
            self.api._update_ui_prices(
                lot_price=lot_price, request_price=request_price,
                calculated_price=calculated, mode=self.shared_bot.pricing.get_mode(),
                price_valid=(calculated < lot_price)
            )

            if self.shared_bot.trading_engine.is_armed:
                self.shared_bot.trading_engine.process_prices(lot_price, request_price)

    async def _tick_inventory(self, cfg: dict):
        """Перевіряє зміну балансу та відправляє звіти в ТГ"""
        if not self.shared_bot: return
            
        try:
            items, gold = await self.shared_bot.inventory.get_inventory_and_balance()
            current_gold = float(gold)
            current_items_ids = {item.id for item in items}
            tg_cfg = cfg.get('telegram', {})
            
            if tg_cfg.get('enabled') and self.last_balance is not None:
                # Купівля
                if current_gold < self.last_balance and tg_cfg.get('notifyBuy'):
                    for item_id in (current_items_ids - self.last_items_ids):
                        item = next((i for i in items if i.id == item_id), None)
                        if item:
                            name = self.api.skins_service.get_name(item.itemDefinitionId)
                            diff = round(self.last_balance - current_gold, 2)
                            stk = self._count_stickers(item)
                            await TelegramService.send_message(cfg, f"📥 Куплено скін!\n🔫 {name}\n🔥 Наклейок: {stk}\n💰 Ціна: {diff} G\n💵 Баланс: {current_gold:.2f} G")

                # Продаж
                elif current_gold > self.last_balance and tg_cfg.get('notifySell'):
                    diff = round(current_gold - self.last_balance, 2)
                    await TelegramService.send_message(cfg, f"💰 Скін продано!\n📈 Отримано: +{diff} G\n💵 Баланс: {current_gold:.2f} G")

            self.last_balance = current_gold
            self.last_items_ids = current_items_ids

            if current_gold < self.api.low_ballance and self.api.bot_running:
                self.api.toggle_bot_engine(False)
                self.api._log_to_ui('ERR', f'⚠️ КРИТИЧНИЙ БАЛАНС: {current_gold:.2f} G. Зупинка!')
            
            self._update_balance_ui(current_gold)
        except Exception: pass

    def _count_stickers(self, item) -> int:
        mods = getattr(item, 'modifications', [])
        return sum(1 for mod in mods if (isinstance(mod, str) and "sticker_" in mod) or (hasattr(mod, 'key') and "sticker_" in mod.key))

    def _update_balance_ui(self, gold: float):
        if self.api._window:
            self.api._window.evaluate_js(f"var el = document.getElementById('balance-display'); if(el) el.textContent = '{float(gold):.2f} G';")