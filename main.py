import asyncio
import json
import os
import re
from datetime import datetime

import pytz
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from dotenv import load_dotenv
from rapidfuzz import process, fuzz

load_dotenv()

TOKEN = os.getenv('TOKEN')
CITIES_FILE = "cities_timezones.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

with open(CITIES_FILE, "r", encoding="utf-8") as f:
    CITIES_TZ = json.load(f)

def normalize_city(text: str) -> str:
    if not text:
        return ""

    text = text.lower().strip()
    text = text.replace("ё", "е")
    text = re.sub(r"[^\w\s-]", "", text)
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text


NORMALIZED_CITIES = {
    normalize_city(city): city
    for city in CITIES_TZ.keys()
}


def get_timezone_from_city(city: str) -> str:
    if not city:
        return "Europe/Moscow"

    norm_city = normalize_city(city)

    if norm_city in NORMALIZED_CITIES:
        real_name = NORMALIZED_CITIES[norm_city]
        tz = CITIES_TZ.get(real_name)
        if tz:
            return tz

    match = process.extractOne(
        norm_city,
        NORMALIZED_CITIES.keys(),
        scorer=fuzz.ratio
    )

    if match:
        best_match, score, _ = match
        if score >= 75:
            real_name = NORMALIZED_CITIES[best_match]
            tz = CITIES_TZ.get(real_name)
            if tz:
                return tz

    return "Europe/Moscow"


def get_timezone(chat_title: str) -> str:
    if not chat_title:
        return "Europe/Moscow"

    if "Vaffel:" in chat_title:
        city = chat_title.split("Vaffel:")[-1].strip()
        return get_timezone_from_city(city)

    return "Europe/Moscow"


def is_working_time(tz_str: str) -> bool:
    tz = pytz.timezone(tz_str)
    now = datetime.now(tz)

    weekday = now.weekday()
    hour = now.hour

    return 0 <= weekday <= 4 and 9 <= hour < 20
    #return 9 <= hour < 20


@dp.message()
async def handle_message(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    tz = get_timezone(message.chat.title or "")
    now = datetime.now(pytz.timezone(tz))
    working = is_working_time(tz)

    print(f"Chat: {message.chat.title}")
    print(f"Timezone: {tz}")
    print(f"Local time: {now}")
    print(f"Working time: {working}")
    print("-" * 50)

    if not working:
        await message.reply(
            "📧 Спасибо за сообщение! 🧡\n"
            "Сейчас команда Vaffel уже не в онлайне — мы на связи по будням с 9:00 до 20:00.\n"
            "Ваш вопрос я уже зафиксировал, и в ближайшее рабочее время коллеги обязательно вернутся с ответом.\n"
            "До скорой связи 😊"
        )


async def main():
    print("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())