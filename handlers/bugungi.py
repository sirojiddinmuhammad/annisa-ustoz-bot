# handlers/bugungi.py
# Bugungi darslar ro'yxati + Belgilanmagan ogohlantirish.

from datetime import date

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

import config
import notion_service as ns
import keyboards as kb
from utils import (sana_ozbekcha, html_himoya, CHIZIQ,
                   dars_kunlari_raqamga, vaqt_tartibi, bugun,
                   belgilanmagan_royxat_matni)

router = Router()

HOLAT_BELGISI = {
    config.GRAFIK_DARS_OTILDI: "✅",
    config.GRAFIK_DARS_QOLDIRILDI: "🚫",
    config.GRAFIK_BELGILANMAGAN: "⏳",
}

HOLAT_MATNI = {
    config.GRAFIK_DARS_OTILDI: "davomat kiritilgan",
    config.GRAFIK_DARS_QOLDIRILDI: "dars qoldirilgan",
    config.GRAFIK_BELGILANMAGAN: "kutilmoqda",
}


@router.message(F.text == kb.BTN_BUGUNGI)
async def bugungi_darslar(message: Message, state: FSMContext):
    await state.clear()
    ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
    if not ustoz:
        await message.answer("Siz hali ro'yxatdan o'tmagansiz.\n/start ni bosing.")
        return

    kutish = await message.answer("⏳  Yuklanmoqda...")

    bugun_sana = bugun()
    bugun_iso = bugun_sana.isoformat()
    kun_idx = bugun_sana.weekday()

    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=True)
    bugungi = []
    for g in guruhlar:
        kunlari = dars_kunlari_raqamga(ns.get_multi_select(g, "Dars kunlari"))
        if kun_idx in kunlari:
            bugungi.append(g)

    # Dars vaqti bo'yicha saralaymiz
    bugungi.sort(key=lambda g: vaqt_tartibi(ns.get_select(g, "Dars vaqti")))

    matn = (
        f"<b>📅  Bugungi darslar</b>\n"
        f"<i>{sana_ozbekcha(bugun_sana)}</i>\n"
        f"{CHIZIQ}\n"
    )

    kutilmoqda = 0
    if not bugungi:
        matn += "🌿  Bugun darsingiz yo'q.\nYaxshi dam oling!"
    else:
        for g in bugungi:
            nomi = ns.get_title(g, "Guruh nomi")
            vaqt = ns.get_select(g, "Dars vaqti") or "vaqti belgilanmagan"
            grafik = await ns.get_grafik_yozuv(g["id"], bugun_iso)
            holat = ns.get_select(grafik, "Holat") if grafik else config.GRAFIK_BELGILANMAGAN
            belgi = HOLAT_BELGISI.get(holat, "⏳")
            izoh = HOLAT_MATNI.get(holat, holat)

            matn += (
                f"\n🕐  <b>{html_himoya(vaqt)}</b>\n"
                f"📚  {html_himoya(nomi)}\n"
                f"{belgi}  <i>{izoh}</i>\n"
            )
            if holat == config.GRAFIK_BELGILANMAGAN:
                kutilmoqda += 1

        matn += f"{CHIZIQ}\n👥  Jami: {len(bugungi)} ta dars"
        if kutilmoqda:
            matn += f"  ·  ⏳ {kutilmoqda} ta kutilmoqda"

    belgilanmagan = await ns.belgilanmagan_darslar()
    guruh_idlari = {g["id"] for g in guruhlar}
    ozimizniki = [
        b for b in belgilanmagan
        if ns.get_relation_ids(b, "Guruh") and ns.get_relation_ids(b, "Guruh")[0] in guruh_idlari
    ]
    if ozimizniki:
        matn += (
            f"\n{CHIZIQ}\n"
            f"⚠️  <b>Belgilanmagan darslar: {len(ozimizniki)} ta</b>\n"
            f"<i>Oxirgi {config.BELGILANMAGAN_TEKSHIRUV_KUN} kun ichida</i>\n"
            + belgilanmagan_royxat_matni(ozimizniki, ns)
            + "\n\n<i>Davomat bo'limidan o'sha kunni tanlab kiriting.</i>"
        )

    markup = kb.barcha_darslarni_qoldirish() if kutilmoqda > 1 else None
    await kutish.edit_text(matn, reply_markup=markup)
