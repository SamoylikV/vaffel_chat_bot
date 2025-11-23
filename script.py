import asyncio
import aiohttp
import json
import time

GEONAMES_USERNAME = "senya_glue"

BASE_URL = "http://api.geonames.org"
MAX_ROWS = 1000
CITY_FEATURE_CODES = {"PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4"}

city_tz = {}
total_cities = 0
start_time = None
sem = asyncio.Semaphore(50)  # ограничение параллельных запросов


async def fetch_json(session, url, params):
    async with session.get(url, params=params) as resp:
        return await resp.json()


async def get_timezone(session, name, lat, lng):
    global total_cities
    async with sem:
        data = await fetch_json(session, f"{BASE_URL}/timezoneJSON", {
            "lat": lat,
            "lng": lng,
            "username": GEONAMES_USERNAME
        })

    tz = data.get("timezoneId")
    if tz:
        city_tz[name] = tz
        total_cities += 1

        if total_cities % 100 == 0:
            elapsed = time.time() - start_time
            speed = total_cities / elapsed if elapsed > 0 else 0
            print(f"[✓] {total_cities} городов | {speed:.1f} городов/сек")


async def main():
    global start_time
    start_time = time.time()

    start_row = 0

    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:

        print("▶ Начинаю загрузку городов...")

        while True:
            search_data = await fetch_json(session, f"{BASE_URL}/searchJSON", {
                "country": "RU",
                "featureClass": "P",
                "maxRows": MAX_ROWS,
                "startRow": start_row,
                "username": GEONAMES_USERNAME,
                "lang": "ru"
            })

            geonames = search_data.get("geonames", [])
            if not geonames:
                break

            print(f"• Загружено: {len(geonames)} объектов (страница {start_row})")

            tasks = []
            added = 0

            for city in geonames:
                name = city.get("name")
                lat = city.get("lat")
                lng = city.get("lng")
                fcode = city.get("fcode")

                if not name or not lat or not lng:
                    continue
                if fcode not in CITY_FEATURE_CODES:
                    continue

                tasks.append(get_timezone(session, name, lat, lng))
                added += 1

            print(f"  → В обработку отправлено: {added} городов")

            # ✅ Запускаем пачку сразу
            await asyncio.gather(*tasks)

            start_row += MAX_ROWS

    with open("cities_timezones.json", "w", encoding="utf-8") as f:
        json.dump(city_tz, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print("\n✅ Готово!")
    print(f"• Всего городов: {total_cities}")
    print(f"• Время работы: {elapsed:.2f} сек")


if __name__ == "__main__":
    asyncio.run(main())