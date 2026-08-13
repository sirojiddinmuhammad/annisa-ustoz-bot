# handlers/bugungi.py
# Bugungi darslar ro'yxati + Belgilanmagan ogohlantirish.

from datetime import date

from aiogram import Router, F
from aiogram.types import CallbackQuery

import config
import notion_service as ns
import keyboards as kb
from utils import HAFTA_KUNLARI, sana_ozbekcha

router = Router()


@router.callback_query(F.data == "menu_bugungi")
async def bugungi_darslar(callback: CallbackQuery):
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    if not ustoz:
        await callback.message.answer("Siz ro'yxatdan o'tmagansiz. /start ni bosing.")
        return

    await callback.answer("Yuklanmoqda...")
    bugun = date.today()
    bugun_iso = bugun.isoformat()
    bugungi_kun_idx = bugun.weekday()

    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=False)
    bugungi_guruhlar = []
    for g in guruhlar:
        if ns.get_checkbox(g, "Davomat kerak emas"):
            continue  # bu bo'limda faqat davomatli guruhlar ko'rsatiladi
        kunlari = [HAFTA_KUNLARI.index(n) for n in ns.get_multi_select(g, "Dars kunlari") if n in HAFTA_KUNLARI]
        if bugungi_kun_idx in kunlari:
            bugungi_guruhlar.append(g)

    matn = f"📅 Bugungi darslar — {sana_ozbekcha(bugun)}\n\n"
    kutilmoqda_soni = 0
    if not bugungi_guruhlar:
        matn += "Bugun darsingiz yo'q."
    else:
        for g in bugungi_guruhlar:
            nomi = ns.get_title(g, "Guruh nomi")
            grafik = await ns.get_grafik_yozuv(g["id"], bugun_iso)
            holat = ns.get_select(grafik, "Holat") if grafik else config.GRAFIK_BELGILANMAGAN
            belgi = {
                config.GRAFIK_DARS_OTILDI: "✅",
                config.GRAFIK_DARS_QOLDIRILDI: "🚫",
            }.get(holat, "⏳")
            matn += f"{belgi} {nomi} — {holat}\n"
            if holat == config.GRAFIK_BELGILANMAGAN:
                kutilmoqda_soni += 1

    belgilanmagan = await ns.belgilanmagan_darslar()
    ustoz_guruh_idlari = {g["id"] for g in guruhlar}
    ozimizniki = [
        b for b in belgilanmagan
        if ns.get_relation_ids(b, "Guruh") and ns.get_relation_ids(b, "Guruh")[0] in ustoz_guruh_idlari
    ]
    if ozimizniki:
        matn += f"\n⚠️ Oxirgi {config.BELGILANMAGAN_TEKSHIRUV_KUN} kunda belgilanmagan: {len(ozimizniki)} ta dars"

    markup = kb.barcha_darslarni_qoldirish() if kutilmoqda_soni > 1 else None
    await callback.message.edit_text(matn, reply_markup=markup)


@router.callback_query(F.data == "menu_asosiy")
async def asosiy_menyuga_qaytish(callback: CallbackQuery):
    await callback.message.edit_text("Asosiy menyu:", reply_markup=kb.asosiy_menyu())
