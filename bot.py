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
ADMIN_USERNAME = "Topyak1"

bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_ID = None

@dp.message(CommandStart())
async def start_handler(message: Message):
    if await is_banned(message.from_user.id):
        return
    
    welcome_text = (
        "<b>👋 Добро пожаловать в анонимный чат!</b>\n\n"
        "💬 <i>Здесь вы можете отправить любое сообщение, фото, видео или аудио, и получатель (@Topyak1) получит его анонимно (но у него будет кнопка для раскрытия личности, если захочет узнать автора).</i>\n\n"
        "✨ Просто напишите ваш текст или отправьте файл следующим сообщением!"
    )
    await message.answer(welcome_text, parse_mode="HTML")

@dp.message(Command("ban"))
async def ban_handler(message: Message):
    if message.from_user.username != ADMIN_USERNAME:
        return
        
    if not message.reply_to_message:
        await message.answer("Сделайте reply (ответ) на сообщение, чтобы заблокировать этого анонима.")
        return
    
    # Ищем юзера по обычному сообщению или по сообщению с кнопкой раскрытия
    target_msg_id = message.reply_to_message.message_id
    user_id = await get_user_by_admin_msg(target_msg_id)
    
    if user_id:
        await ban_user(user_id)
        await message.answer(f"🚷 Аноним (ID: {user_id}) успешно заблокирован.")
    else:
        await message.answer("Не удалось найти пользователя.")

@dp.message(Command("unban"))
async def unban_handler(message: Message):
    if message.from_user.username != ADMIN_USERNAME:
        return
        
    try:
        user_id = int(message.text.split()[1])
        await unban_user(user_id)
        await message.answer(f"Пользователь {user_id} разблокирован.")
    except (IndexError, ValueError):
        await message.answer("Использование: /unban <USER_ID>")

# Обработка нажатия на кнопку "Показать кто отправил"
@dp.callback_query(F.data.startswith("reveal_"))
async def reveal_callback(callback: CallbackQuery):
    if callback.from_user.username != ADMIN_USERNAME:
        await callback.answer("Эта кнопка только для администратора!", show_alert=True)
        return

    # Достаем ID пользователя из callback_data (например, reveal_123456789)
    user_id = int(callback.data.split("_")[1])
    
    # Пытаемся получить информацию о пользователе через бота
    try:
        chat = await bot.get_chat(user_id)
        username_str = f"@{chat.username}" if chat.username else "нет юзернейма"
        name_str = chat.first_name or "Без имени"
        
        info_text = f"👤 Отправитель:\nИмя: {name_str}\nЮзернейм: {username_str}\nID: {user_id}"
    except Exception:
        info_text = f"👤 Отправитель:\nID: {user_id} (не удалось получить профиль)"

    # Показываем всплывающее окошко с данными
    await callback.answer(info_text, show_alert=True)

# Дублирование реакций
@dp.message_reaction()
async def reaction_handler(reaction: MessageReactionUpdated):
    if ADMIN_ID and reaction.chat.id == ADMIN_ID:
        user_id = await get_user_by_admin_msg(reaction.message_id)
        if user_id:
            try:
                await bot.set_message_reaction(
                    chat_id=user_id,
                    message_id=reaction.message_id,
                    reaction=reaction.new_reaction
                )
            except Exception as e:
                print(f"Ошибка отправки реакции: {e}")

# Сообщения и пересылка
@dp.message()
async def main_message_handler(message: Message):
    global ADMIN_ID
    
    # Если пишет администратор
    if message.from_user.username == ADMIN_USERNAME:
        ADMIN_ID = message.chat.id
        
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

    # Сообщение от анонимного пользователя
    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.answer("Вы заблокированы в этом боте.")
        return

    target_chat = ADMIN_ID if ADMIN_ID else f"@{ADMIN_USERNAME}"

    await bot.send_chat_action(chat_id=target_chat, action=ChatAction.TYPING)
    await asyncio.sleep(1)

    # Копируем контент сообщения администратору
    forwarded = await message.copy_to(chat_id=target_chat)
    
    # Сохраняем связку в базу
    await save_message(admin_msg_id=forwarded.message_id, user_id=user_id)

    # Отправляем админу отдельную маленькую кнопку под этим сообщением
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" 👀 Показать кто отправил", callback_data=f"reveal_{user_id}")]
    ])
    
    # Отправляем кнопку ответом на пересланное сообщение, чтобы она была привязана
    await bot.send_message(
        chat_id=target_chat,
        text="👇 Кнопка управления анонимом:",
        reply_to_message_id=forwarded.message_id,
        reply_markup=keyboard
    )

async def main():
    await init_db()
    await dp.start_polling(bot, allowed_updates=["message", "message_reaction", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
    
