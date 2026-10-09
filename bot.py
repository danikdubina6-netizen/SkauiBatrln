import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from database import init_db, save_bridge, get_original_sender, is_banned

TOKEN = "8870589631:AAEWag-OdsFc9ebYCgclYIjKv1a7cKVhJCA"
# ID человека, с которым держат связь через бота (или главный оператор / получатель)
RECEIVER_ID = 123456789  # ⚠️ ЗАМЕНИ НА СВОЙ TELEGRAM ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if is_banned(message.from_user.id):
        return
    await message.answer(
        "🌉 **Анонимный чат-мост запущен!**\n\n"
        "Отправь сюда любое сообщение, текст, фото или голосовое — "
        "оно будет передано собеседнику анонимно.\n"
        "Когда тебе ответят, сообщение придет прямо сюда!"
    )

# Обработка сообщений от пользователей к получателю
@dp.message(F.from_user.id != RECEIVER_ID)
async def handle_user_to_receiver(message: types.Message):
    user_id = message.from_user.id
    if is_banned(user_id):
        return

    await message.react([types.ReactionTypeEmoji(emoji="👍")])
    
    # Шапка для получателя
    username_info = f"@{message.from_user.username}" if message.from_user.username else "скрыт"
    info_msg = await bot.send_message(
        RECEIVER_ID,
        f"📩 <b>Анонимное сообщение от пользователя</b>\n"
        f"🆔 ID: <code>{user_id}</code> ({username_info})\n"
        f"💡 <i>Сделай реплай (ответ) на сообщение ниже, чтобы ответить ему.</i>",
        parse_mode="HTML"
    )
    
    # Копируем контент получателю
    copied = await message.copy_to(chat_id=RECEIVER_ID)
    
    # Сохраняем мост: если получатель ответит на `copied.message_id`, вернем сообщение `user_id`
    save_bridge(target_msg_id=copied.message_id, sender_id=user_id, recipient_id=RECEIVER_ID)

# Обратный ответ от получателя обратно пользователю через реплай
@dp.message(F.from_user.id == RECEIVER_ID, F.reply_to_message)
async def handle_receiver_reply(message: types.Message):
    original_sender_id = get_original_sender(
        target_msg_id=message.reply_to_message.message_id,
        recipient_id=RECEIVER_ID
    )
    
    if not original_sender_id:
        await message.answer("❌ Не удалось найти получателя для этого ответа в базе моста.")
        return

    try:
        copied_back = await message.copy_to(chat_id=original_sender_id)
        await message.react([types.ReactionTypeEmoji(emoji="✍️")])
        
        # Сохраняем обратный мост, чтобы пользователь мог ответить продолжением диалога
        save_bridge(target_msg_id=copied_back.message_id, sender_id=RECEIVER_ID, recipient_id=original_sender_id)
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

# Если получатель пишет без реплая
@dp.message(F.from_user.id == RECEIVER_ID)
async def receiver_chat_without_reply(message: types.Message):
    await message.answer("⚠️ Чтобы ответить пользователю, сделай **реплай (ответ)** на его пересланное сообщение!")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
