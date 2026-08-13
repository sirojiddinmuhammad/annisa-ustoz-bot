# handlers/registration.py
# /start va ustozni ro'yxatdan o'tkazish (admin tasdig'i bilan).

import uuid

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import config
import notion_service as ns
import keyboards as kb
from states import RoyxatdanOtish
from utils import html_himoya, CHIZIQ

router = Router()

PENDING_REGISTRATIONS: dict[str, dict] = {}


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
    if ustoz:
        ism = ns.get_title(ustoz, "Ism")
        await message.answer(
            f"<b>Assalomu alaykum, {html_himoya(ism)}!</b>\n"
            f"{CHIZIQ}\n"
            f"📋  <b>Davomat</b> — dars davomatini kiritish\n"
            f"🚫  <b>Dars qoldirish</b> — dars bo'lmaganini belgilash\n"
            f"🌴  <b>Ta'til olish</b> — dam olish kunlarini belgilash\n"
            f"📅  <b>Bugungi darslar</b> — bugungi jadval\n"
            f"💰  <b>Balansim</b> — daromadingiz\n"
            f"{CHIZIQ}\n"
            f"Quyidagi menyudan tanlang 👇",
            reply_markup=kb.asosiy_menyu(),
        )
        return

    await message.answer(
        f"<b>Assalomu alaykum!</b>\n"
        f"{CHIZIQ}\n"
        f"Siz hali ro'yxatdan o'tmagansiz.\n\n"
        f"Markazdagi <b>to'liq ismingizni</b> yozing.\n"
        f"Notiondagi yozilishi bilan bir xil bo'lsin."
    )
    await state.set_state(RoyxatdanOtish.ism_kutilmoqda)


@router.message(RoyxatdanOtish.ism_kutilmoqda)
async def ism_qabul_qilish(message: Message, state: FSMContext, bot: Bot):
    ism = message.text.strip()
    nomzodlar = await ns.find_ustozlar_by_name(ism)
    await state.clear()

    req_id = uuid.uuid4().hex[:8]
    PENDING_REGISTRATIONS[req_id] = {
        "tg_id": message.from_user.id,
        "username": message.from_user.username or "yo'q",
        "ism_yozgan": ism,
        "nomzodlar": nomzodlar,
    }

    await message.answer(
        f"<b>⏳  So'rovingiz yuborildi</b>\n"
        f"{CHIZIQ}\n"
        f"Admin tasdiqlagach xabar beramiz."
    )

    matn = (
        f"<b>🆕  Ro'yxatdan o'tish so'rovi</b>\n"
        f"{CHIZIQ}\n"
        f"Yozgan ismi: <b>{html_himoya(ism)}</b>\n"
        f"Username: @{html_himoya(message.from_user.username or 'yoq')}\n"
        f"Telegram ID: <code>{message.from_user.id}</code>\n"
        f"{CHIZIQ}\n"
    )

    if not nomzodlar:
        matn += "❌  Notionda mos ustoz topilmadi."
        await bot.send_message(config.ADMIN_ID, matn,
                                reply_markup=kb.royxatdan_otish_tanlov(0))
        return

    if len(nomzodlar) == 1:
        matn += f"✅  Notionda topildi:\n<b>{html_himoya(ns.get_title(nomzodlar[0], 'Ism'))}</b>"
        await bot.send_message(config.ADMIN_ID, matn,
                                reply_markup=kb.royxatdan_otish_tasdiq(0))
    else:
        matn += "Bir nechta mos nomzod topildi:\n"
        for i, n in enumerate(nomzodlar):
            matn += f"{i + 1}.  {html_himoya(ns.get_title(n, 'Ism'))}\n"
        await bot.send_message(config.ADMIN_ID, matn,
                                reply_markup=kb.royxatdan_otish_tanlov(len(nomzodlar)))


def _oxirgi_pending():
    if not PENDING_REGISTRATIONS:
        return None, None
    req_id = list(PENDING_REGISTRATIONS.keys())[-1]
    return req_id, PENDING_REGISTRATIONS[req_id]


@router.callback_query(F.data.startswith("reg_pick:"))
async def nomzod_tanlash(callback: CallbackQuery, bot: Bot):
    idx = int(callback.data.split(":")[1])
    req_id, data = _oxirgi_pending()
    if not data:
        await callback.answer("So'rov topilmadi.")
        return
    await _tasdiqlash(data["nomzodlar"][idx], data, bot)
    del PENDING_REGISTRATIONS[req_id]
    await callback.message.edit_text(callback.message.html_text + "\n\n✅  Tasdiqlandi.")


@router.callback_query(F.data.startswith("reg_ok:"))
async def royxat_tasdiqlash(callback: CallbackQuery, bot: Bot):
    req_id, data = _oxirgi_pending()
    if not data:
        await callback.answer("So'rov topilmadi.")
        return
    await _tasdiqlash(data["nomzodlar"][0], data, bot)
    del PENDING_REGISTRATIONS[req_id]
    await callback.message.edit_text(callback.message.html_text + "\n\n✅  Tasdiqlandi.")


@router.callback_query(F.data == "reg_no")
async def royxat_rad_etish(callback: CallbackQuery, bot: Bot):
    req_id, data = _oxirgi_pending()
    if data:
        await bot.send_message(
            data["tg_id"],
            f"<b>❌  So'rov rad etildi</b>\n"
            f"{CHIZIQ}\n"
            f"Ismingizni to'g'ri yozib qayta urinib ko'ring\n"
            f"yoki markaz bilan bog'laning."
        )
        del PENDING_REGISTRATIONS[req_id]
    await callback.message.edit_text(callback.message.html_text + "\n\n❌  Rad etildi.")


async def _tasdiqlash(ustoz: dict, data: dict, bot: Bot):
    tg_id = data["tg_id"]
    await ns.clear_telegram_id_if_taken(tg_id)
    await ns.set_ustoz_telegram_id(ustoz["id"], tg_id)
    ism = ns.get_title(ustoz, "Ism")
    await bot.send_message(
        tg_id,
        f"<b>✅  Tabriklaymiz, {html_himoya(ism)}!</b>\n"
        f"{CHIZIQ}\n"
        f"Ro'yxatdan o'tishingiz tasdiqlandi.\n"
        f"Endi botdan foydalanishingiz mumkin.\n\n"
        f"Quyidagi menyudan tanlang 👇",
        reply_markup=kb.asosiy_menyu(),
    )
