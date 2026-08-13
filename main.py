# main.py
# Ustozlar boti — kirish nuqtasi.

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import keyboards as kb
import notion_service as ns
import scheduler as sch

from handlers import registration, davomat, dars_qoldirish, tatil, balansim, bugungi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def diagnostika(message):
    """/tekshir — texnik holatni tekshirish."""
    matn = "🔧 Diagnostika\n\n"
    matn += f"Admin ID mos keladi: {'✅' if message.from_user.id == config.ADMIN_ID else '❌'}\n\n"
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
            await ns.query_all(db_id)
            matn += f"✅ {nomi}\n"
        except Exception as e:
            matn += f"❌ {nomi} — xato: {e}\n"

    await message.answer(matn)


async def asosiy_menyu_callback(callback: CallbackQuery):
    await callback.message.edit_text("Asosiy menyu:", reply_markup=kb.asosiy_menyu())


async def main():
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties())
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(registration.router)
    dp.include_router(davomat.router)
    dp.include_router(dars_qoldirish.router)
    dp.include_router(tatil.router)
    dp.include_router(balansim.router)
    dp.include_router(bugungi.router)

    dp.message.register(diagnostika, F.text == "/tekshir")

    scheduler = AsyncIOScheduler()
    sch.sozlash(scheduler, bot)
    scheduler.start()

    logger.info("Ustozlar boti ishga tushdi.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
