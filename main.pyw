import json
import os
import threading
import sys
import traceback
import asyncio
from services.bot_orchestrator import BotOrchestrator
from services.telegram_service import TelegramService
from services.config_service import ConfigService
from services.skins_service import SkinsService
from bot_core import GameBot 
from typing import Optional, Tuple
from interfaces.imarket import IMarketService
from services.pricing_service import PricingService
from Astandy import StandClient
from Astandy.generated.services import (
    GetTradeRequest, CreateSaleRequest, 
    CancelRequestRequest, CreatePurchaseRequestRequest, GetPlayerOpenRequestsRequest, GetTradeOpenSaleRequestsRequest
)
from services.polling_manager import PollingManager  # <-- ДОДАТИ ІМПОРТ
from controllers.config_api import ConfigApiMixin
from controllers.market_api import MarketApiMixin
from controllers.inventory_api import InventoryApiMixin
from utils import get_ui_path, get_jsons_dir

class Api(ConfigApiMixin, MarketApiMixin, InventoryApiMixin):
    def __init__(self):
        self._window = None
        self.config_service = ConfigService()
        self.skins_service = SkinsService()
        self.bot_instance = None
        
        # --- НОВЕ: Запускаємо наш єдиний оркестратор ---
        self.orchestrator = BotOrchestrator()
        self.orchestrator.start()
        
        # Створюємо нашого менеджера!
        self.polling_manager = PollingManager(self)

        # Залишаємо тільки необхідні прапорці
        self.bot_running = False
        self.price_polling_running = False
        self.shared_bot = None
        self.active_tab = 'home'
        self.low_ballance = 0.01

        # --- ЗАХИСТ КОНФІГУ ВІД ПОЛОМКИ (МЕМОРІ КЕШ) ---
        self._config_lock = threading.Lock()
        try:
            self._cached_config = self.config_service.load() or {}
        except Exception:
            self._cached_config = {}
    




    def set_window(self, window):
        self._window = window

    def set_active_tab(self, tab_name):
        self.active_tab = tab_name

    def is_engine_running(self):
        return self.bot_running

    def _start_tg(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.tg_manager.start_watching())

    def toggle_bot_engine(self, active):
        self.bot_running = active
        if active:
            self._log_to_ui('INFO', '🚀 Підготовка до атаки...')
        else:
            self._log_to_ui('WARN', '🛑 Сигнал на зупинку...')
            
        # --- ВІДПРАВКА СТАТУСУ В ТГ ---
        try:
            cfg = self.load_config()
            tg_cfg = cfg.get('telegram', {})
            if tg_cfg.get('enabled') and tg_cfg.get('notifyStatus'):
                msg = "🚀 Bot START" if active else "🛑 Bot STOP"
                # Запускаємо через оркестратор
                asyncio.run_coroutine_threadsafe(TelegramService.send_message(cfg, msg), self.orchestrator.loop)
        except Exception as e:
            print(f"Помилка ТГ статусу: {e}")

        return self.bot_running



    def _run_trading_engine_thread(self):
        try:
            self.trading_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.trading_loop)
            self.trading_loop.run_until_complete(self._run_trading_engine())
        except Exception as e:
            self._log_to_ui('ERR', f'❌ Помилка потоку: {e}')
            traceback.print_exc()
        finally:
            if self.trading_loop:
                self.trading_loop.close()
            self.bot_running = False
            self.trading_loop = None
    
    async def _run_trading_engine(self):
        try:
            config = self.load_config()
            handshake = config.get('handshake')
            
            if not handshake:
                self._log_to_ui('ERR', '❌ Handshake не введено!')
                return
            
            self.bot_instance = self._create_bot_instance(handshake, config)
            await self.bot_instance.start()
            
            self._log_to_ui('OK', '✅ Підключено до сервера!')
            
            await self.bot_instance.start_trading(
                on_log=self._log_to_ui,
                on_price_update=self._update_ui_prices
            )
             
        except Exception as e:
            self._log_to_ui('ERR', f'❌ Помилка: {e}')
            traceback.print_exc()
        finally:
            if self.bot_instance:
                await self.bot_instance.stop()
            self.bot_running = False
    
    async def _stop_trading(self):
        if self.bot_instance:
            await self.bot_instance.stop()
            self.bot_instance = None
        self.bot_running = False
    
    def _log_to_ui(self, msg_type: str, message: str):
        if not self._window:
            return
        try:
            cfg = self.load_config()
            configured_level = str(cfg.get('logLevel', 'INFO')).upper()

            levels_order = {'ALL': 0, 'INFO': 1, 'WARN': 2, 'ERROR': 3}
            msg_severity_map = {
                'ERR': levels_order['ERROR'],
                'WARN': levels_order['WARN'],
                'INFO': levels_order['INFO'],
                'OK': levels_order['INFO'],  
            }
            msg_sev = msg_severity_map.get(msg_type, levels_order['INFO'])
            cfg_sev = levels_order.get(configured_level, levels_order['INFO'])

            if msg_sev < cfg_sev:
                return

            safe_msg = message.replace('"', '\\"').replace('\n', '\\n')
            self._window.evaluate_js(f"addLog('{msg_type}', \"{safe_msg}\")")
        except Exception as e:
            print(f"Помилка логування: {e}")

    def _update_ui_prices(self, lot_price=None, request_price=None, calculated_price=None, mode=None, price_valid=None):
        if not self._window:
            return

        try:
            lp_literal = 'null' if lot_price is None else f"{float(lot_price):.2f}"
            rp_literal = 'null' if request_price is None else f"{float(request_price):.2f}"
            cp_literal = 'null' if calculated_price is None else f"{float(calculated_price):.2f}"
            price_valid_js = 'true' if bool(price_valid) else 'false'

            js_code = f"""
            (function() {{
                try {{
                    const lp = {lp_literal};
                    if (lp !== null) {{
                        const el = document.getElementById('lot-price-display');
                        if (el) el.textContent = '$' + Number(lp).toFixed(2);
                    }}

                    const rp = {rp_literal};
                    if (rp !== null) {{
                        const el = document.getElementById('order-price-display');
                        if (el) el.textContent = '$' + Number(rp).toFixed(2);
                    }}

                    const cp = {cp_literal};
                    if (cp !== null) {{
                        const el = document.getElementById('final-price-display');
                        if (el) {{
                            el.textContent = '$' + Number(cp).toFixed(2);
                            el.style.color = {price_valid_js} ? 'var(--accent)' : '#ff4c4c';
                        }}
                    }}
                }} catch(e) {{}}
            }})();
            """
            self._window.evaluate_js(js_code)
        except Exception as e:
            print(f"Помилка оновлення UI: {e}")

    # --- БЕЗПЕЧНА РОБОТА З КОНФІГОМ ---

    def _create_bot_instance(self, handshake: str, config: dict) -> GameBot:
        """Фабрика для правильного збирання GameBot з усіма залежностями"""
        from Astandy import StandClient
        from services.inventory_service import InventoryService
        from services.market_service import MarketService
        from services.pricing_service import PricingService
        from services.trading_engine import TradingEngine
        
        # 1. Створюємо базові клієнти та сервіси
        client = StandClient(handshake)
        pricing = PricingService()
        if config:
            pricing.set_config(config)
            
        inventory = InventoryService(client)
        market = MarketService(client, pricing)
        trading_engine = TradingEngine(market, config or {})
        
        # 2. Інжектимо їх у бота
        return GameBot(
            handshake=handshake,
            client=client,
            pricing=pricing,
            inventory=inventory,
            market=market,
            trading_engine=trading_engine,
            config=config
        )



    def _run_safely_in_bot_loop(self, coro):
        if not self.shared_bot:
            coro.close() 
            return {"success": False, "error": "Бот ще завантажується. Зачекайте пару секунд..."}
        
        # Використовуємо наш новий оркестратор!
        return self.orchestrator.run_task(coro)



    def fetch_trade_debug(self, handshake, item_def_id):
        return {"success": False, "error": "Функція дебагу відключена для стабільності"}

    def start_price_polling(self):
        return self.polling_manager.start()

    def stop_price_polling(self):
        return self.polling_manager.stop()



if __name__ == '__main__':
    try:
        import webview
        api = Api()
        window = webview.create_window(
            title='xXx Trading Bot',
            url = get_ui_path(),
            js_api=api,
            width=800,
            height=600,
            resizable=False,
            background_color='#1a1a2e',
            text_select=False
        )
        api.set_window(window)
        webview.start()
        os._exit(0)

    except Exception as e:
        print(f"❌ КРИТИЧНА ПОМИЛКА ПРИ ЗАПУСКУ: {e}")
        import traceback
        traceback.print_exc()
        input("Press any key to continue...")