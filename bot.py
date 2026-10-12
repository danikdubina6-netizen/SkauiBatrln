import asyncio
import json
import os
import logging
import base64
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import ChatMemberUpdatedFilter, MEMBER, KICKED, LEFT
from aiogram.types import BotCommand, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

TOKEN = "8850468671:AAEJ31dG-_4JOmg3IOC9e_T3IdtVarLftnY"

bot = Bot(token=TOKEN)
dp = Dispatcher()

MODS_FILE = "mods.json"
SETTINGS_FILE = "settings.json"

REPO_OWNER = "danikdubina6-netizen"
REPO_NAME = "Topyak_bot2026"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

# Словарь для отслеживания прошедших верификацию: {chat_id: {user_id: True}}
verified_users = {}


def load_data(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(chat_id): {int(uid) if str(uid).isdigit() else uid: val for uid, val in items.items()} for chat_id, items in data.items()}
        except Exception:
            return {}
    return {}


group_moderators = load_data(MODS_FILE)


def load_antispam_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(chat_id): val for chat_id, val in data.items()}
        except Exception:
            return {}
    return {}


antispam_settings = load_antispam_settings()


async def push_file_to_github(filename):
    if not GITHUB_TOKEN:
        logging.warning("GitHub токен не найден, авто-коммит пропущен.")
        return

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filename}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    async with aiohttp.ClientSession() as session:
        sha = None
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                file_info = await resp.json()
                sha = file_info.get("sha")

        with open(filename, "r", encoding="utf-8") as f:
            content_str = f.read()
        
        content_encoded = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

        payload = {
            "message": f"Auto-update {filename} via bot command",
            "content": content_encoded,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        async with session.put(url, headers=headers, json=payload) as resp:
            if resp.status in (200, 201):
                logging.info(f"Файл {filename} успешно закоммичен на GitHub!")
            else:
                text = await resp.text()
                logging.error(f"Не удалось запушить {filename} в GitHub: {text}")


async def save_and_sync_moderators():
    try:
        with open(MODS_FILE, "w", encoding="utf-8") as f:
            json.dump(group_moderators, f, ensure_ascii=False, indent=4)
        await push_file_to_github(MODS_FILE)
    except Exception as e:
        logging.error(f"Ошибка сохранения модераторов: {e}")


async def save_and_sync_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(antispam_settings, f, ensure_ascii=False, indent=4)
        await push_file_to_github(SETTINGS_FILE)
    except Exception as e:
        logging.error(f"Ошибка сохранения настроек: {e}")


async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="ban", description="Забанить пользователя (в ответ)"),
        BotCommand(command="unban", description="Разбанить пользователя (в ответ)"),
        BotCommand(command="mute", description="Замутить пользователя (в ответ)"),
        BotCommand(command="unmute", description="Размутить пользователя (в ответ)"),
        BotCommand(command="cleandeleted", description="Очистить удаленные аккаунты"),
        BotCommand(command="rules", description="Показать правила из описания"),
        BotCommand(command="addmod", description="Добавить модератора (в ответ)"),
        BotCommand(command="delmod", description="Убрать модератора (в ответ)"),
        BotCommand(command="mods", description="Список модераторов бота"),
        BotCommand(command="antispam", description="Управление защитой от накрутки"),
    ]
    await bot.set_my_commands(main_menu_commands)


async def is_owner(message: types.Message) -> bool:
    if message.chat.type == "private":
        return True
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status == "creator"
    except Exception:
        return False


async def can_manage(message: types.Message) -> bool:
    if await is_owner(message):
        return True
    chat_mods = group_moderators.get(message.chat.id, {})
    if message.from_user.id in chat_mods:
        return True
    return False


# 1. КОМАНДА И ТЕКСТОВЫЙ ТРИГГЕР ДЛЯ ОЧИСТКИ УДАЛЕННЫХ АККАУНТОВ
@dp.message(F.text.lower().regexp(r"^(/cleandeleted(@[a-zA-Z0-9_]+)?|очистить удаленных аккаунтов|очистить удаленных)"))
async def clean_deleted_accounts(message: types.Message):
    if message.chat.type == "private":
        await message.answer("ℹ️ Эту команду или фразу нужно использовать в группе!")
        return

    if not await can_manage(message):
        await message.reply("⛔ Только владелец или модераторы могут запускать очистку чата!")
        return

    status_msg = await message.answer("🧹 Проверяю список администраторов и активных участников на «собачек»...")
    
    chat_id = message.chat.id
    removed_count = 0

    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            user = admin.user
            if user.first_name == "Deleted Account" or getattr(user, 'is_deleted', False):
                try:
                    await bot.ban_chat_member(chat_id, user.id)
                    await bot.unban_chat_member(chat_id, user.id)
                    removed_count += 1
                except Exception:
                    pass

        if removed_count > 0:
            await status_msg.edit_text(f"✅ Очистка завершена! Удалено аккаунтов: **{removed_count}**", parse_mode="Markdown")
        else:
            await status_msg.edit_text("✅ Очистка завершена! Удаленных аккаунтов среди видимых пользователей не найдено.\n\n🛡 Включен авто-бан: если удаленный аккаунт напишет сообщение, бот сразу забанит его!")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка при сканировании: {e}")


# 2. АВТО-БАН УДАЛЕННЫХ АККАУНТОВ ПРИ ЛЮБОЙ АКТИВНОСТИ В ЧАТЕ
@dp.message(F.from_user.first_name == "Deleted Account")
async def auto_ban_deleted_users(message: types.Message):
    user = message.from_user
    if not user or message.chat.type == "private":
        return

    try:
        await message.delete()
        await bot.ban_chat_member(message.chat.id, user.id)
        await message.answer(f"🗑 Удаленный аккаунт (ID: `{user.id}`) забанен и очищен из чата.", parse_mode="Markdown")
    except Exception:
        pass


# ЛОВИМ РУЧНЫЕ УДАЛЕНИЯ И ВХОДЫ
@dp.chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED | LEFT | MEMBER))
async def track_chat_member_updates(event: types.ChatMemberUpdated):
    chat_id = event.chat.id
    user = event.new_chat_member.user
    new_status = event.new_chat_member.status
    old_status = event.old_chat_member.status
    actor = event.from_user

    if new_status in ("kicked", "left") and old_status not in ("kicked", "left"):
        if actor and actor.id == (await bot.get_me()).id:
            return

        target_name = user.full_name
        target_mention = f"@{user.username}" if user.username else f"ID: `{user.id}`"
        target_str = f"{target_name} ({target_mention})"

        if actor and actor.id != user.id:
            actor_name = actor.full_name
            actor_mention = f"@{actor.username}" if actor.username else f"ID: `{actor.id}`"
            actor_str = f"{actor_name} ({actor_mention})"
            await bot.send_message(chat_id, f"🗑 Админ {actor_str} удалил {target_str}.", parse_mode="Markdown")
        else:
            if new_status == "kicked":
                await bot.send_message(chat_id, f"🗑 Пользователь {target_str} был удален из чата.", parse_mode="Markdown")
        return

    if new_status == "member" and old_status in ("left", "kicked", "restricted"):
        if user.is_bot or not antispam_settings.get(chat_id, True):
            return

        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
        except Exception:
            pass

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Я не бот (Нажми меня)", callback_data=f"verify_{user.id}")]
        ])

        msg = await bot.send_message(
            chat_id,
            f"Привет, {user.full_name}!\n\n🤖 В этом чате работает защита от накрутки. Подтверди, что ты человек, нажав кнопку ниже в течение **3 минут**, иначе система тебя исключит.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

        async def check_verification():
            await asyncio.sleep(180)
            try:
                if chat_id in verified_users and user.id in verified_users[chat_id]:
                    return  
                
                member = await bot.get_chat_member(chat_id, user.id)
                if member.status in ("restricted", "member"):
                    await bot.ban_chat_member(chat_id, user.id)
                    await bot.unban_chat_member(chat_id, user.id)
                    await msg.edit_text(f"❌ Пользователь {user.full_name} не прошел верификацию и был исключен.")
            except Exception:
                pass

        asyncio.create_task(check_verification())


# Команда /antispam
@dp.message(F.text.lower().regexp(r"^(/antispam(@[a-zA-Z0-9_]+)?|антиспам)"))
async def toggle_antispam(message: types.Message):
    chat_id = message.chat.id
    args = message.text.split()

    if len(args) < 2:
        current_status = antispam_settings.get(chat_id, True)
        status_text = "🟢 Включена" if current_status else "🔴 Выключена"
        
        help_text = (
            f"🛡 **Управление защитой от накрутки (антиспам)**\n\n"
            f"Текущий статус в этом чате: {status_text}\n\n"
            f"📋 **Инструкция по настройке:**\n"
            f"• Защита проверяет новых участников с помощью кнопки и таймера на 3 минуты, защищая чат от ботов.\n"
            f"• Чтобы **включить** защиту, отправьте:\n`/antispam on`\n"
            f"• Чтобы **выключить** защиту (убрать проверки), отправьте:\n`/antispam off`"
        )
        await message.answer(help_text, parse_mode="Markdown")
        return

    if not await can_manage(message):
        await message.reply("⛔ Только владелец или модераторы могут менять настройки защиты!")
        return

    mode = args[1].lower()
    if mode in ("on", "вкл", "1", "true"):
        antispam_settings[chat_id] = True
        await save_and_sync_settings()
        await message.answer("✅ Защита от накрутки успешно **включена** для этого чата!", parse_mode="Markdown")
    elif mode in ("off", "выкл", "0", "false"):
        antispam_settings[chat_id] = False
        await save_and_sync_settings()
        await message.answer("⚠️ Защита от накрутки **выключена**. Жесткие проверки больше не действуют.", parse_mode="Markdown")
    else:
        await message.answer("❌ Неверный параметр! Используйте:\n`/antispam on` — включить\n`/antispam off` — выключить", parse_mode="Markdown")


@dp.callback_query(F.data.startswith("verify_"))
async def verify_callback(callback: types.CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    
    if callback.from_user.id != target_user_id:
        await callback.answer("⛔ Эта кнопка не для тебя!", show_alert=True)
        return

    chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    if chat_id not in verified_users:
        verified_users[chat_id] = {}
    verified_users[chat_id][user_id] = True

    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_add_web_page_previews=True
            )
        )
        await callback.message.delete()
        await callback.answer("✅ Верификация пройдена! Добро пожаловать.", show_alert=True)
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


# ДОБАВИТЬ МОДЕРАТОРА
@dp.message(F.text.lower().regexp(r"^(/addmod(@[a-zA-Z0-9_]+)?|добавить модератора)"))
async def add_moderator(message: types.Message):
    if not await is_owner(message):
        await message.reply("⛔ Только владелец группы может назначать модераторов!")
        return

    if not message.reply_to_message:
        await message.reply("❌ Сделай реплай на сообщение пользователя!", parse_mode="Markdown")
        return

    target_user = message.reply_to_message.from_user
    chat_id = message.chat.id

    if chat_id not in group_moderators:
        group_moderators[chat_id] = {}

    group_moderators[chat_id][target_user.id] = target_user.full_name
    await save_and_sync_moderators()
    await message.answer(f"✅ Пользователь {target_user.full_name} назначен модератором и сохранен!")


# УБРАТЬ МОДЕРАТОРА
@dp.message(F.text.lower().regexp(r"^(/delmod(@[a-zA-Z0-9_]+)?|убрать модератора)"))
async def remove_moderator(message: types.Message):
    if not await is_owner(message):
        await message.reply("⛔ Только владелец группы может снимать модераторов!")
        return

    if not message.reply_to_message:
        await message.reply("❌ Сделай реплай на сообщение модератора!", parse_mode="Markdown")
        return

    target_user = message.reply_to_message.from_user
    chat_id = message.chat.id

    chat_mods = group_moderators.get(chat_id, {})
    if target_user.id in chat_mods:
        del chat_mods[target_user.id]
        await save_and_sync_moderators()
        await message.answer(f"🗑 Пользователь {target_user.full_name} снят с поста модератора.")
    else:
        await message.answer(f"⚠️ Пользователь не найден в модераторах этого чата.")


# СПИСОК МОДЕРАТОРОВ
@dp.message(F.text.lower().regexp(r"^(/mods(@[a-zA-Z0-9_]+)?|список администраторов|модераторы|админы)"))
async def list_moderators(message: types.Message):
    chat_id = message.chat.id
    chat_mods = group_moderators.get(chat_id, {})

    if not chat_mods:
        await message.answer("ℹ️ У этого бота пока нет модераторов в данном чате.")
        return
    
    text = "🛡 **Список модераторов этого чата:**\n\n"
    for idx, (uid, name) in enumerate(chat_mods.items(), 1):
        text += f"{idx}. {name} (ID: `{uid}`)\n"
        
    await message.answer(text, parse_mode="Markdown")


# ПРАВИЛА
@dp.message(F.text.lower().regexp(r"^(/rules(@[a-zA-Z0-9_]+)?|правила|каталог правил)"))
async def text_rules(message: types.Message):
    if message.chat.type == "private":
        await message.answer("ℹ️ Используй эту команду в группе!")
        return
        
    try:
        chat_info = await bot.get_chat(message.chat.id)
        if chat_info.description:
            await message.answer(f"📋 **Правила группы:**\n\n{chat_info.description}", parse_mode="Markdown")
        else:
            await message.answer("⚠️ У группы нет описания с правилами!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


# БАН
@dp.message(F.text.lower().regexp(r"^(/ban(@[a-zA-Z0-9_]+)?|бан)"))
async def text_ban(message: types.Message):
    if not await can_manage(message):
        await message.reply("⛔ Нет прав!")
        return

    if not message.reply_to_message:
        await message.reply("❌ Сделай реплай на сообщение нарушителя!")
        return

    target_user = message.reply_to_message.from_user
    args = message.text.split()
    until_date = None
    time_text = "навсегда"

    if len(args) >= 2:
        try:
            for i, arg in enumerate(args):
                if arg.isdigit():
                    amount = int(arg)
                    unit = args[i+1].lower() if i+1 < len(args) else "мин"
                    
                    if "час" in unit or "ч" in unit:
                        duration_minutes = amount * 60
                        time_text = f"на {amount} час(а)" if amount < 5 else f"на {amount} часов"
                    elif "д" in unit:
                        duration_minutes = amount * 24 * 60
                        time_text = f"на {amount} день/дней"
                    else:
                        duration_minutes = amount
                        time_text = f"на {amount} минут(ы)"
                    
                    until_date = datetime.now() + timedelta(minutes=duration_minutes)
                    break
        except Exception:
            pass

    try:
        if until_date:
            await bot.ban_chat_member(chat_id=message.chat.id, user_id=target_user.id, until_date=until_date)
        else:
            await bot.ban_chat_member(chat_id=message.chat.id, user_id=target_user.id)
            
        await message.answer(f"Пользователь {target_user.full_name} забанен {time_text}.")
    except Exception as e:
        await message.answer(f"Ошибка бана: {e}")


# РАЗБАН
@dp.message(F.text.lower().regexp(r"^(/unban(@[a-zA-Z0-9_]+)?|разбан)"))
async def text_unban(message: types.Message):
    if not await can_manage(message):
        await message.reply("⛔ Нет прав!")
        return
    
    if not message.reply_to_message:
        await message.reply("❌ Сделай реплай!")
        return
    
    target_user = message.reply_to_message.from_user
    try:
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=target_user.id)
        await message.answer(f"Пользователь {target_user.full_name} разбанен.")
    except Exception as e:
        await message.answer(f"Ошибка разбана: {e}")


# МУТ
@dp.message(F.text.lower().regexp(r"^(/mute(@[a-zA-Z0-9_]+)?|мут)"))
async def text_mute(message: types.Message):
    if not await can_manage(message):
        await message.reply("⛔ Нет прав!")
        return

    if not message.reply_to_message:
        await message.reply("❌ Сделай реплай!")
        return
    
    target_user = message.reply_to_message.from_user
    args = message.text.split()
    until_date = None
    time_text = "навсегда"

    if len(args) >= 2:
        try:
            for i, arg in enumerate(args):
                if arg.isdigit():
                    amount = int(arg)
                    unit = args[i+1].lower() if i+1 < len(args) else "мин"
                    
                    if "час" in unit or "ч" in unit:
                        duration_minutes = amount * 60
                        time_text = f"на {amount} час(а)" if amount < 5 else f"на {amount} часов"
                    elif "д" in unit:
                        duration_minutes = amount * 24 * 60
                        time_text = f"на {amount} день/дней"
                    else:
                        duration_minutes = amount
                        time_text = f"на {amount} минут(ы)"
                        
                    until_date = datetime.now() + timedelta(minutes=duration_minutes)
                    break
        except Exception:
            pass

    try:
        await message.chat.restrict(
            user_id=target_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        await message.answer(f"Пользователь {target_user.full_name} замучен {time_text}.")
    except Exception as e:
        await message.answer(f"Ошибка мута: {e}")


# РАЗМУТ
@dp.message(F.text.lower().regexp(r"^(/unmute(@[a-zA-Z0-9_]+)?|размут)"))
async def text_unmute(message: types.Message):
    if not await can_manage(message):
        await message.reply("⛔ Нет прав!")
        return

    if not message.reply_to_message:
        await message.reply("❌ Сделай реплай!")
        return

    target_user = message.reply_to_message.from_user
    try:
        await message.chat.restrict(
            user_id=target_user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_add_web_page_previews=True
            )
        )
        await message.answer(f"Пользователь {target_user.full_name} размучен.")
    except Exception as e:
        await message.answer(f"Ошибка размута: {e}")


async def main():
    await set_main_menu(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
