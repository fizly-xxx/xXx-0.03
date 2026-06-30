import json
import os
from utils import get_jsons_dir

class ConfigService:
    def __init__(self, file_path=None):
        if file_path is None:
            file_path = os.path.join(get_jsons_dir(), 'config.json')
            
        self.file_path = file_path
        self.config = {}
        self.load()

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Помилка читання конфігурації: {e}")
                self.config = {}
        else:
            self.config = {}
        return self.config

    def save(self, data: dict = None):
        if data:
            self.config.update(data)
        
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Помилка збереження конфігурації: {e}")
            return False

    def get(self, key, default=None):
        return self.config.get(key, default)

    @property
    def is_tg_enabled(self):
        return self.get('telegramEnabled', False)