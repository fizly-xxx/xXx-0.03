class InventoryApiMixin:
    def fetch_inventory(self, handshake):
        async def _coro():
            items, gold = await self.shared_bot.inventory.get_inventory_and_balance()
            items_data = []
            
            for item in items:
                modifications = getattr(item, 'modifications', [])
                sticker_count = 0
                
                # Поле modifications — це словник (map). 
                # Проходимо по ключах і рахуємо ті, що містять "sticker_"
                for mod_key in modifications:
                    if isinstance(mod_key, str):
                        if "sticker_" in mod_key:
                            sticker_count += 1
                    elif hasattr(mod_key, 'key'): # про всяк випадок для інших версій
                        if "sticker_" in mod_key.key:
                            sticker_count += 1
                
                items_data.append({
                    "id": item.id, 
                    "def_id": item.itemDefinitionId,
                    "name": self.skins_service.get_name(item.itemDefinitionId),
                    "emoji": "🔫",
                    "stickers": sticker_count
                })
            
            return {"success": True, "gold": gold, "items": items_data}
        
        return self._run_safely_in_bot_loop(_coro())