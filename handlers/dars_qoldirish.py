# handlers/dars_qoldirish.py
# Dars qoldirish — Darslar grafigiga yoziladi, Davomatga tegilmaydi.
#
# MUHIM o'zgarish: izoh endi MAJBURIY EMAS.
# Ilgari sabab tanlangach bot matn kutib qolardi — ustoz yozishni unutsa,
# oqim yarim qolib Notionga hech narsa yozilmasdi. Ustoz "qoldirdim" deb
# o'ylardi, aslida yozuv yaratilmagan bo'lardi.
# Endi: sabab tanlanishi bilan dars DARHOL qoldiriladi, izoh esa keyin
# tugma orqali ixtiyoriy qo'shiladi.

from datetime import date

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
import notion_service as ns
import admin_xabar
import keyboards as kb
import admin_rejim
from admin_rejim import haqiqiy_ustoz
from states import DarsQoldirish
from utils import (sana_ozbekcha, yaqin_kunlar, html_himoya, CHIZIQ,
                   dars_kunlari_raqamga, bugun)

router = Router()


class Izoh(StatesGroup):
    kutilmoqda = State()


# ---------------------------------------------------------------------------
# Bitta guruh darsini qoldirish
# ---------------------------------------------------------------------------

@router.message(F.text == kb.BTN_DARS_QOLDIRISH)
async def boshlash(message: Message, state: FSMContext):
    await state.clear()
    ustoz = await haqiqiy_ustoz(message.from_user.id)
    if not ustoz:
        await message.answer("Siz hali ro'yxatdan o'tmagansiz.\n/start ni bosing.")
        return

    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=True)
    if not guruhlar:
        await message.answer("📭  Sizda hozircha faol guruh yo'q.")
        return

    guruh_royxati = [
        {"id": g["id"], "nomi": ns.get_title(g, "Guruh nomi"),
         "vaqt": ns.get_select(g, "Dars vaqti")}
        for g in guruhlar
    ]
    await state.update_data(guruhlar=guruh_royxati)
    await state.set_state(DarsQoldirish.guruh_tanlash)
    await message.answer(
        admin_rejim.sarlavha(message.from_user.id)
        + f"<b>🚫  Dars qoldirish</b>\n"
        f"{CHIZIQ}\n"
        f"Qaysi guruhning darsi qoldiriladi?",
        reply_markup=kb.guruhlar_royxati(guruh_royxati, "dq"),
    )


@router.callback_query(DarsQoldirish.guruh_tanlash, F.data.startswith("dq_g:"))
async def guruh_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    guruh = data["guruhlar"][idx]
    guruh_page = await ns.get_page(guruh["id"])

    kunlari = dars_kunlari_raqamga(ns.get_multi_select(guruh_page, "Dars kunlari"))
    sanalar = yaqin_kunlar(kunlari or list(range(7)), soni=4)

    sana_royxati = [{"label": sana_ozbekcha(s), "value": s.isoformat()} for s in sanalar]
    await state.update_data(tanlangan_guruh=guruh, sanalar=sana_royxati)
    await state.set_state(DarsQoldirish.sana_tanlash)
    await callback.message.edit_text(
        f"<b>🚫  Dars qoldirish</b>\n"
        f"{CHIZIQ}\n"
        f"📚  {html_himoya(guruh['nomi'])}\n\n"
        f"Qaysi kun?",
        reply_markup=kb.sanalar_royxati(sana_royxati, "dq"),
    )


@router.callback_query(DarsQoldirish.sana_tanlash, F.data.startswith("dq_s:"))
async def sana_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    sana = data["sanalar"][idx]["value"]
    guruh = data["tanlangan_guruh"]
    await state.update_data(tanlangan_sana=sana)
    await state.set_state(DarsQoldirish.sabab_tanlash)
    await callback.message.edit_text(
        f"<b>🚫  Dars qoldirish</b>\n"
        f"{CHIZIQ}\n"
        f"📚  {html_himoya(guruh['nomi'])}\n"
        f"📅  {sana_ozbekcha(date.fromisoformat(sana))}\n\n"
        f"Sababi nima?",
        reply_markup=kb.sabablar_royxati("dq"),
    )


@router.callback_query(DarsQoldirish.sabab_tanlash, F.data.startswith("dq_sabab:"))
async def sabab_tanlandi(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Sabab tanlanishi bilan dars DARHOL qoldiriladi — izoh kutilmaydi."""
    idx = int(callback.data.split(":")[1])
    sabab = config.SABABLAR_RO_YXATI[idx]

    data = await state.get_data()
    guruh = data["tanlangan_guruh"]
    sana = data["tanlangan_sana"]

    await callback.answer("Saqlanmoqda...")

    grafik = await ns.get_grafik_yozuv(guruh["id"], sana)
    if grafik:
        await ns.grafik_yangilash(grafik["id"], config.GRAFIK_DARS_QOLDIRILDI, sabab=sabab)
        grafik_id = grafik["id"]
    else:
        yangi = await ns.grafik_yaratish(
            guruh["id"], sana, config.GRAFIK_DARS_QOLDIRILDI,
            sabab=sabab, guruh_nomi=guruh["nomi"],
        )
        grafik_id = yangi["id"]

    ustoz = await haqiqiy_ustoz(callback.from_user.id)
    ustoz_ismi = ns.get_title(ustoz, "Ism") if ustoz else "Ustoz"

    await state.clear()
    await callback.message.edit_text(
        f"<b>🚫  Dars qoldirildi</b>\n"
        f"{CHIZIQ}\n"
        f"📚  {html_himoya(guruh['nomi'])}\n"
        f"📅  {sana_ozbekcha(date.fromisoformat(sana))}\n"
        f"📝  {sabab}\n"
        f"{CHIZIQ}\n"
        f"<i>Qo'shimcha izoh yozmoqchi bo'lsangiz — quyidagi tugma.\n"
        f"Shart emas, hammasi allaqachon saqlandi.</i>",
        reply_markup=kb.izoh_qoshish([grafik_id]),
    )

    admin_matn = (
        f"<b>🚫  Dars qoldirildi</b>\n"
        f"{CHIZIQ}\n"
        f"Ustoz: {html_himoya(ustoz_ismi)}\n"
        f"Guruh: {html_himoya(guruh['nomi'])}\n"
        f"Sana: {sana_ozbekcha(date.fromisoformat(sana))}\n"
        f"Sabab: {sabab}"
    )
    await admin_xabar.yuborish(admin_matn, bot)

    await admin_rejim.ustozni_ogohlantirish(
        callback.from_user.id,
        f"🚫  <b>{html_himoya(guruh['nomi'])}</b> guruhining\n"
        f"{sana_ozbekcha(date.fromisoformat(sana))} kungi darsi qoldirildi.\n"
        f"Sabab: {html_himoya(sabab)}",
        bot,
    )


# ---------------------------------------------------------------------------
# Izoh qo'shish (ixtiyoriy)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("dq_izoh:"))
async def izoh_sorash(callback: CallbackQuery, state: FSMContext):
    """Grafik yozuv ID si tugmadan olinadi — xotira kerak emas, shuning
    uchun ustoz ertasi kuni bossa ham ishlayveradi."""
    grafik_id = callback.data.split(":", 1)[1]
    await state.set_state(Izoh.kutilmoqda)
    await state.update_data(izoh_grafik_idlar=[grafik_id])
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"<b>📝  Izoh</b>\n"
        f"{CHIZIQ}\n"
        f"Qisqacha izoh yozing."
    )


@router.callback_query(F.data.startswith("dq_izohall:"))
async def izoh_sorash_barcha(callback: CallbackQuery, state: FSMContext):
    """Barcha darslar qoldirilgan holat — izoh hammasiga birdan qo'shiladi.
    Tugmada ustoz ID va sana turadi, yozuvlar shular bo'yicha qayta topiladi."""
    qism = callback.data.split(":", 1)[1]
    ustoz_id, sana = qism.rsplit(":", 1)

    await callback.answer("Yuklanmoqda...")
    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz_id, davomatli_faqat=True)
    idlar = []
    for g in guruhlar:
        grafik = await ns.get_grafik_yozuv(g["id"], sana)
        if grafik and ns.get_select(grafik, "Holat") == config.GRAFIK_DARS_QOLDIRILDI:
            idlar.append(grafik["id"])

    if not idlar:
        await callback.message.answer("Izoh qo'shiladigan yozuv topilmadi.")
        return

    await state.set_state(Izoh.kutilmoqda)
    await state.update_data(izoh_grafik_idlar=idlar)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"<b>📝  Izoh</b>\n"
        f"{CHIZIQ}\n"
        f"Izoh <b>{len(idlar)} ta</b> darsga qo'shiladi.\n\n"
        f"Qisqacha izoh yozing."
    )


@router.message(Izoh.kutilmoqda, ~F.text.in_(kb.MENYU_TUGMALARI))
async def izoh_qabul(message: Message, state: FSMContext, bot: Bot):
    matn = (message.text or "").strip()
    if len(matn) < 2:
        await message.answer("Izohni biroz to'liqroq yozing.")
        return

    data = await state.get_data()
    idlar = data.get("izoh_grafik_idlar", [])
    await state.clear()

    for grafik_id in idlar:
        try:
            await ns.grafik_izoh_qoshish(grafik_id, matn)
        except Exception:
            pass

    await message.answer(
        f"<b>✅  Izoh qo'shildi</b>\n"
        f"{CHIZIQ}\n"
        f"{html_himoya(matn)}"
    )

    ustoz = await haqiqiy_ustoz(message.from_user.id)
    ustoz_ismi = ns.get_title(ustoz, "Ism") if ustoz else "Ustoz"
    await admin_xabar.yuborish(
        f"<b>📝  Qoldirilgan darsga izoh</b>\n"
        f"{CHIZIQ}\n"
        f"Ustoz: {html_himoya(ustoz_ismi)}\n"
        f"Izoh: {html_himoya(matn)}",
        bot,
    )


# ---------------------------------------------------------------------------
# Bugungi barcha darslarni qoldirish
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "dq_hammasi")
async def barcha_sabab_sorash(callback: CallbackQuery, state: FSMContext):
    ustoz = await haqiqiy_ustoz(callback.from_user.id)
    if not ustoz:
        return
    await state.clear()
    await callback.message.answer(
        f"<b>🚫  Bugungi barcha darslarni qoldirish</b>\n"
        f"{CHIZIQ}\n"
        f"Sababi nima?",
        reply_markup=kb.barcha_sabablar(),
    )


@router.callback_query(F.data == "dqall_bekor")
async def barcha_bekor(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("↩️  Bekor qilindi. Hech narsa o'zgarmadi.")


@router.callback_query(F.data.startswith("dqall_sabab:"))
async def barcha_qoldirish(callback: CallbackQuery, state: FSMContext, bot: Bot):
    idx = int(callback.data.split(":")[1])
    sabab = config.SABABLAR_RO_YXATI[idx]

    ustoz = await haqiqiy_ustoz(callback.from_user.id)
    if not ustoz:
        return

    await callback.answer("Bajarilmoqda...")
    bugun_iso = bugun().isoformat()
    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=True)

    qoldirilgan = []
    for g in guruhlar:
        grafik = await ns.get_grafik_yozuv(g["id"], bugun_iso)
        # Davomat kiritilgan yoki talabaga ta'til berilgan guruhga tegilmaydi —
        # ularda kun allaqachon hal qilingan, ustidan yozish ma'lumotni yo'qotadi
        tegilmaydi = (config.GRAFIK_DARS_OTILDI, config.GRAFIK_TALABAGA_TATIL)
        if grafik and ns.get_select(grafik, "Holat") in tegilmaydi:
            continue
        nomi = ns.get_title(g, "Guruh nomi")
        if grafik:
            await ns.grafik_yangilash(grafik["id"], config.GRAFIK_DARS_QOLDIRILDI,
                                       sabab=sabab)
        else:
            await ns.grafik_yaratish(g["id"], bugun_iso, config.GRAFIK_DARS_QOLDIRILDI,
                                      sabab=sabab, guruh_nomi=nomi)
        qoldirilgan.append(nomi)

    await state.clear()
    ustoz_ismi = ns.get_title(ustoz, "Ism")

    if not qoldirilgan:
        await callback.message.edit_text(
            "Qoldiriladigan dars topilmadi — hammasiga davomat kiritilgan."
        )
        return

    royxat = "\n".join(f"•  {html_himoya(n)}" for n in qoldirilgan)
    kalit = f"{ustoz['id'].replace('-', '')}:{bugun_iso}"
    await callback.message.edit_text(
        f"<b>🚫  Bugungi barcha darslar qoldirildi</b>\n"
        f"{CHIZIQ}\n{royxat}\n"
        f"{CHIZIQ}\n"
        f"📝  Sabab: {sabab}\n\n"
        f"<i>Qo'shimcha izoh yozmoqchi bo'lsangiz — quyidagi tugma.</i>",
        reply_markup=kb.barcha_izoh_qoshish(kalit),
    )

    await admin_xabar.yuborish(
        f"<b>🚫  Barcha darslar qoldirildi</b>\n"
        f"{CHIZIQ}\n"
        f"Ustoz: {html_himoya(ustoz_ismi)}\n"
        f"Sabab: {sabab}\n"
        f"{royxat}",
        bot,
    )

    await admin_rejim.ustozni_ogohlantirish(
        callback.from_user.id,
        f"🚫  Bugungi barcha darslaringiz qoldirildi.\nSabab: {sabab}",
        bot,
    )
