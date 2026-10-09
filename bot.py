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
        # Настройки эмуляции мобильного клиента для обхода блокировок IP GitHub
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'mweb', 'android'],
            }
        },
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
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
        "Йоу! ✌️ Бот готов к работе. "
        "Кидай ссылку на **YouTube**, **TikTok** или **Instagram**!"
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
    
    await callback.message.edit_text("⏳ Качаю с обходом защиты, секунду...")
    
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
        await callback.message.edit_text(f"❌ Ошибка скачивания: платформа отклонила запрос с облачного сервера.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
