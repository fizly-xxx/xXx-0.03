from interfaces.iinventory import IInventoryService
from Astandy import StandClient
from Astandy.generated.services import GetPlayerInventoryRequest

class InventoryService(IInventoryService):
    def __init__(self, client: StandClient):
        self.client = client

    async def get_inventory_and_balance(self):
        request = GetPlayerInventoryRequest()
        raw = await self.client.send_request(
            *self.client.raw.InventoryRemoteService.getPlayerInventoryEncryptedRequest(request, self.client.cipher)
        )
        res = self.client.raw.InventoryRemoteService.getPlayerInventoryEncryptedResponse(raw, self.client.cipher)
        
        items = res.playerInventory.inventoryItems
        
        # ЎукаЇмо валюту з ID 102 (Gold) [cite: 68, 69]
        gold = 0.0
        for currency in res.playerInventory.currencies:
            if currency.currencyId == 102:
                gold = currency.value
                break
                
        return items, gold