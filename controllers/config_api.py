import json, os
from utils import get_ui_path, get_jsons_dir

class ConfigApiMixin:
    def load_config(self): 
        with self._config_lock:
            return self._cached_config.copy()

    def save_config(self, data): 
        with self._config_lock:
            self._cached_config.update(data)
            return self.config_service.save(self._cached_config)

    def load_python_weapons(self):
        file_path = os.path.join(get_jsons_dir(), 'weapons.json')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
