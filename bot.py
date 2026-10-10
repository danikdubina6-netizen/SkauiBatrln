import os
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, MessageReactionUpdated
from database import (
    init_db, save_message, get_user_by_admin_msg,
    is_banned, ban_user, unban_user
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = "Topyak1"  # Куда будут доставляться все анонимные сообщения

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Переменная для хранения ID администратора (определится автоматически при первом сообщении)
ADMIN_ID = None

@dp.message(CommandStart())
async def start_handler(message: Message):
    if await is_banned(message.from_user.id):
        return
    
    welcome_text = (
        "<b>👋 Добро пожаловать в анонимный чат!</b>\n\n"
        "💬 <i>Здесь вы можете отправить любое сообщение, фото, видео или аудио, и оно будет доставлено получателю (@Topyak1) полностью анонимно.</i>\n\n"
        "✨ Просто напишите ваш текст или отправьте файл следующим сообщением!"
    )
    await message.answer(welcome_text, parse_mode="HTML")

@dp.message(Command("ban"))
async def ban_handler(message: Message):
    if message.from_user.username != ADMIN_USERNAME:
        return
        
    if not message.reply_to_message:
        await message.answer("Сделайте reply (ответ) на сообщение пользователя с командой /ban.")
        return
    
    user_id = await get_user_by_admin_msg(message.reply_to_message.message_id)
    if user_id:
        await ban_user(user_id)
        await message.answer(f"Пользователь {user_id} заблокирован.")
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

# Сообщения от пользователя -> админу (@Topyak1)
@dp.message()
async def main_message_handler(message: Message):
    global ADMIN_ID
    
    # Если пишет сам администратор по юзернейму
    if message.from_user.username == ADMIN_USERNAME:
        ADMIN_ID = message.chat.id
        
        if not message.reply_to_message:
            await message.answer("Сделайте reply на сообщение, чтобы ответить пользователю.")
            return

        user_id = await get_user_by_admin_msg(message.reply_to_message.message_id)
        if not user_id:
            await message.answer("Не удалось найти адресата.")
            return

        await bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
        await asyncio.sleep(1)

        await message.copy_to(chat_id=user_id)
        return

    # Сообщение от обычного пользователя
    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.answer("Вы заблокированы.")
        return

    # Если мы еще не знаем ID админа, пробуем отправить по юзернейму
    target_chat = ADMIN_ID if ADMIN_ID else f"@{ADMIN_USERNAME}"

    await bot.send_chat_action(chat_id=target_chat, action=ChatAction.TYPING)
    await asyncio.sleep(1)

    forwarded = await message.copy_to(chat_id=target_chat)
    
    # Сохраняем привязку для ответа
    await save_message(admin_msg_id=forwarded.message_id, user_id=user_id)

async def main():
    await init_db()
    await dp.start_polling(bot, allowed_updates=["message", "message_reaction"])

if __name__ == "__main__":
    asyncio.run(main())
    
