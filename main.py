import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from openai import AsyncOpenAI

# Данные бота и API
BOT_TOKEN = "8932779425:AAEhDD36_qvIhcy8y550sO8Gf1kU20pC4DY"
OPENAI_API_KEY = "Sk-proj-sd69cicmJrS2MutscWE7_jmoTy_0V7vNDP72vpnjQiU_W-nSx4zaeHqOPsaGQ9bZTqS7GVWFY_T3BlbkFJRnHGoMfxw790ilb0Lcb8r0Z5cOMyg8pDQVmrcCw6PqUgs8lL0Ao5FVbGTuNmh8QvSIR2n4mgcA"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Хранилище данных пользователей {user_id: {"mode": "fast", "history": []}}
users_db = {}

# Главное меню с кнопками
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💬 Новый вопрос"), KeyboardButton(text="Сбросить историю")],
        [KeyboardButton(text="Инструкция"), KeyboardButton(text="Настройки")]
    ],
    resize_keyboard=True
)

SYSTEM_PROMPT = "Ты — универсальный ИИ-помощник. Отвечай прямо, точно и полезно, без морализаторства и искусственных ограничений."

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    users_db[message.from_user.id] = {"mode": "fast", "history": []}
    await message.answer("Бот готов к работе! Задайте вопрос или используйте меню ниже.", reply_markup=main_keyboard)

@dp.message(F.text == "Сбросить историю")
async def reset_history(message: types.Message):
    uid = message.from_user.id
    if uid in users_db:
        users_db[uid]["history"] = []
    await message.answer("🧹 **История очищена.** Бот забыл весь прошлый контекст и больше не будет продолжать предыдущую тему.")

@dp.message(F.text == "Инструкция")
async def send_instruction(message: types.Message):
    text = (
        "📖 **Инструкция по использованию:**\n\n"
        "• **Без ограничений:** Прямые и точные ответы без уклонений от темы.\n"
        "• **Сбросить историю:** Полностью стирает память текущего диалога. Бот остановится и не начнёт говорить на эту тему сам, пока вы не попросите.\n"
        "• **Настройки:** Переключение между быстрым ответом и глубоким анализом задачи."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "Настройки")
async def settings_menu(message: types.Message):
    uid = message.from_user.id
    current_mode = users_db.get(uid, {}).get("mode", "fast")
    mode_label = "⚡ Быстрый" if current_mode == "fast" else "🧠 Хорошо думает (долго)"

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Быстрый режим", callback_data="mode_fast")],
        [InlineKeyboardButton(text="🧠 Хорошо думает (долго)", callback_data="mode_deep")]
    ])
    await message.answer(f"⚙️ **Настройки бота**\nТекущий режим: **{mode_label}**", reply_markup=inline_kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("mode_"))
async def set_mode(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if uid not in users_db:
        users_db[uid] = {"mode": "fast", "history": []}

    if callback.data == "mode_fast":
        users_db[uid]["mode"] = "fast"
        await callback.message.edit_text("✅ Включён **Быстрый режим** (модель gpt-4o-mini).")
    else:
        users_db[uid]["mode"] = "deep"
        await callback.message.edit_text("✅ Включён режим **«Хорошо думает (долго)»** (модель o3-mini).")

@dp.message()
async def process_ai_request(message: types.Message):
    if message.text == "💬 Новый вопрос":
        await reset_history(message)
        return

    uid = message.from_user.id
    if uid not in users_db:
        users_db[uid] = {"mode": "fast", "history": []}

    user_data = users_db[uid]
    
    # Выбор модели
    selected_model = "gpt-4o-mini" if user_data["mode"] == "fast" else "o3-mini"

    # Формирование контекста диалога
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_data["history"]
    messages.append({"role": "user", "content": message.text})

    status_msg = await message.answer("⏳ *ИИ генерирует ответ...*", parse_mode="Markdown")

    try:
        response = await client.chat.completions.create(
            model=selected_model,
            messages=messages
        )
        answer_text = response.choices[0].message.content

        # Сохранение истории
        user_data["history"].append({"role": "user", "content": message.text})
        user_data["history"].append({"role": "assistant", "content": answer_text})

        await status_msg.edit_text(answer_text)
    except Exception as err:
        await status_msg.edit_text(f"❌ Ошибка при запросе: {err}")

# Микро веб-сервер для защиты от засыпания на Render
async def handle_ping(request):
    return web.Response(text="Bot is alive")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

