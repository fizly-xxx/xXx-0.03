import aiohttp
import logging

class TelegramService:
    @staticmethod
    async def send_message(config: dict, text: str):
        tg_cfg = config.get('telegram', {})
        # Перевірка чи заповнені дані в UI
        if not tg_cfg.get('enabled') or not tg_cfg.get('token') or not tg_cfg.get('chatId'):
            return

        url = f"https://api.telegram.org/bot{tg_cfg['token']}/sendMessage"
        payload = {
            'chat_id': tg_cfg['chatId'],
            'text': text,
            'parse_mode': 'HTML'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=5) as resp:
                    if resp.status != 200:
                        logging.error(f"Telegram Error: {await resp.text()}")
        except Exception as e:
            logging.error(f"Telegram Connection Error: {e}")