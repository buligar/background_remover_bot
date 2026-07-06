import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, Message
from dotenv import load_dotenv
from rembg import new_session, remove

BASE_DIR = Path(file).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Модель u2netp загружается один раз при старте и переиспользуется между запросами
session = new_session("u2netp")

SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Пришли мне фото (как фото или файлом), и я уберу с него фон "
        "с помощью модели u2netp."
    )


async def process_and_reply(message: Message, file_id: str) -> None:
    status_message = await message.answer("Обрабатываю фото, подожди немного...")

    try:
        file = await bot.get_file(file_id)
        file_bytes_io = await bot.download_file(file.file_path)
        input_bytes = file_bytes_io.read()

        output_bytes = await asyncio.to_thread(remove, input_bytes, session=session)

        result_file = BufferedInputFile(output_bytes, filename="no_background.png")
        await message.answer_document(result_file, caption="Готово! Фон удалён 🎉")
    except Exception:
        logging.exception("Ошибка при обработке изображения")
        await message.answer("Не получилось обработать фото. Попробуй ещё раз.")
    finally:
        await status_message.delete()


@dp.message(F.photo)
async def handle_photo(message: Message) -> None:
    largest_photo = message.photo[-1]
    await process_and_reply(message, largest_photo.file_id)


@dp.message(F.document)
async def handle_document(message: Message) -> None:
    document = message.document
    if document.mime_type not in SUPPORTED_MIME_TYPES:
        await message.answer("Пришли изображение в формате JPG, PNG или WEBP.")
        return
    await process_and_reply(message, document.file_id)


async def main() -> None:
    await dp.start_polling(bot)


if name == "main":
    asyncio.run(main())
