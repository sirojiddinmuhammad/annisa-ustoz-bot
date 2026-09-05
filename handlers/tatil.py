# handlers/tatil.py
# Ustozning o'zi ta'til olishi. Sanalar tugma orqali tanlanadi.

import re
from datetime import date, timedelta

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import config
import notion_service as ns
import admin_xabar
import keyboards as kb
from states import Tatil
from utils import sana_ozbekcha, sana_qisqa, html_himoya, CHIZIQ, bugun

router = Router()

SANA_REGEX = re.compile(r"^(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})$")


def _sanani_parse(matn: str) -> date | None:
    m = SANA_REGEX.match(matn.strip())
    if not m:
        return None
    kun, oy, yil = map(int, m.groups())
    try:
        return date(yil, oy, kun)
    except ValueError:
        return None


@router.message(F.text == kb.BTN_TATIL)
async def tatil_boshlash(message: Message, state: FSMContext):
    await state.clear()
    ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
    if not ustoz:
        await message.answer("Siz hali ro'yxatdan o'tmagansiz.\n/start ni bosing.")
        return

    if ns.ustoz_tatilda_mi(ustoz, bugun()):
        boshlanish = ns.get_date_start(ustoz, "Ta'til boshlanishi")
        tugash = ns.get_date_start(ustoz, "Ta'til tugashi")
        await message.answer(
            f"<b>🌴  Siz hozir ta'tildasiz</b>\n"
            f"{CHIZIQ}\n"
            f"Boshlangan: {sana_qisqa(date.fromisoformat(boshlanish[:10]))}\n"
            f"Tugaydi: {sana_qisqa(date.fromisoformat(tugash[:10]))}\n\n"
            f"Erta qaytmoqchimisiz?",
            reply_markup=kb.tatil_bekor_qilish(),
        )
        return

    markup, sanalar = kb.tatil_boshlanish_sanalari()
    await state.update_data(boshlanish_variantlari=sanalar)
    await state.set_state(Tatil.boshlanish_tanlash)
    await message.answer(
        f"<b>🌴  Ta'til olish</b>\n"
        f"{CHIZIQ}\n"
        f"Ta'til qaysi kundan boshlanadi?",
        reply_markup=markup,
    )


@router.callback_query(Tatil.boshlanish_tanlash, F.data.startswith("tat_b:"))
async def boshlanish_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    boshlanish_iso = data["boshlanish_variantlari"][idx]
    boshlanish = date.fromisoformat(boshlanish_iso)

    markup, tugash_sanalari = kb.tatil_muddatlari(boshlanish)
    await state.update_data(boshlanish=boshlanish_iso, muddat_variantlari=tugash_sanalari)
    await state.set_state(Tatil.muddat_tanlash)
    await callback.message.edit_text(
        f"<b>🌴  Ta'til olish</b>\n"
        f"{CHIZIQ}\n"
        f"Boshlanish: <b>{sana_ozbekcha(boshlanish)}</b>\n\n"
        f"Qancha davom etadi?",
        reply_markup=markup,
    )


@router.callback_query(Tatil.muddat_tanlash, F.data.startswith("tat_m:"))
async def muddat_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    tugash_iso = data["muddat_variantlari"][idx]
    await state.update_data(tugash=tugash_iso)
    await _tasdiq_korsatish(callback.message, state, tahrirlash=True)


@router.callback_query(Tatil.muddat_tanlash, F.data == "tat_qolda")
async def qolda_sana_sorash(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Tatil.qolda_sana)
    await callback.message.edit_text(
        f"<b>📅  Qaytish sanasi</b>\n"
        f"{CHIZIQ}\n"
        f"Ta'til tugash sanasini yozing.\n\n"
        f"Namuna: <code>25.09.2026</code>"
    )


@router.message(Tatil.qolda_sana, ~F.text.in_(kb.MENYU_TUGMALARI))
async def qolda_sana_qabul(message: Message, state: FSMContext):
    d = _sanani_parse(message.text)
    if not d:
        await message.answer("Sana formati noto'g'ri.\nNamuna: <code>25.09.2026</code>")
        return

    data = await state.get_data()
    boshlanish_iso = data.get("boshlanish")
    if not boshlanish_iso:
        ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
        mavjud = ns.get_date_start(ustoz, "Ta'til boshlanishi") if ustoz else None
        if not mavjud:
            await message.answer("Xatolik yuz berdi. /start bilan qaytadan urinib ko'ring.")
            await state.clear()
            return
        boshlanish_iso = mavjud[:10]
        await state.update_data(boshlanish=boshlanish_iso)

    if d < date.fromisoformat(boshlanish_iso):
        await message.answer("Tugash sanasi boshlanish sanasidan oldin bo'lishi mumkin emas.")
        return

    await state.update_data(tugash=d.isoformat())
    await _tasdiq_korsatish(message, state, tahrirlash=False)


async def _tasdiq_korsatish(message: Message, state: FSMContext, tahrirlash: bool):
    data = await state.get_data()
    boshlanish = date.fromisoformat(data["boshlanish"])
    tugash = date.fromisoformat(data["tugash"])
    kunlar = (tugash - boshlanish).days + 1

    matn = (
        f"<b>🌴  Ta'tilni tasdiqlang</b>\n"
        f"{CHIZIQ}\n"
        f"Boshlanish:  <b>{sana_ozbekcha(boshlanish)}</b>\n"
        f"Tugash:  <b>{sana_ozbekcha(tugash)}</b>\n"
        f"Davomiyligi:  <b>{kunlar} kun</b>\n"
        f"{CHIZIQ}\n"
        f"Bu kunlardagi darslaringiz «Dars qoldirildi»\n"
        f"deb belgilanadi va eslatma yuborilmaydi."
    )
    await state.set_state(Tatil.tasdiq)
    if tahrirlash:
        await message.edit_text(matn, reply_markup=kb.tatil_tasdiq())
    else:
        await message.answer(matn, reply_markup=kb.tatil_tasdiq())


@router.callback_query(Tatil.tasdiq, F.data == "tat_cancel")
async def tatil_bekor(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("↩️  Bekor qilindi.")


@router.callback_query(Tatil.tasdiq, F.data == "tat_confirm")
async def tatil_tasdiqlash(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    boshlanish = data["boshlanish"]
    tugash = data["tugash"]

    await callback.answer("Saqlanmoqda...")
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    await ns.set_ustoz_tatil(ustoz["id"], boshlanish, tugash)

    bugun_sana = bugun()
    if date.fromisoformat(boshlanish) <= bugun_sana <= date.fromisoformat(tugash):
        await _bugungi_darslarni_qoldirish(ustoz["id"], bugun_sana.isoformat())

    ustoz_ismi = ns.get_title(ustoz, "Ism")
    await state.clear()
    await callback.message.edit_text(
        f"<b>🌴  Ta'til qabul qilindi</b>\n"
        f"{CHIZIQ}\n"
        f"{sana_qisqa(date.fromisoformat(boshlanish))} — "
        f"{sana_qisqa(date.fromisoformat(tugash))}\n\n"
        f"Yaxshi dam oling! 🌿"
    )
    await admin_xabar.yuborish(
                f"<b>🌴  Ustoz ta'tilga chiqdi</b>\n"
        f"{CHIZIQ}\n"
        f"Ustoz: {html_himoya(ustoz_ismi)}\n"
        f"Muddat: {sana_qisqa(date.fromisoformat(boshlanish))} — "
        f"{sana_qisqa(date.fromisoformat(tugash))}"
    , bot)


async def _bugungi_darslarni_qoldirish(ustoz_id: str, sana: str):
    """Faqat davomatli guruhlarga tegadi."""
    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz_id, davomatli_faqat=True)
    for g in guruhlar:
        grafik = await ns.get_grafik_yozuv(g["id"], sana)
        if grafik and ns.get_select(grafik, "Holat") == config.GRAFIK_DARS_OTILDI:
            continue
        if grafik:
            await ns.grafik_yangilash(grafik["id"], config.GRAFIK_DARS_QOLDIRILDI,
                                       sabab=config.SABAB_TATIL)
        else:
            await ns.grafik_yaratish(g["id"], sana, config.GRAFIK_DARS_QOLDIRILDI,
                                      sabab=config.SABAB_TATIL,
                                      guruh_nomi=ns.get_title(g, "Guruh nomi"))


@router.callback_query(F.data == "tat_bekor")
async def tatilni_erta_tugatish(callback: CallbackQuery, bot: Bot):
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    await ns.clear_ustoz_tatil(ustoz["id"])
    await callback.message.edit_text(
        f"<b>🔄  Ta'til bekor qilindi</b>\n"
        f"{CHIZIQ}\n"
        f"Kunlik eslatmalar tiklandi."
    )
    await admin_xabar.yuborish(
                f"🔄  {html_himoya(ns.get_title(ustoz, 'Ism'))} ta'tilini bekor qildi."
    , bot)


@router.callback_query(F.data == "tat_qaytdim")
async def tatildan_qaytish(callback: CallbackQuery):
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    await ns.clear_ustoz_tatil(ustoz["id"])
    await callback.message.edit_text(
        f"<b>✅  Xush kelibsiz!</b>\n"
        f"{CHIZIQ}\n"
        f"Ta'til tugatildi, eslatmalar tiklandi."
    )


@router.callback_query(F.data == "tat_uzaytirish")
async def tatilni_uzaytirish(callback: CallbackQuery, state: FSMContext):
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    mavjud = ns.get_date_start(ustoz, "Ta'til boshlanishi")
    tugash = ns.get_date_start(ustoz, "Ta'til tugashi")
    if not mavjud or not tugash:
        await callback.answer("Ta'til topilmadi.")
        return

    # Yangi muddat joriy tugash sanasidan boshlab sanaladi
    joriy_tugash = date.fromisoformat(tugash[:10])
    markup, tugash_sanalari = kb.tatil_muddatlari(joriy_tugash + timedelta(days=1))
    await state.update_data(boshlanish=mavjud[:10], muddat_variantlari=tugash_sanalari)
    await state.set_state(Tatil.muddat_tanlash)
    await callback.message.edit_text(
        f"<b>🌴  Ta'tilni uzaytirish</b>\n"
        f"{CHIZIQ}\n"
        f"Joriy tugash: {sana_ozbekcha(joriy_tugash)}\n\n"
        f"Yana qancha davom etadi?",
        reply_markup=markup,
    )
