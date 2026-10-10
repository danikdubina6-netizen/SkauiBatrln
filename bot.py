import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import init_db, save_message, get_user_by_admin_msg, is_banned, ban_user, unban_user

# Читаем токен из переменных окружения (GitHub Secrets)
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ Ошибка: Переменная BOT_TOKEN не найдена в Secrets!")

ADMIN_ID = 7725909693  # Твой ID (@Topyak1)

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
    
    # Кнопка блокировки
    builder = InlineKeyboardBuilder()
    builder.button(text="🚫 Заблокировать контакт", callback_data=f"ban_{user_id}")
    
    info_msg = await bot.send_message(
        ADMIN_ID, 
        f"📩 <b>Новое анонимное сообщение для @Topyak1!</b>\n"
        f"👤 Отправитель ID: <code>{user_id}</code> ({username_info})\n"
        f"💡 <i>Ответь реплаем на сообщение ниже или нажми кнопку для блокировки.</i>",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    
    copied_msg = await message.copy_to(chat_id=ADMIN_ID)
    
    save_message(copied_msg.message_id, user_id)
    save_message(info_msg.message_id, user_id)

# Обработка кнопок банов/разбанов
@dp.callback_query(F.data.startswith(("ban_", "unban_")))
async def process_mod_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Эта кнопка не для вас!", show_alert=True)
        return

    action, user_id_str = callback.data.split("_")
    target_user_id = int(user_id_str)
    
    builder = InlineKeyboardBuilder()

    if action == "ban":
        ban_user(target_user_id)
        
        try:
            await bot.send_message(
                target_user_id, 
                "🚫 Топяк заблокировал вас, любое ваше сообщение — уйдут в пустоту."
            )
        except Exception:
            pass

        builder.button(text="🔓 Разблокировать контакт", callback_data=f"unban_{target_user_id}")
        
        base_text = callback.message.html_text.split("\n\n❌")[0].split("\n\n🔓")[0]
        await callback.message.edit_text(
            f"{base_text}\n\n❌ <b>СТАТУС: Контакт заблокирован!</b>",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        await callback.answer("🚫 Пользователь заблокирован!", show_alert=True)

    elif action == "unban":
        unban_user(target_user_id)
        
        try:
            await bot.send_message(
                target_user_id, 
                "🔓 Топяк вас официально разблокировал, можете ему снова писать — сообщение реально придет к нему"
            )
        except Exception:
            pass

        builder.button(text="🚫 Заблокировать контакт", callback_data=f"ban_{target_user_id}")
        
        base_text = callback.message.html_text.split("\n\n❌")[0].split("\n\n🔓")[0]
        await callback.message.edit_text(
            f"{base_text}\n\n🔓 <b>СТАТУС: Контакт разблокирован!</b>",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        await callback.answer("🔓 Пользователь разблокирован!", show_alert=True)

# Ответ администратора (@Topyak1) пользователю через Reply
@dp.message(F.from_user.id == ADMIN_ID, F.reply_to_message)
async def handle_admin_reply(message: types.Message):
    target_user_id = get_user_by_admin_msg(message.reply_to_message.message_id)
    
    if not target_user_id:
        return

    if is_banned(target_user_id):
        await message.answer("❌ Этот пользователь заблокирован. Сначала разблокируйте его кнопкой.")
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
    
