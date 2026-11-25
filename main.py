import asyncio
import os
import logging
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Налаштування логування (безпечний та чистий моніторинг подій)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Безпечне зчитування токена зі змінних середовища Render
API_TOKEN = os.getenv("BOT_TOKEN")

if not API_TOKEN:
    logger.error("Помилка: не задано змінну середовища BOT_TOKEN!")
    raise ValueError("Помилка: не задано змінну середовища BOT_TOKEN!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_keyboard():
    button_today = KeyboardButton(text="Графік на сьогодні")
    button_tomorrow = KeyboardButton(text="Графік на завтра")
    return ReplyKeyboardMarkup(keyboard=[[button_today], [button_tomorrow]], resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    logger.info(f"Користувач {message.from_user.id} запустив бота.")
    await message.answer(
        "Вітаю! Оберіть, на який день вас цікавить графік для черги 3.1:",
        reply_markup=get_keyboard()
    )

async def fetch_schedule(message: types.Message, target_date_str: str, display_date_label: str):
    url = "https://be-svitlo.oe.if.ua/schedule-by-queue?queue=3.1"
    try:
        # Використовуємо таймаут, щоб уникнути зависання бота
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                    except Exception as json_err:
                        logger.error(Stops parsing error: {json_err})
                        await message.answer("⚠️ Помилка обробки даних від сервера.")
                        return

                    found = False
                    if data and isinstance(data, list):
                        for item in data:
                            if item.get("eventDate") == target_date_str:
                                schedule = item.get("queues", {}).get("3.1", [])
                                if schedule:
                                    hours = "\n".join([f"• {h.get('shutdownHours', 'Не вказано')}" for h in schedule])
                                    text = f"📋 Черга 3.1 на {display_date_label} ({target_date_str}):\n\n{hours}"
                                else:
                                    text = f"✅ Черга 3.1 на {display_date_label} ({target_date_str}): без вимкнень."
                                await message.answer(text)
                                found = True
                                break
                    if not found:
                        await message.answer(f"⚠️ Даних для черги 3.1 на {display_date_label} ще немає.")
                else:
                    logger.warning(f"Зовнішній сервер повернув статус: {response.status}")
                    await message.answer("Помилка сервера. Спробуйте пізніше.")
    except asyncio.TimeoutError:
        logger.error("Перевищено час очікування відповіді від сервера (Timeout).")
        await message.answer("⏱ Час очікування минув. Сервер не відповідає.")
    except Exception as e:
        logger.error(f"Непередбачувана помилка під час запиту: {e}")
        await message.answer("Не вдалося отримати дані. Перевірте з'єднання.")

@dp.message(F.text == "Графік на сьогодні")
async def today_schedule(message: types.Message):
    today_str = datetime.now().strftime("%d.%m.%Y")
    await fetch_schedule(message, today_str, "сьогодні")

@dp.message(F.text == "Графік на завтра")
async def tomorrow_schedule(message: types.Message):
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    await fetch_schedule(message, tomorrow_str, "завтра")

async def main():
    logger.info("Бот запущено і починає опитування (polling)...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинений.")
