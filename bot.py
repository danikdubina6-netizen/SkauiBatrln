import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8762582086:AAHSujA_gAP3kUnlOCGMcf3gv9puRbqm3vo"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Йоу! ✌️ Бот для TikTok и Instagram через API на связи.\n"
        "Кидай ссылку — заберем в видео или аудио!"
    )

@dp.message(F.text.startswith("http"))
async def handle_url(message: types.Message):
    url = message.text.strip()
    
    if "youtube.com" in url or "youtu.be" in url:
        await message.answer("❌ Ютуб отключен. Используй только TikTok или Instagram!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎥 Видео", callback_data=f"vid|{url}"),
            InlineKeyboardButton(text="🎵 Аудио (MP3)", callback_data=f"aud|{url}")
        ]
    ])
    
    await message.answer("В каком формате забрать контент?", reply_markup=keyboard)

@dp.callback_query(F.data.startswith(("vid|", "aud|")))
async def process_download(callback: types.CallbackQuery):
    action, url = callback.data.split("|", 1)
    mode = "video" if action == "vid" else "audio"
    
    await callback.message.edit_text("⏳ Запрашиваю файл через шлюз...")
    
    try:
        # Используем мощный публичный API шлюз cobalt.tools для обхода блокировок
        cobalt_api = "https://api.cobalt.tools/api/json"
        headers = {
            "Accept": "application/json", 
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        
        # Если нужно аудио, просим кобальт выдать аудио напрямую, если нет — видео
        payload = {
            "url": url,
            "downloadMode": "audio" if mode == "audio" else "auto"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(cobalt_api, json=payload, headers=headers) as resp:
                res = await resp.json()
                
                download_url = res.get("url") or res.get("picker", [{}])[0].get("url")
                
                if not download_url:
                    await callback.message.edit_text("❌ Не удалось получить ссылку на файл. Попробуй другую.")
                    return
                
                await callback.message.edit_text("📤 Скачиваю и отправляю в Telegram...")
                
                ext = "mp3" if mode == "audio" else "mp4"
                file_path = f"downloads/media.{ext}"
                os.makedirs("downloads", exist_ok=True)
                
                async with session.get(download_url) as vid_resp:
                    with open(file_path, "wb") as f:
                        f.write(await vid_resp.read())
                        
                file = FSInputFile(file_path)
                if mode == "video":
                    await callback.message.answer_video(file)
                else:
                    await callback.message.answer_audio(file)
                    
                os.remove(file_path)
                await callback.message.delete()
                
    except Exception as e:
        logging.error(f"Error: {e}")
        await callback.message.edit_text("❌ Ошибка при обработке ссылки.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
