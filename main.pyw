import webview
import json
import os

class Api:
    def save_config(self, data):
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return "Saved"

    def load_config(self):
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

# Створюємо вікно і передаємо Python-клас у JavaScript (js_api)
if __name__ == '__main__':
    api = Api()
    webview.create_window('xXx API', 'index.html', js_api=api, width=600, height=600, resizable=False)
    webview.start()