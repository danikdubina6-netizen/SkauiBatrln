import os
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, MessageReactionUpdated, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    init_db, save_message, get_user_by_admin_msg,
    is_banned, ban_user, unban_user, set_user_lang, get_user_lang
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 123456789  # Вкажи свій ID адміністратора

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Полные тексты с приветствием и инструкцией на трех языках
TEXTS = {
    "ru": {
        "start_prompt": "Выберите язык / Виберіть мову / Choose language:",
        "welcome": (
            "<b>👋 Добро пожаловать в анонимный чат!</b>\n\n"
            "💬 <i>Здесь вы можете отправить любое сообщение, фото, видео или аудио, и оно будет доставлено получателю полностью анонимно.</i>\n\n"
            "✨ Просто напишите ваш текст следующим сообщением!"
        ),
        "banned": "Вы заблокированы.",
        "reply_hint": "Сделайте reply (ответ) на сообщение, чтобы ответить пользователю."
    },
    "uk": {
        "start_prompt": "Виберіть мову / Выберите язык / Choose language:",
        "welcome": (
            "<b>👋 Ласкаво просимо до анонімного чату!</b>\n\n"
            "💬 <i>Тут ви можете надіслати будь-яке повідомлення, фото, відео чи аудіо, і воно буде доставлене отримувачу повністю анонімно.</i>\n\n"
            "✨ Просто напишіть ваш текст наступним повідомленням!"
        ),
        "banned": "Ви заблоковані.",
        "reply_hint": "Зробіть reply (відповідь) на повідомлення, щоб відповісти користувачу."
    },
    "en": {
        "start_prompt": "Choose language / Выберите язык / Виберіть мову:",
        "welcome": (
            "<b>👋 Welcome to the anonymous chat!</b>\n\n"
            "💬 <i>Here you can send any message, photo, video or audio, and it will be delivered to the recipient completely anonymously.</i>\n\n"
            "✨ Just type your message below!"
        ),
        "banned": "You are blocked.",
        "reply_hint": "Reply to the message to answer the user."
    }
}

@dp.message(CommandStart())
async def start_handler(message: Message):
    if await is_banned(message.from_user.id):
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_uk"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
        ]
    ])
    
    await message.answer("Выберите язык / Виберіть мову / Choose language:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("lang_"))
async def language_callback(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    await set_user_lang(callback.from_user.id, lang)
    
    # Редактируем сообщение с кнопками на приветствие + инструкцию
    await callback.message.edit_text(TEXTS[lang]["welcome"], parse_mode="HTML")
    await callback.answer()

@dp.message(Command("ban"), F.chat.id == ADMIN_ID)
async def ban_handler(message: Message):
    if not message.reply_to_message:
        await message.answer("Дай ответ на сообщение пользователя с командой /ban.")
        return
    
    user_id = await get_user_by_admin_msg(message.reply_to_message.message_id)
    if user_id:
        await ban_user(user_id)
        await message.answer(f"Пользователь {user_id} заблокирован.")
    else:
        await message.answer("Не удалось найти пользователя.")

@dp.message(Command("unban"), F.chat.id == ADMIN_ID)
async def unban_handler(message: Message):
    try:
        user_id = int(message.text.split()[1])
        await unban_user(user_id)
        await message.answer(f"Пользователь {user_id} разблокирован.")
    except (IndexError, ValueError):
        await message.answer("Использование: /unban <USER_ID>")

# Дублирование реакций
@dp.message_reaction()
async def reaction_handler(reaction: MessageReactionUpdated):
    if reaction.chat.id == ADMIN_ID:
        user_id = await get_user_by_admin_msg(reaction.message_id)
        if user_id:
            try:
                await bot.set_message_reaction(
                    chat_id=user_id,
                    message_id=reaction.message_id,
                    reaction=reaction.new_reaction
                )
            except Exception as e:
                print(f"Помилка реакції: {e}")

# Сообщения от пользователя -> админу
@dp.message(F.chat.id != ADMIN_ID)
async def user_message_handler(message: Message):
    user_id = message.from_user.id
    if await is_banned(user_id):
        lang = await get_user_lang(user_id)
        await message.answer(TEXTS[lang]["banned"])
        return

    await bot.send_chat_action(chat_id=ADMIN_ID, action=ChatAction.TYPING)
    await asyncio.sleep(1)

    forwarded = await message.copy_to(chat_id=ADMIN_ID)
    await save_message(admin_msg_id=forwarded.message_id, user_id=user_id)

# Ответы от админа -> пользователю
@dp.message(F.chat.id == ADMIN_ID)
async def admin_message_handler(message: Message):
    if not message.reply_to_message:
        await message.answer("Сделайте reply на сообщение.")
        return

    user_id = await get_user_by_admin_msg(message.reply_to_message.message_id)
    if not user_id:
        await message.answer("Не удалось найти адресата.")
        return

    await bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
    await asyncio.sleep(1)

    await message.copy_to(chat_id=user_id)

async def main():
    await init_db()
    await dp.start_polling(bot, allowed_updates=["message", "message_reaction", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
    
