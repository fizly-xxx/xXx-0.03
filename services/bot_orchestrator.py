import asyncio
import threading
import traceback
from typing import Coroutine, Any

class BotOrchestrator:
    """
    Керує єдиним асинхронним циклом у фоновому потоці.
    Це вирішить проблему з 'зависаннями' та конфліктами потоків.
    """
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._start_loop, daemon=True, name="AsyncBotLoop")
        self.is_running = False

    def start(self):
        """Запускає фоновий потік з event loop"""
        if not self.is_running:
            self.is_running = True
            self._thread.start()

    def _start_loop(self):
        """Внутрішній метод для запуску циклу в потоці"""
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        except Exception as e:
            print(f"Критична помилка в BotOrchestrator: {e}")
            traceback.print_exc()
        finally:
            self.loop.close()

    def run_task(self, coro: Coroutine) -> Any:
        """
        Безпечно запускає асинхронну функцію (корутину) з синхронного коду (з UI) 
        і чекає на результат.
        """
        if not self.is_running:
            return {"success": False, "error": "Оркестратор не запущено"}
        
        try:
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            # Чекаємо результат з таймаутом, щоб UI не завис назавжди
            return future.result(timeout=15) 
        except Exception as e:
            print(f"Помилка виконання таски: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def stop(self):
        """Зупиняє цикл"""
        self.is_running = False
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)