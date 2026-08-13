# handlers/balansim.py

from datetime import date

from aiogram import Router, F
from aiogram.types import Message

import notion_service as ns
import money_service as ms
import keyboards as kb
from utils import summa_format, OYLAR, CHIZIQ

router = Router()


@router.message(F.text == kb.BTN_BALANS)
async def balansim(message: Message):
    ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
    if not ustoz:
        await message.answer("Siz hali ro'yxatdan o'tmagansiz.\n/start ni bosing.")
        return

    kutish = await message.answer("⏳  Hisoblanmoqda...")
    natija = await ms.ustoz_balansi_hisobla(ustoz)
    oy_nomi = OYLAR[date.today().month - 1]

    balans = natija["balans"]
    belgi = "🟢" if balans >= 0 else "🔴"

    await kutish.edit_text(
        f"<b>💰  Balansingiz</b>\n"
        f"{CHIZIQ}\n"
        f"Jami ishlab topgan\n"
        f"<b>{summa_format(natija['ishlab_topgani'])}</b> so'm\n\n"
        f"Berilgan oyliklar\n"
        f"<b>{summa_format(natija['berilgan_oyliklar'])}</b> so'm\n"
        f"{CHIZIQ}\n"
        f"{belgi}  <b>Balans:  {summa_format(balans)} so'm</b>\n"
        f"{CHIZIQ}\n"
        f"📆  Shu oy ({oy_nomi})\n"
        f"<b>{summa_format(natija['shu_oy'])}</b> so'm"
    )
