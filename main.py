# main.py
# Ustozlar boti — kirish nuqtasi.

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import keyboards as kb
import notion_service as ns
import scheduler as sch
from utils import CHIZIQ

from handlers import registration, davomat, dars_qoldirish, tatil, balansim, bugungi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def diagnostika(message: Message):
    """/tekshir — texnik holatni tekshirish."""
    kutish = await message.answer("⏳  Tekshirilmoqda...")
    matn = (
        f"<b>🔧  Diagnostika</b>\n"
        f"{CHIZIQ}\n"
        f"Admin huquqi: {'✅' if message.from_user.id == config.ADMIN_ID else '❌'}\n"
        f"{CHIZIQ}\n"
    )
    bazalar = {
        "Ustozlar": config.DB_USTOZLAR,
        "Guruhlar": config.DB_GURUHLAR,
        "Talabalar": config.DB_TALABALAR,
        "Yozilishlar": config.DB_YOZILISHLAR,
        "Davomat": config.DB_DAVOMAT,
        "Chegirmalar": config.DB_CHEGIRMALAR,
        "Oyliklar": config.DB_OYLIKLAR,
        "Darslar grafigi": config.DB_DARSLAR_GRAFIGI,
    }
    for nomi, db_id in bazalar.items():
        try:
            natija = await ns.query_all(db_id)
            matn += f"✅  {nomi} — {len(natija)} ta yozuv\n"
        except Exception as e:
            qisqa = str(e)[:80]
            matn += f"❌  {nomi} — {qisqa}\n"

    await kutish.edit_text(matn)


async def notanish_xabar(message: Message):
    """Menyudan tashqari yozilgan matnlar uchun."""
    await message.answer(
        "Quyidagi menyudan tanlang 👇",
        reply_markup=kb.asosiy_menyu(),
    )


async def main():
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(diagnostika, F.text == "/tekshir")

    dp.include_router(registration.router)
    dp.include_router(davomat.router)
    dp.include_router(dars_qoldirish.router)
    dp.include_router(tatil.router)
    dp.include_router(balansim.router)
    dp.include_router(bugungi.router)

    # Eng oxirida: hech qaysi handlerga tushmagan matnlar
    dp.message.register(notanish_xabar, F.text)

    scheduler = AsyncIOScheduler()
    sch.sozlash(scheduler, bot)
    scheduler.start()

    logger.info("Ustozlar boti ishga tushdi.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
