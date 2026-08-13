# handlers/dars_qoldirish.py
# Ustoz darsni oldindan "qoldirilgan" deb belgilashi — Darslar grafigiga
# yoziladi, Davomatga tegilmaydi (pul ketmaydi).

from datetime import date

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import config
import notion_service as ns
import keyboards as kb
from states import DarsQoldirish
from utils import sana_ozbekcha, yaqin_kunlar, HAFTA_KUNLARI, markdown_himoya

router = Router()


@router.callback_query(F.data == "menu_dars_qoldirish")
async def boshlash(callback: CallbackQuery, state: FSMContext):
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    if not ustoz:
        await callback.message.answer("Siz ro'yxatdan o'tmagansiz. /start ni bosing.")
        return

    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=True)
    if not guruhlar:
        await callback.message.edit_text("Sizda hozircha faol guruh yo'q.")
        return

    guruh_royxati = [{"id": g["id"], "nomi": ns.get_title(g, "Guruh nomi")} for g in guruhlar]
    await state.update_data(guruhlar=guruh_royxati)
    await state.set_state(DarsQoldirish.guruh_tanlash)
    await callback.message.edit_text(
        "Qaysi guruhning darsi qoldiriladi?",
        reply_markup=kb.guruhlar_royxati(guruh_royxati, "dq"),
    )


@router.callback_query(DarsQoldirish.guruh_tanlash, F.data.startswith("dq_g:"))
async def guruh_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    guruh = data["guruhlar"][idx]
    guruh_page = await ns.get_page(guruh["id"])

    dars_kunlari_nomlari = ns.get_multi_select(guruh_page, "Dars kunlari")
    dars_kunlari_idx = [HAFTA_KUNLARI.index(n) for n in dars_kunlari_nomlari if n in HAFTA_KUNLARI]
    sanalar = yaqin_kunlar(dars_kunlari_idx or list(range(7)), soni=4)

    sana_royxati = [{"label": sana_ozbekcha(s), "value": s.isoformat()} for s in sanalar]
    await state.update_data(tanlangan_guruh=guruh, sanalar=sana_royxati)
    await state.set_state(DarsQoldirish.sana_tanlash)
    await callback.message.edit_text(
        f"Guruh: {guruh['nomi']}\nQaysi kun?",
        reply_markup=kb.sanalar_royxati(sana_royxati, "dq"),
    )


@router.callback_query(DarsQoldirish.sana_tanlash, F.data.startswith("dq_s:"))
async def sana_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    sana = data["sanalar"][idx]["value"]
    await state.update_data(tanlangan_sana=sana)
    await state.set_state(DarsQoldirish.sabab_tanlash)
    await callback.message.edit_text(
        "Sababi?", reply_markup=kb.sabablar_royxati("dq")
    )


@router.callback_query(DarsQoldirish.sabab_tanlash, F.data.startswith("dq_sabab:"))
async def sabab_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    sabab = config.SABABLAR_RO_YXATI[idx]
    await state.update_data(tanlangan_sabab=sabab)
    await state.set_state(DarsQoldirish.izoh_kutilmoqda)
    await callback.message.edit_text(
        f"Sabab: {sabab}\n\nQisqacha izoh yozing (yoki \"-\" deb yuboring):"
    )


@router.message(DarsQoldirish.izoh_kutilmoqda)
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
                                  sabab=sabab, izoh=izoh)

    ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
    ustoz_ismi = ns.get_title(ustoz, "Ism") if ustoz else "Ustoz"

    await state.clear()
    await message.answer(
        f"🚫 {guruh['nomi']} guruhining {sana_ozbekcha(date.fromisoformat(sana))} "
        f"kungi darsi qoldirildi.\nSabab: {sabab}"
    )
    await bot.send_message(
        config.ADMIN_ID,
        f"🚫 *Dars qoldirildi*\n\n"
        f"Ustoz: {markdown_himoya(ustoz_ismi)}\n"
        f"Guruh: {markdown_himoya(guruh['nomi'])}\n"
        f"Sana: {markdown_himoya(sana_ozbekcha(date.fromisoformat(sana)))}\n"
        f"Sabab: {markdown_himoya(sabab)}",
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "dq_hammasi")
async def barcha_darslarni_qoldirish(callback: CallbackQuery, bot: Bot):
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    if not ustoz:
        return

    bugun = date.today().isoformat()
    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=True)

    qoldirilgan = []
    for g in guruhlar:
        grafik = await ns.get_grafik_yozuv(g["id"], bugun)
        if grafik and ns.get_select(grafik, "Holat") == config.GRAFIK_DARS_OTILDI:
            continue  # davomat allaqachon kiritilgan — tegilmaydi
        nomi = ns.get_title(g, "Guruh nomi")
        if grafik:
            await ns.grafik_yangilash(grafik["id"], config.GRAFIK_DARS_QOLDIRILDI, sabab=config.SABAB_BOSHQA)
        else:
            await ns.grafik_yaratish(g["id"], bugun, config.GRAFIK_DARS_QOLDIRILDI, sabab=config.SABAB_BOSHQA)
        qoldirilgan.append(nomi)

    ustoz_ismi = ns.get_title(ustoz, "Ism")
    if qoldirilgan:
        royxat = "\n".join(f"— {n}" for n in qoldirilgan)
        await callback.message.answer(f"🚫 Bugungi barcha darslar qoldirildi:\n{royxat}")
        await bot.send_message(
            config.ADMIN_ID,
            f"🚫 {markdown_himoya(ustoz_ismi)} bugungi barcha darslarini qoldirdi:\n"
            + markdown_himoya(royxat),
            parse_mode="MarkdownV2",
        )
    else:
        await callback.message.answer("Qoldiriladigan dars topilmadi (hammasi allaqachon kiritilgan).")
