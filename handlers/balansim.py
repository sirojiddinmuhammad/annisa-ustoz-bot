# handlers/balansim.py

from datetime import date

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import notion_service as ns
import money_service as ms
import keyboards as kb
import admin_xabar
from admin_rejim import haqiqiy_ustoz
from utils import summa_format, OYLAR, CHIZIQ, bugun, html_himoya, sana_qisqa

router = Router()


@router.message(F.text == kb.BTN_BALANS)
async def balansim(message: Message, state: FSMContext):
    await state.clear()
    ustoz = await haqiqiy_ustoz(message.from_user.id)
    if not ustoz:
        await message.answer("Siz hali ro'yxatdan o'tmagansiz.\n/start ni bosing.")
        return

    kutish = await message.answer("⏳  Hisoblanmoqda...")
    natija = await ms.ustoz_balansi_hisobla(ustoz)
    oy_nomi = OYLAR[bugun().month - 1]

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
        f"<b>{summa_format(natija['shu_oy'])}</b> so'm",
        reply_markup=kb.oylik_sorash(),
    )


@router.callback_query(F.data == "oylik_sora")
async def oylik_sorash(callback: CallbackQuery, bot: Bot):
    """Ustoz oylik so'raydi — adminga balans ma'lumoti bilan xabar boradi."""
    ustoz = await haqiqiy_ustoz(callback.from_user.id)
    if not ustoz:
        await callback.answer("Siz ro'yxatdan o'tmagansiz.", show_alert=True)
        return

    await callback.answer("Yuborilmoqda...")
    natija = await ms.ustoz_balansi_hisobla(ustoz)
    ismi = ns.get_title(ustoz, "Ism")
    balans = natija["balans"]
    belgi = "🟢" if balans >= 0 else "🔴"

    await admin_xabar.yuborish(
        f"<b>💸  Oylik so'rovi</b>\n"
        f"{CHIZIQ}\n"
        f"Ustoz: <b>{html_himoya(ismi)}</b>\n"
        f"Sana: {sana_qisqa(bugun())}\n"
        f"{CHIZIQ}\n"
        f"Jami ishlab topgan: {summa_format(natija['ishlab_topgani'])} so'm\n"
        f"Berilgan oyliklar: {summa_format(natija['berilgan_oyliklar'])} so'm\n\n"
        f"{belgi}  <b>Berilishi kerak: {summa_format(balans)} so'm</b>",
        bot,
    )

    await callback.message.answer(
        f"<b>✅  So'rovingiz yuborildi</b>\n"
        f"{CHIZIQ}\n"
        f"Administrator ko'rib chiqadi."
    )
