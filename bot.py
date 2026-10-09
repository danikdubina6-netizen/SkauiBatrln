import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from database import init_db, save_message, get_user_by_admin_msg, is_banned, ban_user

TOKEN = "8870589631:AAEWag-OdsFc9ebYCgclYIjKv1a7cKVhJCA"

# Твой реальный Telegram ID для аккаунта @Topyak1
ADMIN_ID = 7725909693

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if is_banned(message.from_user.id):
        return
    await message.answer(
        "🥷 **Добро пожаловать в анонимный чат!**\n\n"
        "Здесь ты можешь отправить сообщение, фото, видео, кружочек или голосовое — **администратор (@Topyak1) получит его полностью анонимно**.\n\n"
        "📌 **Как это работает:**\n"
        "• Просто кидай сюда любой контент.\n"
        "• Твой профиль останется скрытым.\n"
        "• Когда администратор ответит, ответ придет прямо сюда.\n\n"
        "Жду твоё сообщение! Погнали 👇",
        parse_mode="Markdown"
    )

# Команда бана: отправь в ответ на сообщение пользователя /ban
@dp.message(Command("ban"))
async def cmd_ban(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    if message.reply_to_message:
        target_user_id = get_user_by_admin_msg(message.reply_to_message.message_id)
        if target_user_id:
            ban_user(target_user_id)
            await message.answer(f"🚫 Пользователь с ID `{target_user_id}` заблокирован в боте.")
        else:
            await message.answer("❌ Не удалось найти автора этого сообщения в базе.")
    else:
        await message.answer("⚠️ Эту команду нужно отправлять «реплаем» (в ответ) на сообщение.")

# Прием сообщений от пользователей и пересылка администратору @Topyak1
@dp.message(F.from_user.id != ADMIN_ID)
async def handle_user_message(message: types.Message):
    user_id = message.from_user.id
    if is_banned(user_id):
        await message.answer("❌ Вы заблокированы в этом боте.")
        return

    # Реакция-подтверждение пользователю
    await message.react([types.ReactionTypeEmoji(emoji="👍")])
    
    username_info = f"@{message.from_user.username}" if message.from_user.username else "скрыт"
    
    # Шапка-уведомление для администратора (@Topyak1)
    await bot.send_message(
        ADMIN_ID, 
        f"📩 <b>Новое анонимное сообщение для @Topyak1!</b>\n"
        f"👤 Отправитель ID: <code>{user_id}</code> ({username_info})\n"
        f"💡 <i>Ответь реплаем (ответом) на сообщение ниже, чтобы ответить пользователю.</i>",
        parse_mode="HTML"
    )
    
    # Копируем контент пользователю (@Topyak1) в ЛС
    copied_msg = await message.copy_to(chat_id=ADMIN_ID)
    
    # Сохраняем связку для ответа
    save_message(copied_msg.message_id, user_id)

# Ответ администратора (@Topyak1) пользователю через Reply
@dp.message(F.from_user.id == ADMIN_ID, F.reply_to_message)
async def handle_admin_reply(message: types.Message):
    target_user_id = get_user_by_admin_msg(message.reply_to_message.message_id)
    
    if not target_user_id:
        return

    try:
        await message.copy_to(chat_id=target_user_id)
        await message.react([types.ReactionTypeEmoji(emoji="✍️")])
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить ответ пользователю: {e}")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
