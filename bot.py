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
        "Йоу! ✌️ Бот переведен на быстрое API. "
        "Кидай ссылку на **YouTube**, **TikTok** или **Instagram**!"
    )

@dp.message(F.text.startswith("http"))
async def handle_url(message: types.Message):
    url = message.text.strip()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎥 Скачать видео", callback_data=f"get|{url}")
        ]
    ])
    
    await message.answer("Жми кнопку, чтобы забрать видос без ошибок облака:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("get|"))
async def process_download(callback: types.CallbackQuery):
    _, url = callback.data.split("|", 1)
    await callback.message.edit_text("⏳ Получаю прямую ссылку через API...")
    
    try:
        # Используем публичный открытый сервис-агрегатор для скачивания
        api_url = f"https://tikwm.com/api/?url={url}" # Универсальный шлюз
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                data = await resp.json()
                
                if data.get("code") == 0 and "data" in data:
                    video_url = data["data"].get("play") or data["data"].get("url")
                    
                    if video_url:
                        await callback.message.edit_text("📤 Скачиваю и отправляю в телегу...")
                        
                        # Скачиваем файл во временную зону
                        file_path = "downloads/temp_video.mp4"
                        os.makedirs("downloads", exist_ok=True)
                        
                        async with session.get(video_url) as vid_resp:
                            with open(file_path, "wb") as f:
                                f.write(await vid_resp.read())
                                
                        file = FSInputFile(file_path)
                        await callback.message.answer_video(file)
                        
                        os.remove(file_path)
                        await callback.message.delete()
                        return

        # Если универсальный метод не сработал для ютуба, шлем запасной вариант через cobalt.tools API (одно из лучших открытых API)
        cobalt_api = "https://api.cobalt.tools/api/json"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        payload = {"url": url}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(cobalt_api, json=payload, headers=headers) as resp:
                res = await resp.json()
                if "url" in res:
                    await callback.message.edit_text("📤 Загружаю с Cobalt API...")
                    file_path = "downloads/cobalt_video.mp4"
                    os.makedirs("downloads", exist_ok=True)
                    
                    async with session.get(res["url"]) as vid_resp:
                        with open(file_path, "wb") as f:
                            f.write(await vid_resp.read())
                            
                    file = FSInputFile(file_path)
                    await callback.message.answer_video(file)
                    os.remove(file_path)
                    await callback.message.delete()
                    return

        await callback.message.edit_text("❌ Не удалось вытянуть медиа через API. Попробуй другую ссылку.")

    except Exception as e:
        logging.error(f"Error: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {str(e)[:100]}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
