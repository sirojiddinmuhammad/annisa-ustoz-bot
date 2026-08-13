# handlers/balansim.py

from datetime import date

from aiogram import Router, F
from aiogram.types import CallbackQuery

import notion_service as ns
import money_service as ms
from utils import summa_format, OYLAR

router = Router()


@router.callback_query(F.data == "menu_balans")
async def balansim(callback: CallbackQuery):
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    if not ustoz:
        await callback.message.answer("Siz ro'yxatdan o'tmagansiz. /start ni bosing.")
        return

    await callback.answer("Hisoblanmoqda...")
    natija = await ms.ustoz_balansi_hisobla(ustoz)
    oy_nomi = OYLAR[date.today().month - 1]

    matn = (
        "💰 Sizning balansingiz\n\n"
        f"Jami ishlab topgan: {summa_format(natija['ishlab_topgani'])} so'm\n"
        f"Berilgan oyliklar: {summa_format(natija['berilgan_oyliklar'])} so'm\n"
        "─────────────────────\n"
        f"Balans: {summa_format(natija['balans'])} so'm\n\n"
        f"Shu oy ({oy_nomi}): {summa_format(natija['shu_oy'])} so'm"
    )
    await callback.message.edit_text(matn)
