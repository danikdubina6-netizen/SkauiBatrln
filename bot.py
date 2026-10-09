import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# Твой токен бота
TOKEN = "8762582086:AAHSujA_gAP3kUnlOCGMcf3gv9puRbqm3vo"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Функция для скачивания видео/аудио
def download_media(url: str, mode: str = "video") -> str:
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
    }
    
    if mode == "audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
        })

    os.makedirs('downloads', exist_ok=True)
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if mode == "audio":
            # Исправляем расширение после конвертации в mp3
            base, _ = os.path.splitext(filename)
            filename = base + ".mp3"
        return filename

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Йоу! ✌️ Кинь мне ссылку на видео из **YouTube**, **TikTok** или **Instagram**, "
        "а я предложу скачать его в видео или вырезать аудио (MP3)."
    )

@dp.message(F.text.startswith("http"))
async def handle_url(message: types.Message):
    url = message.text.strip()
    
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
    
    await callback.message.edit_text("⏳ Качаю, секунду...")
    
    try:
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(None, download_media, url, mode)
        
        await callback.message.edit_text("📤 Загружаю файл в Telegram...")
        
        file = FSInputFile(file_path)
        if mode == "video":
            await callback.message.answer_video(file)
        else:
            await callback.message.answer_audio(file)
            
        # Удаляем файл после отправки
        os.remove(file_path)
        await callback.message.delete()
        
    except Exception as e:
        logging.error(f"Error: {e}")
        await callback.message.edit_text("❌ Ошибка при скачивании: с ссылкой что-то не так или платформа блокирует запрос.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
