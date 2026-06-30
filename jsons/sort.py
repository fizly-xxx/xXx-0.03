import json
import re

# English categories
GUNS = {
    "PISTOLS": ["G22", "USP", "P350", "Berettas", "TEC-9", "F/S", "Desert Eagle"],
    "SMGS": ["MAC10", "UMP45", "MP5", "MP7", "Akimbo Uzi", "P90"],
    "RIFLES": ["FN FAL", "FAMAS", "VAL", "M4A1", "M4", "AKR12", "AKR", "M16"],
    "SHOTGUNS": ["FabM", "SM1014", "SPAS", "M60"],
    "SNIPERS": ["M40", "Mallard", "M110", "AWM"]
}

KNIFES = ["M9 Bayonet", "Karambit", "jKommando", "Butterfly", "Flip", "Kunai", "Scorpion", "Tanto", "Dual Daggers", "Kukri", "Stiletto", "Mantis", "Fang", "Sting"]

# Додали рукавиці
GLOVES = ["Gloves"]

result = {
    "GUNS": {cat: {w: [] for w in weapons} for cat, weapons in GUNS.items()},
    "KNIFES": {knife: [] for knife in KNIFES},
    "GLOVES": {glove: [] for glove in GLOVES}
}

# Читаємо ТЕКСТОВИЙ файл
with open("items.txt", "r", encoding="utf-8") as file:
    content = file.read()

blocks = content.split("inventoryItemDefinitions {")[1:]

for block in blocks:
    id_match = re.search(r'id:\s*(\d+)', block)
    item_id = int(id_match.group(1)) if id_match else None
    
    name_match = re.search(r'displayName:\s*"(.*)"', block)
    full_name = name_match.group(1).replace('\\"', '"') if name_match else ""
    
    if not item_id or not full_name:
        continue
    
    is_stattrak = bool(re.search(r"(?i)StatTrack|StatTrak", full_name))
    
    if not is_stattrak:
        props = re.findall(r'properties\s*\{\s*key:\s*"([^"]+)"\s*value:\s*"([^"]+)"\s*\}', block)
        for key, value in props:
            if key == "stattrack" and value == "true":
                is_stattrak = True
                break
                
    clean_name = re.sub(r"(?i)\s*(StatTrack|StatTrak)\s*", "", full_name).strip()
    
    found = False

    # 1. Перевірка на Рукавиці
    for glove in GLOVES:
        if clean_name == glove or clean_name.startswith(glove + " ") or clean_name.startswith(glove + '"'):
            skin_name = clean_name[len(glove):].strip(' "-_') or "Default"
            result["GLOVES"][glove].append({
                "id": item_id,
                "skin": skin_name,
                "is_stattrak": is_stattrak
            })
            found = True
            break
            
    if found: continue

    # 2. Перевірка на Ножі
    for knife in KNIFES:
        if clean_name == knife or clean_name.startswith(knife + " ") or clean_name.startswith(knife + '"'):
            skin_name = clean_name[len(knife):].strip(' "-_') or "Default"
            result["KNIFES"][knife].append({
                "id": item_id,
                "skin": skin_name,
                "is_stattrak": is_stattrak
            })
            found = True
            break
            
    if found: continue

    # 3. Перевірка на Зброю (з фіксом для M40)
    for cat, weapons in GUNS.items():
        for w in weapons:
            # Фікс: перевіряємо, щоб після назви йшов пробіл, лапки, або це була точна назва.
            if clean_name == w or clean_name.startswith(w + " ") or clean_name.startswith(w + '"'):
                skin_name = clean_name[len(w):].strip(' "-_') or "Default"
                result["GUNS"][cat][w].append({
                    "id": item_id,
                    "skin": skin_name,
                    "is_stattrak": is_stattrak
                })
                found = True
                break
        if found: break

# Чистка порожніх
for cat in result["GUNS"]:
    result["GUNS"][cat] = {w: skins for w, skins in result["GUNS"][cat].items() if skins}

result["KNIFES"] = {k: skins for k, skins in result["KNIFES"].items() if skins}
result["GLOVES"] = {g: skins for g, skins in result["GLOVES"].items() if skins}
result["GUNS"] = {cat: weapons for cat, weapons in result["GUNS"].items() if weapons}

# Зберігаємо
with open("sorted_weapons.json", "w", encoding="utf-8") as file:
    json.dump(result, file, indent=4, ensure_ascii=False)

print("Done! File sorted_weapons.json has been generated successfully.")