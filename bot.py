import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

TOKEN = "8762582086:AAHSujA_gAP3kUnlOCGMcf3gv9puRbqm3vo"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

def download_media(url: str, mode: str = "video") -> str:
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'socket_timeout': 30,
        # Используем встроенный обход через эмуляцию клиентов и прокси-шлюзы yt-dlp
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web', 'mweb'],
            }
        },
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
            'format': 'best[ext=mp4]/best/bestvideo+bestaudio/best',
        })

    os.makedirs('downloads', exist_ok=True)
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if mode == "audio":
            base, _ = os.path.splitext(filename)
            filename = base + ".mp3"
        return filename

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Йоу! ✌️ Скачиватель на связи.\n"
        "Кидай ссылку на **YouTube**, **TikTok** или **Instagram** — заберем видео или сделаем MP3!"
    )

@dp.message(F.text.startswith("http"))
async def handle_url(message: types.Message):
    url = message.text.strip()
    
    # Вернули выбор формата: видео и аудио
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
    
    await callback.message.edit_text("⏳ Качаю контент...")
    
    try:
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(None, download_media, url, mode)
        
        await callback.message.edit_text("📤 Загружаю файл в Telegram...")
        
        file = FSInputFile(file_path)
        if mode == "video":
            await callback.message.answer_video(file)
        else:
            await callback.message.answer_audio(file)
            
        os.remove(file_path)
        await callback.message.delete()
        
    except Exception as e:
        logging.error(f"Error: {e}")
        await callback.message.edit_text(f"❌ Ошибка скачивания. Попробуй ссылку из TikTok или другую платформу.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
