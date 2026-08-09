import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROLE_HEROES = {
    "POSITION_1": [18, 8, 54, 41, 12, 10, 73, 81],
    "POSITION_2": [74, 106, 17, 107, 46, 13, 61],
    "POSITION_3": [99, 98, 2, 96, 108, 129, 69],
    "POSITION_4": [64, 88, 27, 101, 86, 20],
    "POSITION_5": [31, 111, 5, 83, 30, 26]
}

# Кэш констант
CONSTANTS_CACHE = {
    "abilities": {},
    "items": {},
    "hero_abilities": {}
}

async def load_constants():
    async with httpx.AsyncClient() as client:
        try:
            abilities_res = await client.get("https://api.opendota.com/api/constants/abilities", timeout=10.0)
            items_res = await client.get("https://api.opendota.com/api/constants/items", timeout=10.0)
            hero_ab_res = await client.get("https://api.opendota.com/api/constants/hero_abilities", timeout=10.0)
            
            if abilities_res.status_code == 200:
                CONSTANTS_CACHE["abilities"] = abilities_res.json()
            if items_res.status_code == 200:
                CONSTANTS_CACHE["items"] = items_res.json()
            if hero_ab_res.status_code == 200:
                CONSTANTS_CACHE["hero_abilities"] = hero_ab_res.json()
        except Exception as e:
            print(f"Error loading constants: {e}")

@app.on_event("startup")
async def startup_event():
    await load_constants()

@app.get("/api/meta")
async def get_meta():
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get("https://api.opendota.com/api/heroStats", timeout=10.0)
            if res.status_code != 200:
                return {"status": "error", "message": "API error", "roles": {}}
            
            raw_heroes = res.json()
            heroes_by_id = {}

            for h in raw_heroes:
                picks = h.get("7_pick", 0) + h.get("8_pick", 0) + h.get("pro_pick", 0)
                wins = h.get("7_win", 0) + h.get("8_win", 0) + h.get("pro_win", 0)
                
                if picks == 0:
                    picks = h.get("turbo_picks", 1000)
                    wins = int(picks * 0.52)

                wr = round((wins / picks * 100), 1) if picks > 0 else 52.0
                short_name = h.get("name", "").replace("npc_dota_hero_", "")

                heroes_by_id[h.get("id")] = {
                    "id": h.get("id"),
                    "name": h.get("localized_name"),
                    "shortName": short_name,
                    "matches": picks,
                    "winrate": wr
                }

            result = {}
            for role, ids in ROLE_HEROES.items():
                role_list = [heroes_by_id[hid] for hid in ids if hid in heroes_by_id]
                role_list.sort(key=lambda x: x["winrate"], reverse=True)
                result[role] = role_list[:5]

            return {"status": "ok", "rank": "Immortal / Pro", "roles": result}
    except Exception as e:
        return {"status": "error", "message": str(e), "roles": {}}

@app.get("/api/hero/{hero_id}")
async def get_hero_detail(hero_id: int):
    try:
        if not CONSTANTS_CACHE["abilities"]:
            await load_constants()

        async with httpx.AsyncClient() as client:
            # 1. Запрос популярных предметов
            item_res = await client.get(f"https://api.opendota.com/api/heroes/{hero_id}/itemPopularity", timeout=10.0)
            items_data = item_res.json() if item_res.status_code == 200 else {}
            
            mid_items = items_data.get("mid_game", {})
            late_items = items_data.get("late_game", {})
            merged_items = {**mid_items, **late_items}
            sorted_item_ids = sorted(merged_items.keys(), key=lambda k: merged_items[k], reverse=True)

            item_names = []
            items_const = CONSTANTS_CACHE["items"]
            for i_id in sorted_item_ids:
                for name, info in items_const.items():
                    if isinstance(info, dict) and str(info.get("id")) == str(i_id):
                        if name not in item_names and "recipe" not in name and name != "blink":
                            item_names.append(name)
                        break
                if len(item_names) >= 6:
                    break

            # 2. Получение реальных талантов героя из констант
            hero_stats_res = await client.get("https://api.opendota.com/api/heroStats", timeout=10.0)
            hero_name_key = None
            if hero_stats_res.status_code == 200:
                for h in hero_stats_res.json():
                    if h.get("id") == hero_id:
                        hero_name_key = h.get("name")
                        break

            talents_list = []
            if hero_name_key and hero_name_key in CONSTANTS_CACHE["hero_abilities"]:
                abilities_keys = CONSTANTS_CACHE["hero_abilities"][hero_name_key].get("abilities", [])
                talent_keys = [a for a in abilities_keys if a.startswith("special_bonus_")]

                # Сортировка по уровням (10, 15, 20, 25)
                # Таланты возвращаются парами: [L10, R10, L15, R15, L20, R20, L25, R25]
                parsed_talents = []
                for t_key in talent_keys:
                    ab_info = CONSTANTS_CACHE["abilities"].get(t_key, {})
                    d_name = ab_info.get("dname", t_key.replace("special_bonus_", "").replace("_", " "))
                    parsed_talents.append(d_name)

                if len(parsed_talents) >= 8:
                    talents_list = [
                        {"lvl": 25, "left": parsed_talents[6], "right": parsed_talents[7]},
                        {"lvl": 20, "left": parsed_talents[4], "right": parsed_talents[5]},
                        {"lvl": 15, "left": parsed_talents[2], "right": parsed_talents[3]},
                        {"lvl": 10, "left": parsed_talents[0], "right": parsed_talents[1]}
                    ]

            return {
                "status": "ok",
                "items": item_names if item_names else ["arcane_boots", "blink", "black_king_bar"],
                "talents": talents_list
            }
    except Exception as e:
        return {"status": "error", "message": str(e), "items": [], "talents": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)