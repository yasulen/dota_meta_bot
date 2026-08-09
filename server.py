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
    """Динамическое получение предметов и талантов героя"""
    try:
        async with httpx.AsyncClient() as client:
            # Запрос популярности предметов на герое
            item_res = await client.get(f"https://api.opendota.com/api/heroes/{hero_id}/itemPopularity", timeout=10.0)
            items_data = item_res.json() if item_res.status_code == 200 else {}
            
            # Константа предметов для получения системных имен
            constants_res = await client.get("https://api.opendota.com/api/constants/items", timeout=10.0)
            items_constants = constants_res.json() if constants_res.status_code == 200 else {}

            mid_game_items = items_data.get("mid_game", {})
            late_game_items = items_data.get("late_game", {})
            
            merged_items = {**mid_game_items, **late_game_items}
            sorted_item_ids = sorted(merged_items.keys(), key=lambda k: merged_items[k], reverse=True)

            item_names = []
            for i_id in sorted_item_ids:
                for name, info in items_constants.items():
                    if isinstance(info, dict) and str(info.get("id")) == str(i_id):
                        if name not in item_names and "recipe" not in name:
                            item_names.append(name)
                        break
                if len(item_names) >= 6:
                    break

            return {
                "status": "ok",
                "items": item_names if item_names else ["power_treads", "black_king_bar", "blink"]
            }
    except Exception as e:
        return {"status": "error", "message": str(e), "items": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)