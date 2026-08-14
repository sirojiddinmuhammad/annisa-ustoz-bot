# handlers/dars_qoldirish.py
# Dars qoldirish — Darslar grafigiga yoziladi, Davomatga tegilmaydi.

from datetime import date

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import config
import notion_service as ns
import keyboards as kb
from states import DarsQoldirish
from utils import (sana_ozbekcha, yaqin_kunlar, html_himoya, CHIZIQ,
                   dars_kunlari_raqamga, bugun)

router = Router()


@router.message(F.text == kb.BTN_DARS_QOLDIRISH)
async def boshlash(message: Message, state: FSMContext):
    await state.clear()
    ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
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
        f"<b>🚫  Dars qoldirish</b>\n"
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
async def sabab_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    sabab = config.SABABLAR_RO_YXATI[idx]
    await state.update_data(tanlangan_sabab=sabab)
    await state.set_state(DarsQoldirish.izoh_kutilmoqda)
    await callback.message.edit_text(
        f"<b>🚫  Dars qoldirish</b>\n"
        f"{CHIZIQ}\n"
        f"Sabab: <b>{sabab}</b>\n\n"
        f"Qisqacha izoh yozing.\n"
        f"Izoh kerak bo'lmasa <code>-</code> yuboring."
    )


@router.message(DarsQoldirish.izoh_kutilmoqda, ~F.text.in_(kb.MENYU_TUGMALARI))
async def izoh_qabul_qilish(message: Message, state: FSMContext, bot: Bot):
    izoh = message.text.strip()
    if izoh == "-":
        izoh = None

    data = await state.get_data()
    guruh = data["tanlangan_guruh"]
    sana = data["tanlangan_sana"]
    sabab = data["tanlangan_sabab"]

    grafik = await ns.get_grafik_yozuv(guruh["id"], sana)
    if grafik:
        await ns.grafik_yangilash(grafik["id"], config.GRAFIK_DARS_QOLDIRILDI, sabab=sabab)
    else:
        await ns.grafik_yaratish(guruh["id"], sana, config.GRAFIK_DARS_QOLDIRILDI,
                                  sabab=sabab, izoh=izoh, guruh_nomi=guruh["nomi"])

    ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
    ustoz_ismi = ns.get_title(ustoz, "Ism") if ustoz else "Ustoz"

    await state.clear()
    await message.answer(
        f"<b>🚫  Dars qoldirildi</b>\n"
        f"{CHIZIQ}\n"
        f"📚  {html_himoya(guruh['nomi'])}\n"
        f"📅  {sana_ozbekcha(date.fromisoformat(sana))}\n"
        f"📝  {sabab}"
    )

    admin_matn = (
        f"<b>🚫  Dars qoldirildi</b>\n"
        f"{CHIZIQ}\n"
        f"Ustoz: {html_himoya(ustoz_ismi)}\n"
        f"Guruh: {html_himoya(guruh['nomi'])}\n"
        f"Sana: {sana_ozbekcha(date.fromisoformat(sana))}\n"
        f"Sabab: {sabab}"
    )
    if izoh:
        admin_matn += f"\nIzoh: {html_himoya(izoh)}"
    await bot.send_message(config.ADMIN_ID, admin_matn)


@router.callback_query(F.data == "dq_hammasi")
async def barcha_darslarni_qoldirish(callback: CallbackQuery, bot: Bot):
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    if not ustoz:
        return

    await callback.answer("Bajarilmoqda...")
    bugun_iso = bugun().isoformat()
    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=True)

    qoldirilgan = []
    for g in guruhlar:
        grafik = await ns.get_grafik_yozuv(g["id"], bugun_iso)
        if grafik and ns.get_select(grafik, "Holat") == config.GRAFIK_DARS_OTILDI:
            continue
        nomi = ns.get_title(g, "Guruh nomi")
        if grafik:
            await ns.grafik_yangilash(grafik["id"], config.GRAFIK_DARS_QOLDIRILDI,
                                       sabab=config.SABAB_BOSHQA)
        else:
            await ns.grafik_yaratish(g["id"], bugun_iso, config.GRAFIK_DARS_QOLDIRILDI,
                                      sabab=config.SABAB_BOSHQA, guruh_nomi=nomi)
        qoldirilgan.append(nomi)

    ustoz_ismi = ns.get_title(ustoz, "Ism")
    if qoldirilgan:
        royxat = "\n".join(f"•  {html_himoya(n)}" for n in qoldirilgan)
        await callback.message.answer(
            f"<b>🚫  Bugungi barcha darslar qoldirildi</b>\n"
            f"{CHIZIQ}\n{royxat}"
        )
        await bot.send_message(
            config.ADMIN_ID,
            f"<b>🚫  Barcha darslar qoldirildi</b>\n"
            f"{CHIZIQ}\n"
            f"Ustoz: {html_himoya(ustoz_ismi)}\n"
            f"{royxat}"
        )
    else:
        await callback.message.answer(
            "Qoldiriladigan dars topilmadi — hammasiga davomat kiritilgan."
        )
