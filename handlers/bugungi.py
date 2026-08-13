# handlers/bugungi.py
# Bugungi darslar ro'yxati + Belgilanmagan ogohlantirish.

from datetime import date

from aiogram import Router, F
from aiogram.types import Message

import config
import notion_service as ns
import keyboards as kb
from utils import HAFTA_KUNLARI, sana_ozbekcha, html_himoya, CHIZIQ

router = Router()


@router.message(F.text == kb.BTN_BUGUNGI)
async def bugungi_darslar(message: Message):
    ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
    if not ustoz:
        await message.answer("Siz hali ro'yxatdan o'tmagansiz.\n/start ni bosing.")
        return

    kutish = await message.answer("⏳  Yuklanmoqda...")

    bugun = date.today()
    bugun_iso = bugun.isoformat()
    kun_idx = bugun.weekday()

    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=True)
    bugungi = []
    for g in guruhlar:
        kunlari = [HAFTA_KUNLARI.index(n) for n in ns.get_multi_select(g, "Dars kunlari")
                   if n in HAFTA_KUNLARI]
        if kun_idx in kunlari:
            bugungi.append(g)

    matn = (
        f"<b>📅  Bugungi darslar</b>\n"
        f"{sana_ozbekcha(bugun)}\n"
        f"{CHIZIQ}\n"
    )

    kutilmoqda = 0
    if not bugungi:
        matn += "🌿  Bugun darsingiz yo'q. Yaxshi dam oling!"
    else:
        for g in bugungi:
            nomi = ns.get_title(g, "Guruh nomi")
            grafik = await ns.get_grafik_yozuv(g["id"], bugun_iso)
            holat = ns.get_select(grafik, "Holat") if grafik else config.GRAFIK_BELGILANMAGAN
            belgi = {
                config.GRAFIK_DARS_OTILDI: "✅",
                config.GRAFIK_DARS_QOLDIRILDI: "🚫",
            }.get(holat, "⏳")
            matn += f"{belgi}  <b>{html_himoya(nomi)}</b>\n     {holat}\n"
            if holat == config.GRAFIK_BELGILANMAGAN:
                kutilmoqda += 1

    belgilanmagan = await ns.belgilanmagan_darslar()
    guruh_idlari = {g["id"] for g in guruhlar}
    ozimizniki = [
        b for b in belgilanmagan
        if ns.get_relation_ids(b, "Guruh") and ns.get_relation_ids(b, "Guruh")[0] in guruh_idlari
    ]
    if ozimizniki:
        matn += (
            f"{CHIZIQ}\n"
            f"⚠️  <b>Belgilanmagan darslar: {len(ozimizniki)} ta</b>\n"
            f"Oxirgi {config.BELGILANMAGAN_TEKSHIRUV_KUN} kun ichida"
        )

    markup = kb.barcha_darslarni_qoldirish() if kutilmoqda > 1 else None
    await kutish.edit_text(matn, reply_markup=markup)
