# main.py
# Ustozlar boti — kirish nuqtasi.

import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import keyboards as kb
import notion_service as ns
import scheduler as sch
import webserver
from utils import CHIZIQ

from handlers import (registration, davomat, dars_qoldirish, tatil,
                      balansim, bugungi, qollanma)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Diagnostika va zaxira ushlagichlar uchun alohida router.
# Diqqat: zaxira ushlagich ENG OXIRIDA ulanishi shart, aks holda u
# barcha xabarlarni o'zi ushlab qoladi va menyu ishlamay qoladi.
xizmat_router = Router()
zaxira_router = Router()


@xizmat_router.message(Command("tekshir"))
async def diagnostika(message: Message):
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
            matn += f"❌  {nomi} — {str(e)[:80]}\n"

    await kutish.edit_text(matn)


@xizmat_router.message(Command("menyu"))
async def menyu_korsatish(message: Message):
    await message.answer(
        "Quyidagi menyudan tanlang 👇",
        reply_markup=kb.asosiy_menyu(),
    )


@zaxira_router.message(F.text)
async def notanish_xabar(message: Message):
    """Hech qaysi handlerga tushmagan matnlar uchun."""
    await message.answer(
        "Menyudan tanlang 👇",
        reply_markup=kb.asosiy_menyu(),
    )


async def main():
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(xizmat_router)
    dp.include_router(registration.router)
    dp.include_router(davomat.router)
    dp.include_router(dars_qoldirish.router)
    dp.include_router(tatil.router)
    dp.include_router(balansim.router)
    dp.include_router(bugungi.router)
    dp.include_router(qollanma.router)
    dp.include_router(zaxira_router)  # eng oxirida!

    scheduler = AsyncIOScheduler()
    sch.sozlash(scheduler, bot)
    scheduler.start()

    # Web server (Mini App uchun) polling bilan parallel ishlaydi
    runner = await webserver.ishga_tushirish()

    logger.info("Ustozlar boti ishga tushdi.")
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
