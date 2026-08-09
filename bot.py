import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

# Замените этот токен на тот, который вы получили от @BotFather
BOT_TOKEN = "8716268896:AAFc6JwhvtLrPZgnn8P-QsWPFxQ3FcnL-RI"

# Пока поставим тестовую ссылку. Позже мы заменим её на ваш сайт
WEB_APP_URL = "https://dotametabot.vercel.app" 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    # Создаем кнопку, которая открывает Web App прямо внутри Telegram
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📊 Открыть мету Dota 2", 
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ]
    ])
    
    await message.answer(
        "Привет! Нажми на кнопку ниже, чтобы открыть актуальную статистику героев и их сборок:",
        reply_markup=keyboard
    )

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())