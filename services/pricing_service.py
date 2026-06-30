import random
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

# --- 1. Інтерфейс для всіх стратегій ціноутворення ---
class IPricingStrategy(ABC):
    @abstractmethod
    def calculate(self, lot_price: Optional[float], request_price: Optional[float], config: Dict[str, Any]) -> float:
        pass

# --- 2. Конкретні реалізації стратегій ---
class RandomPricingStrategy(IPricingStrategy):
    def calculate(self, lot_price: Optional[float], request_price: Optional[float], config: Dict[str, Any]) -> float:
        """Рандомний перебив: вибирає випадковий крок 1-4 копійки."""
        if request_price is None or request_price <= 0:
            return 0.01
        
        offset = random.choice([0.01, 0.02, 0.03, 0.04])
        calculated = request_price + offset
        
        if lot_price is not None and calculated >= lot_price:
            return lot_price - 0.01
            
        return max(0.01, calculated)

class CustomPricingStrategy(IPricingStrategy):
    def calculate(self, lot_price: Optional[float], request_price: Optional[float], config: Dict[str, Any]) -> float:
        """Фіксована ціна з налаштувань (Custom Price)"""
        offset = float(config.get('customPrice', 0.01))
        return max(0.01, (request_price or 0) + offset)

class OutbidPricingStrategy(IPricingStrategy):
    def calculate(self, lot_price: Optional[float], request_price: Optional[float], config: Dict[str, Any]) -> float:
        """Режим 'Under Lot': ставимо на X дешевше за найменший лот"""
        if lot_price is None or lot_price <= 0:
            return 0.01
        
        delta = float(config.get('outbidDelta', 0.01))
        return max(0.01, lot_price - delta)

# --- 3. Головний сервіс, який керує стратегіями ---
class PricingService:
    def __init__(self):
        self.mode = 'custom'
        self.config = {}
        
        # Реєструємо наші стратегії у словник
        self._strategies = {
            'random': RandomPricingStrategy(),
            'custom': CustomPricingStrategy(),
            'outbid': OutbidPricingStrategy()
        }

    def set_config(self, config: Dict[str, Any]):
        self.config = config
        self.mode = config.get('mode', 'custom')

    def calculate_price(self, lot_price: Optional[float] = None, request_price: Optional[float] = None) -> float:
        """Головний метод розрахунку ціни"""
        limit_price = float(self.config.get('limitPrice', 999999.0))
        
        # Отримуємо потрібну стратегію зі словника (або custom, якщо щось пішло не так)
        strategy = self._strategies.get(self.mode, self._strategies['custom'])
        
        # Розраховуємо ціну за вибраною стратегією
        price = strategy.calculate(lot_price, request_price, self.config)
            
        return min(round(price, 2), limit_price)

    def get_mode(self) -> str:
        return self.mode

    def get_delay(self) -> int:
        """Повертає Trade Delay (ms)"""
        return int(self.config.get('tradeDelay', 1000))

    @staticmethod
    def calculate_smart_sell_price(prices_list: list[float]) -> float:
        """Аналізує список цін конкурентів і видає оптимальну ціну для продажу"""
        if not prices_list:
            return 0.01
            
        if len(prices_list) < 3: 
            return round(prices_list[0] - 0.01, 2)
            
        i = 0
        while i < len(prices_list) - 1:
            current_price = prices_list[i]
            count = 1
            for j in range(i + 1, len(prices_list)):
                if prices_list[j] - current_price <= current_price * 0.005: 
                    count += 1
                else: 
                    break
            
            next_idx = i + count
            if next_idx < len(prices_list):
                next_price = prices_list[next_idx]
                gap = (next_price - current_price) / current_price
                if count < 5 and gap > 0.01:
                    i = next_idx
                    continue
            
            if i > 0:
                raw_target = current_price * 0.995
                rounded_target = round(raw_target)
                if prices_list[i-1] < rounded_target < current_price:
                    return float(rounded_target)
                return max(0.01, round(raw_target, 2))
            else:
                return max(0.01, round(current_price - 0.01, 2))
                
        return round(prices_list[0] - 0.01, 2)