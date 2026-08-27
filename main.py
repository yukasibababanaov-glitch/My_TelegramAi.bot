import asyncio
import os
import json
import urllib.parse
import random
from aiohttp import web, ClientSession
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- ДАННЫЕ БОТА И API ---
BOT_TOKEN = "8932779425:AAEH0mqS6olP1cOaYIeB3ibt4u0MvPc7tac"
OPENROUTER_API_KEY = "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"

# Канал для обязательной подписки
CHANNEL_USERNAME = "@Ai_CHEAT_roblox"
CHANNEL_URL = "https://t.me/Ai_CHEAT_roblox"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users_db = {}

SYSTEM_PROMPT = (
    "Твои создатели и разработчики — @zehoq и @maksfunx. "
    "Всегда говори, что тебя создали именно они, если спрашивают про авторов, создателей или разработчиков. "
    "Отвечай кратко, точно, без лишней «воды» и без длинных лекций. "
    "На короткие приветствия (например, «Пр», «Привет», «Салам») отвечай коротко и дружелюбно."
)

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎨 Создать картинку"), KeyboardButton(text="💬 Новый вопрос")],
        [KeyboardButton(text="Сбросить историю"), KeyboardButton(text="Настройки")],
        [KeyboardButton(text="Инструкция")]
    ],
    resize_keyboard=True
)

async def check_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
    ])

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    uid = message.from_user.id
    users_db[uid] = {"mode": "fast", "history": []}
    
    if not await check_sub(uid):
        await message.answer(
            f"⚠️ **Доступ ограничен!**\n\nДля использования бота подпишитесь на наш канал: {CHANNEL_URL}",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown"
        )
        return

    await message.answer("Бот запущен и готов к работе!", reply_markup=main_keyboard)

@dp.message(F.text == "💬 Новый вопрос")
async def new_question_cmd(message: types.Message):
    uid = message.from_user.id
    if uid in users_db:
        users_db[uid]["history"] = []
        users_db[uid]["mode"] = "fast"
    else:
        users_db[uid] = {"mode": "fast", "history": []}

    if not await check_sub(uid):
        await message.answer(
            f"⚠️ **Доступ ограничен!**\n\nДля использования бота подпишитесь на наш канал: {CHANNEL_URL}",
            reply_markup=get_sub_keyboard(),
            parse_mode="Markdown"
        )
        return

    await message.answer("🔄 Чат сброшен! Задавай свой новый вопрос.", reply_markup=main_keyboard)

@dp.callback_query(F.data == "check_subscription")
async def check_sub_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if await check_sub(uid):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer("✅ Подписка подтверждена! Бот готов к работе.", reply_markup=main_keyboard)
    else:
        await callback.answer("❌ Вы всё ещё не подписаны на канал (или бот не назначен администратором в канале)!", show_alert=True)

@dp.message(F.text == "Сбросить историю")
async def reset_history(message: types.Message):
    uid = message.from_user.id
    if not await check_sub(uid):
        await message.answer("⚠️ Сначала подпишитесь на канал!", reply_markup=get_sub_keyboard())
        return
    if uid in users_db:
        users_db[uid]["history"] = []
    await message.answer("🧹 История очищена. Контекст сброшен.", reply_markup=main_keyboard)

@dp.message(F.text == "Инструкция")
async def send_instruction(message: types.Message):
    uid = message.from_user.id
    if not await check_sub(uid):
        await message.answer("⚠️ Сначала подпишитесь на канал!", reply_markup=get_sub_keyboard())
        return
    text = (
        "📖 **Инструкция:**\n\n"
        "• Задавайте любые вопросы в чат.\n"
        "• Нажмите **«🎨 Создать картинку»**, чтобы сгенерировать фото.\n"
        "• **💬 Новый вопрос** — сбросить контекст и начать диалог заново.\n"
        "• **Создатели бота:** @zehoq и @maksfunx"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard)

@dp.message(F.text == "🎨 Создать картинку")
async def image_mode_prompt(message: types.Message):
    uid = message.from_user.id
    if not await check_sub(uid):
        await message.answer("⚠️ Сначала подпишитесь на канал!", reply_markup=get_sub_keyboard())
        return
    
    if uid not in users_db:
        users_db[uid] = {"mode": "fast", "history": []}
    
    users_db[uid]["mode"] = "image_wait"
    await message.answer("🎨 Отправь текстовое описание картинки, и я её нарисую!", parse_mode="Markdown")

@dp.message(F.text == "Настройки")
async def settings_menu(message: types.Message):
    uid = message.from_user.id
    if not await check_sub(uid):
        await message.answer("⚠️ Сначала подпишитесь на канал!", reply_markup=get_sub_keyboard())
        return
        
    current_mode = users_db.get(uid, {}).get("mode", "fast")
    mode_label = "⚡ Быстрый (DeepSeek Chat)" if current_mode == "fast" else "🧠 Глубокий (DeepSeek R1)"

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Быстрый режим", callback_data="mode_fast")],
        [InlineKeyboardButton(text="🧠 Глубокий режим", callback_data="mode_deep")]
    ])
    await message.answer(f"⚙️ **Настройки**\nТекущий режим: **{mode_label}**", reply_markup=inline_kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("mode_"))
async def set_mode(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if uid not in users_db:
        users_db[uid] = {"mode": "fast", "history": []}

    if callback.data == "mode_fast":
        users_db[uid]["mode"] = "fast"
        await callback.message.edit_text("✅ Включён **Быстрый режим**.")
    else:
        users_db[uid]["mode"] = "deep"
        await callback.message.edit_text("✅ Включён **Глубокий режим**.")

@dp.message()
async def process_ai_request(message: types.Message):
    if message.text in ["💬 Новый вопрос", "Сбросить историю", "Инструкция", "Настройки", "🎨 Создать картинку"]:
        return

    uid = message.from_user.id

    if not await check_sub(uid):
        await message.answer(
            f"⚠️ **Для использования бота необходимо подписаться на канал!**\n{CHANNEL_URL}",
            reply_markup=get_sub_keyboard()
        )
        return

    if uid not in users_db:
        users_db[uid] = {"mode": "fast", "history": []}

    user_data = users_db[uid]

    if user_data.get("mode") == "image_wait":
        prompt_text = message.text
        user_data["mode"] = "fast"
        
        status_msg = await message.answer("🎨 Генерирую изображение...")
        
        translated_prompt = prompt_text
        try:
            async with ClientSession() as session:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "deepseek/deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "Translate to English for image generation. Return ONLY translated text."},
                        {"role": "user", "content": prompt_text}
                    ]
                }
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        tr_data = await resp.json()
                        translated_prompt = tr_data["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

        seed = random.randint(1, 999999)
        encoded_prompt = urllib.parse.quote(translated_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=flux&seed={seed}&nologo=true"
        
        try:
            await message.answer_photo(
                photo=image_url, 
                caption=f"🖼 **Запрос:** {prompt_text}", 
                parse_mode="Markdown",
                reply_markup=main_keyboard
            )
            await status_msg.delete()
        except Exception as err:
            await status_msg.edit_text(f"❌ Ошибка генерации картинки: {err}")
        return

    selected_model = "deepseek/deepseek-chat" if user_data["mode"] == "fast" else "deepseek/deepseek-r1"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_data["history"]
    messages.append({"role": "user", "content": message.text})

    status_msg = await message.answer("⏳ ИИ думает...")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": selected_model,
        "messages": messages,
        "max_tokens": 1000
    }

    try:
        async with ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                
                if resp.status != 200:
                    err_msg = data.get("error", {}).get("message", "Неизвестная ошибка")
                    await status_msg.edit_text(f"❌ Ошибка {resp.status}: {err_msg}")
                    return

                answer_text = data["choices"][0]["message"]["content"]
                
                user_data["history"].append({"role": "user", "content": message.text})
                user_data["history"].append({"role": "assistant", "content": answer_text})

                await status_msg.edit_text(answer_text)
    except Exception as err:
        await status_msg.edit_text(f"❌ Ошибка соединения: {err}")

async def handle_ping(request):
    return web.Response(text="Bot active")

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
