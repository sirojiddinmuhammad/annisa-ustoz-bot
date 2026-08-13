# handlers/tatil.py
# Ustozning o'zi ta'til olishi — barcha davomatli guruhlaridagi shu kunlar
# Darslar grafigida "Dars qoldirildi, sabab=Ta'til" bo'ladi.

import re
from datetime import date, timedelta

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import config
import notion_service as ns
import keyboards as kb
from states import Tatil
from utils import sana_ozbekcha, sana_qisqa, markdown_himoya

router = Router()

SANA_REGEX = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")


def _sanani_parse(matn: str) -> date | None:
    m = SANA_REGEX.match(matn.strip())
    if not m:
        return None
    kun, oy, yil = map(int, m.groups())
    try:
        return date(yil, oy, kun)
    except ValueError:
        return None


@router.callback_query(F.data == "menu_tatil")
async def tatil_boshlash(callback: CallbackQuery, state: FSMContext):
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    if not ustoz:
        await callback.message.answer("Siz ro'yxatdan o'tmagansiz. /start ni bosing.")
        return

    if ns.ustoz_tatilda_mi(ustoz, date.today()):
        tugash = ns.get_date_start(ustoz, "Ta'til tugashi")
        await callback.message.edit_text(
            f"Siz hozir ta'tildasiz (tugash sanasi: {tugash[:10]}).\n"
            "Erta qaytmoqchimisiz?",
            reply_markup=kb.tatil_bekor_qilish(),
        )
        return

    await state.set_state(Tatil.boshlanish_sana)
    await callback.message.edit_text(
        "Ta'til boshlanish sanasini kiriting (KK.OO.YYYY, masalan 15.08.2026):"
    )


@router.message(Tatil.boshlanish_sana)
async def boshlanish_qabul(message: Message, state: FSMContext):
    d = _sanani_parse(message.text)
    if not d:
        await message.answer("Sana formati noto'g'ri. Masalan: 15.08.2026")
        return
    await state.update_data(boshlanish=d.isoformat())
    await state.set_state(Tatil.tugash_sana)
    await message.answer("Ta'til tugash sanasini kiriting (KK.OO.YYYY):")


@router.message(Tatil.tugash_sana)
async def tugash_qabul(message: Message, state: FSMContext):
    d = _sanani_parse(message.text)
    if not d:
        await message.answer("Sana formati noto'g'ri. Masalan: 22.08.2026")
        return

    data = await state.get_data()
    boshlanish_str = data.get("boshlanish")
    if not boshlanish_str:
        # Ta'tilni uzaytirish oqimi — boshlanish sanasi Notiondagi mavjud yozuvdan olinadi
        ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
        boshlanish_str = ns.get_date_start(ustoz, "Ta'til boshlanishi")
        if not boshlanish_str:
            await message.answer("Xatolik: mavjud ta'til topilmadi. /start bilan qaytadan urinib ko'ring.")
            await state.clear()
            return
        await state.update_data(boshlanish=boshlanish_str[:10])
    boshlanish = date.fromisoformat(boshlanish_str[:10])
    if d < boshlanish:
        await message.answer("Tugash sanasi boshlanish sanasidan oldin bo'lishi mumkin emas.")
        return

    await state.update_data(tugash=d.isoformat())
    await state.set_state(Tatil.tasdiq)
    await message.answer(
        f"🌴 Ta'til: {sana_qisqa(boshlanish)} — {sana_qisqa(d)}\n\nTasdiqlaysizmi?",
        reply_markup=kb.tatil_tasdiq(),
    )


@router.callback_query(Tatil.tasdiq, F.data == "tat_cancel")
async def tatil_bekor(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Bekor qilindi.")


@router.callback_query(Tatil.tasdiq, F.data == "tat_confirm")
async def tatil_tasdiqlash(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    boshlanish = data["boshlanish"]
    tugash = data["tugash"]

    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    await ns.set_ustoz_tatil(ustoz["id"], boshlanish, tugash)

    # Bugun ta'til oralig'ida bo'lsa — bugungi darslarni qoldiramiz
    bugun = date.today()
    if date.fromisoformat(boshlanish) <= bugun <= date.fromisoformat(tugash):
        await _bugungi_darslarni_qoldirish(ustoz["id"], bugun.isoformat())

    ustoz_ismi = ns.get_title(ustoz, "Ism")
    await state.clear()
    await callback.message.edit_text(
        f"🌴 Ta'til qabul qilindi: {sana_qisqa(date.fromisoformat(boshlanish))} — "
        f"{sana_qisqa(date.fromisoformat(tugash))}"
    )
    await bot.send_message(
        config.ADMIN_ID,
        f"🌴 *Ustoz ta'tilga chiqdi*\n\n"
        f"Ustoz: {markdown_himoya(ustoz_ismi)}\n"
        f"Muddat: {markdown_himoya(sana_qisqa(date.fromisoformat(boshlanish)))} — "
        f"{markdown_himoya(sana_qisqa(date.fromisoformat(tugash)))}",
        parse_mode="MarkdownV2",
    )


async def _bugungi_darslarni_qoldirish(ustoz_id: str, sana: str):
    """Faqat davomatli guruhlarga tegadi (Taklif 4)."""
    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz_id, davomatli_faqat=True)
    for g in guruhlar:
        grafik = await ns.get_grafik_yozuv(g["id"], sana)
        if grafik and ns.get_select(grafik, "Holat") == config.GRAFIK_DARS_OTILDI:
            continue
        if grafik:
            await ns.grafik_yangilash(grafik["id"], config.GRAFIK_DARS_QOLDIRILDI, sabab=config.SABAB_TATIL)
        else:
            await ns.grafik_yaratish(g["id"], sana, config.GRAFIK_DARS_QOLDIRILDI, sabab=config.SABAB_TATIL)


@router.callback_query(F.data == "tat_bekor")
async def tatilni_erta_tugatish(callback: CallbackQuery):
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    await ns.clear_ustoz_tatil(ustoz["id"])
    await callback.message.edit_text("🔄 Ta'til bekor qilindi. Kunlik eslatmalar tiklandi.")


@router.callback_query(F.data == "tat_qaytdim")
async def tatildan_qaytish(callback: CallbackQuery):
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    await ns.clear_ustoz_tatil(ustoz["id"])
    await callback.message.edit_text("✅ Xush kelibsiz! Ta'til tugatildi.")


@router.callback_query(F.data == "tat_uzaytirish")
async def tatilni_uzaytirish_sorash(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Tatil.tugash_sana)
    await callback.message.edit_text("Yangi tugash sanasini kiriting (KK.OO.YYYY):")
    # Eslatma: bu holatda "boshlanish" state ma'lumotida yo'q, shuning uchun
    # tugash_qabul funksiyasi ustozning mavjud boshlanish sanasini Notiondan olishi kerak.
