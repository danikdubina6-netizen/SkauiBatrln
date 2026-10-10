import os
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, MessageReactionUpdated, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import (
    init_db, save_message, get_user_by_admin_msg,
    is_banned, ban_user, unban_user
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7725909693

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Бот запущен и работает! Ждем анонимные сообщения.")
        return

    if await is_banned(message.from_user.id):
        return
    
    welcome_text = (
        "<b>👋 Добро пожаловать в анонимный чат!</b>\n\n"
        "💬 <i>Здесь вы можете отправить любое сообщение, фото, видео или аудио, и получатель получит его полностью анонимно.</i>\n\n"
        "✨ Просто напишите ваш текст или отправьте файл следующим сообщением!"
    )
    await message.answer(welcome_text, parse_mode="HTML")

@dp.message(Command("ban"), F.from_user.id == ADMIN_ID)
async def ban_handler(message: Message):
    if not message.reply_to_message:
        await message.answer("Сделайте reply (ответ) на сообщение, чтобы заблокировать этого анонима.")
        return
    
    target_msg_id = message.reply_to_message.message_id
    user_id = await get_user_by_admin_msg(target_msg_id)
    
    if user_id:
        await ban_user(user_id)
        await message.answer(f"🚷 Аноним (ID: {user_id}) успешно заблокирован.")
    else:
        await message.answer("Не удалось найти пользователя.")

@dp.message(Command("unban"), F.from_user.id == ADMIN_ID)
async def unban_handler(message: Message):
    try:
        user_id = int(message.text.split()[1])
        await unban_user(user_id)
        await message.answer(f"Пользователь {user_id} разблокирован.")
    except (IndexError, ValueError):
        await message.answer("Использование: /unban <USER_ID>")

# Обработка нажатия на кнопку "Показать кто отправил"
@dp.callback_query(F.data.startswith("reveal_"))
async def reveal_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Эта кнопка только для администратора!", show_alert=True)
        return

    user_id = int(callback.data.split("_")[1])
    
    try:
        chat = await bot.get_chat(user_id)
        username_str = f"@{chat.username}" if chat.username else "нет юзернейма"
        name_str = chat.first_name or "Без имени"
        
        info_text = f"👤 Отправитель:\nИмя: {name_str}\nЮзернейм: {username_str}\nID: {user_id}"
    except Exception:
        info_text = f"👤 Отправитель:\nID: {user_id} (не удалось получить профиль)"

    await callback.answer(info_text, show_alert=True)

# Уведомление о реакциях
@dp.message_reaction()
async def reaction_handler(reaction: MessageReactionUpdated):
    if reaction.chat.id == ADMIN_ID:
        user_id = await get_user_by_admin_msg(reaction.message_id)
        if user_id:
            try:
                # Извлекаем эмодзи поставленной реакции (если они есть)
                new_reacts = reaction.new_reaction
                if new_reacts:
                    # Берем первый попавшийся эмодзи из списка новых реакций
                    emoji = getattr(new_reacts[0], "emoji", "👍")
                else:
                    emoji = "👍"
                
                await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"💬 Аноним оставил реакцию <b>{emoji}</b> на сообщение.",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления о реакции: {e}")

# Сообщения и пересылка
@dp.message()
async def main_message_handler(message: Message):
    if message.from_user.id == ADMIN_ID:
        if not message.reply_to_message:
            await message.answer("Сделайте reply на сообщение анонима, чтобы ответить ему.")
            return

        user_id = await get_user_by_admin_msg(message.reply_to_message.message_id)
        if not user_id:
            await message.answer("Не удалось найти адресата.")
            return

        await bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
        await asyncio.sleep(1)

        await message.copy_to(chat_id=user_id)
        return

    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.answer("Вы заблокированы в этом боте.")
        return

    await bot.send_chat_action(chat_id=ADMIN_ID, action=ChatAction.TYPING)
    await asyncio.sleep(1)

    # 1. Отправляем кнопку "Показать кто отправил" В НАЧАЛЕ (ПЕРЕД сообщением)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👀 Показать кто отправил", callback_data=f"reveal_{user_id}")]
    ])
    control_msg = await bot.send_message(
        chat_id=ADMIN_ID,
        text="👇 <b>Анонимное сообщение:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    # 2. Копируем само сообщение анонима ниже
    forwarded = await message.copy_to(chat_id=ADMIN_ID)
    
    # Сохраняем связку в базу
    await save_message(admin_msg_id=forwarded.message_id, user_id=user_id)
    await save_message(admin_msg_id=control_msg.message_id, user_id=user_id)

async def main():
    await init_db()
    await dp.start_polling(bot, allowed_updates=["message", "message_reaction", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
    
