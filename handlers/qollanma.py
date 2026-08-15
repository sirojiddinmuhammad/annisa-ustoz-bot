# handlers/qollanma.py
# Qo'llanma — Telegram Mini App sifatida ochiladi.
#
# Menyudagi "📖 Qo'llanma" tugmasi web_app tugmasi bo'lgani uchun bosilganda
# darhol ochiladi va botga xabar yubormaydi. Shuning uchun bu yerdagi matn
# ushlagichi faqat ikki holatda ishlaydi:
#   1) WEBAPP_URL sozlanmagan (tugma oddiy matn tugmasiga aylangan)
#   2) Ustozda eski klaviatura qolgan (yangilanmagan)

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

import config
import keyboards as kb
from utils import CHIZIQ

router = Router()

QOLLANMA_MATNI = (
    f"<b>📖  Botdan foydalanish qo'llanmasi</b>\n"
    f"{CHIZIQ}\n"
    f"Davomat kiritish, dars qoldirish, ta'til olish va balansni ko'rish "
    f"bo'yicha to'liq yo'riqnoma.\n\n"
    f"Quyidagi tugmani bosing 👇"
)

MAVJUD_EMAS = (
    f"<b>📖  Qo'llanma</b>\n"
    f"{CHIZIQ}\n"
    f"Qo'llanma hozircha mavjud emas.\n"
    f"Iltimos, keyinroq urinib ko'ring yoki administratorga murojaat qiling."
)


@router.message(Command("qollanma"))
async def qollanma_buyruq(message: Message, state: FSMContext):
    await state.clear()
    await _yuborish(message)


@router.message(F.text == kb.BTN_QOLLANMA)
async def qollanma_tugma(message: Message, state: FSMContext):
    await state.clear()
    await _yuborish(message)


async def _yuborish(message: Message):
    if not config.WEBAPP_URL:
        await message.answer(MAVJUD_EMAS)
        return
    await message.answer(QOLLANMA_MATNI, reply_markup=kb.qollanma_inline())
