import json
import os
from utils import get_jsons_dir

class SkinsService:
    def __init__(self, file_path=None):
        if file_path is None:
            file_path = os.path.join(get_jsons_dir(), 'skins.json')
            
        self.items_map = {}
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.items_map = {str(item['id']): item['name'] for item in data}
            except Exception as e:
                print(f"Помилка бази предметів: {e}")

    def get_name(self, def_id):
        return self.items_map.get(str(def_id), f"ID: {def_id}")