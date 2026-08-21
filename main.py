import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import google.generativeai as genai

# --- КОНФИГУРАЦИЯ ---
# Вставь свои данные сюда, если не хочешь использовать переменные окружения
BOT_TOKEN = "8932779425:AAEhDD36_qvIhcy8y550sO8Gf1kU20pC4DY"
GOOGLE_API_KEY = "AQ.Ab8RN6LVNmVf7vwe9vyfsCc7tXoXJ5BwztOcU0PME-hS8h66eA"

# Настройка ИИ
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Настройка Бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# База данных для хранения истории (в памяти)
users_db = {}

# --- КЛАВИАТУРЫ ---
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💬 Новый вопрос"), KeyboardButton(text="Сбросить историю")],
        [KeyboardButton(text="Инструкция"), KeyboardButton(text="Настройки")]
    ],
    resize_keyboard=True
)

# --- ХЕНДЛЕРЫ (ЛОГИКА БОТА) ---

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    users_db[message.from_user.id] = []
    await message.answer(
        "Привет! Я ИИ-ассистент. Готов помочь с любым вопросом.", 
        reply_markup=main_keyboard
    )

@dp.message(F.text == "Сбросить историю")
async def reset_history(message: types.Message):
    users_db[message.from_user.id] = []
    await message.answer("🧹 История очищена. Бот забыл весь контекст.")

@dp.message(F.text == "Инструкция")
async def send_instruction(message: types.Message):
    text = (
        "📖 **Как пользоваться:**\n"
        "1. Просто пиши вопрос в чат.\n"
        "2. Используй 'Сбросить историю', если тема сменилась.\n"
        "3. Настройки позволяют менять параметры."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "Настройки")
async def settings_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Быстрый режим", callback_data="mode_fast")],
        [InlineKeyboardButton(text="🧠 Глубокий режим", callback_data="mode_deep")]
    ])
    await message.answer("⚙️ Выберите режим работы ИИ:", reply_markup=kb)

@dp.callback_query(F.data.startswith("mode_"))
async def handle_mode(callback: types.CallbackQuery):
    mode = "Быстрый" if callback.data == "mode_fast" else "Глубокий"
    await callback.message.edit_text(f"✅ Режим изменен на: **{mode}**", parse_mode="Markdown")

@dp.message()
async def ai_handler(message: types.Message):
    if message.text in ["💬 Новый вопрос", "Сбросить историю", "Инструкция", "Настройки"]:
        return

    uid = message.from_user.id
    if uid not in users_db:
        users_db[uid] = []

    chat = model.start_chat(history=users_db[uid])
    status_msg = await message.answer("⏳ ИИ думает...")

    try:
        response = chat.send_message(message.text)
        users_db[uid] = chat.history
        await status_msg.edit_text(response.text)
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="Bot is running")

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
