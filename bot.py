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
# Вкажи тут свій Telegram ID (ID адміна)
ADMIN_ID = 123456789 

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: Message):
    if await is_banned(message.from_user.id):
        return
    await message.answer("Привіт! Надішли мені будь-яке повідомлення, і я анонімно передам його.")

# Блокування користувача (команда /ban у відповідь на повідомлення)
@dp.message(Command("ban"), F.chat.id == ADMIN_ID)
async def ban_handler(message: Message):
    if not message.reply_to_message:
        await message.answer("Дай відповідь на повідомлення користувача з командою /ban.")
        return
    
    user_id = await get_user_by_admin_msg(message.reply_to_message.message_id)
    if user_id:
        await ban_user(user_id)
        await message.answer(f"Користувача {user_id} заблоковано.")
    else:
        await message.answer("Не вдалося знайти користувача для цього повідомлення.")

# Розблокування (команда /unban ID)
@dp.message(Command("unban"), F.chat.id == ADMIN_ID)
async def unban_handler(message: Message):
    try:
        user_id = int(message.text.split()[1])
        await unban_user(user_id)
        await message.answer(f"Користувача {user_id} розблоковано.")
    except (IndexError, ValueError):
        await message.answer("Використання: /unban <USER_ID>")

# 1. ФУНКЦИЯ ДУБЛИРОВАНИЯ РЕАКЦИЙ
@dp.message_reaction()
async def reaction_handler(reaction: MessageReactionUpdated):
    # Если реакцию поставил админ в чате админа
    if reaction.chat.id == ADMIN_ID:
        user_id = await get_user_by_admin_msg(reaction.message_id)
        if user_id:
            try:
                # Передаем список реакций (new_reaction) пользователю
                await bot.set_message_reaction(
                    chat_id=user_id,
                    message_id=reaction.message_id, # Если нужно привязать к конкретному ID, иначе отправляется реакция
                    reaction=reaction.new_reaction
                )
            except Exception as e:
                print(f"Помилка відправки реакції користувачу: {e}")

# 2. Пересылка сообщений от ПОЛЬЗОВАТЕЛЯ -> АДМИНУ (со статусом "печатает...")
@dp.message(F.chat.id != ADMIN_ID)
async def user_message_handler(message: Message):
    if await is_banned(message.from_user.id):
        return

    # Имитация "печатает..." перед отправкой админу
    await bot.send_chat_action(chat_id=ADMIN_ID, action=ChatAction.TYPING)
    await asyncio.sleep(1) # Небольшая пауза для естественности

    forwarded = await message.copy_to(chat_id=ADMIN_ID)
    await save_message(admin_msg_id=forwarded.message_id, user_id=message.from_user.id)

# 3. Пересылка ответов от АДМИНА -> ПОЛЬЗОВАТЕЛЮ (со статусом "печатает...")
@dp.message(F.chat.id == ADMIN_ID)
async def admin_message_handler(message: Message):
    if not message.reply_to_message:
        await message.answer("Зроби reply (відповідь) на повідомлення, щоб відповісти користувачу.")
        return

    user_id = await get_user_by_admin_msg(message.reply_to_message.message_id)
    if not user_id:
        await message.answer("Не вдалося знайти адресата.")
        return

    # Имитация "печатает..." перед отправкой пользователю
    await bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
    await asyncio.sleep(1)

    await message.copy_to(chat_id=user_id)

async def main():
    await init_db()
    # Разрешаем обработку событий реакций (message_reaction)
    await dp.start_polling(bot, allowed_updates=["message", "message_reaction"])

if __name__ == "__main__":
    asyncio.run(main())
    
