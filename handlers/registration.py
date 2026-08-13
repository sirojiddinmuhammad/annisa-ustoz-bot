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
from utils import markdown_himoya

router = Router()

# Tasdiq kutayotgan so'rovlar: {request_id: {...}}
# Eslatma: bot qayta ishga tushsa, kutayotgan so'rovlar tozalanadi.
PENDING_REGISTRATIONS: dict[str, dict] = {}


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
    if ustoz:
        ism = ns.get_title(ustoz, "Ism")
        await message.answer(
            f"Assalomu alaykum, {ism}! Xush kelibsiz.",
            reply_markup=kb.asosiy_menyu(),
        )
        return

    await message.answer(
        "Assalomu alaykum! Siz hali ro'yxatdan o'tmagansiz.\n\n"
        "Markazdagi to'liq ismingizni yozing (Notiondagi yozilishi bilan bir xil):"
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
        "So'rovingiz adminga yuborildi. Tasdiqlangach xabar beramiz."
    )

    matn = (
        f"🆕 *Yangi ro'yxatdan o'tish so'rovi*\n\n"
        f"Yozgan ismi: {markdown_himoya(ism)}\n"
        f"Username: @{markdown_himoya(message.from_user.username or 'yoq')}\n"
        f"Telegram ID: `{message.from_user.id}`\n\n"
    )

    if not nomzodlar:
        matn += "Notionda mos ustoz topilmadi\\."
        await bot.send_message(
            config.ADMIN_ID, matn, parse_mode="MarkdownV2",
            reply_markup=kb.royxatdan_otish_tanlov(0),
        )
        return

    if len(nomzodlar) == 1:
        matn += f"Notionda topildi: *{markdown_himoya(ns.get_title(nomzodlar[0], 'Ism'))}*"
        await bot.send_message(
            config.ADMIN_ID, matn, parse_mode="MarkdownV2",
            reply_markup=kb.royxatdan_otish_tasdiq(0),
        )
    else:
        matn += "Bir nechta mos nomzod topildi, to'g'risini tanlang:\n"
        for i, n in enumerate(nomzodlar):
            matn += f"{i + 1}\\. {markdown_himoya(ns.get_title(n, 'Ism'))}\n"
        await bot.send_message(
            config.ADMIN_ID, matn, parse_mode="MarkdownV2",
            reply_markup=kb.royxatdan_otish_tanlov(len(nomzodlar)),
        )

    # req_id ni oxirgi PENDING yozuvga bog'laymiz (oddiy holatda bitta faol so'rov)
    PENDING_REGISTRATIONS[req_id]["_req_id"] = req_id


async def _oxirgi_pending_topish() -> tuple[str, dict] | tuple[None, None]:
    if not PENDING_REGISTRATIONS:
        return None, None
    req_id = list(PENDING_REGISTRATIONS.keys())[-1]
    return req_id, PENDING_REGISTRATIONS[req_id]


@router.callback_query(F.data.startswith("reg_pick:"))
async def nomzod_tanlash(callback: CallbackQuery, bot: Bot):
    idx = int(callback.data.split(":")[1])
    req_id, data = await _oxirgi_pending_topish()
    if not data:
        await callback.answer("So'rov topilmadi.")
        return
    ustoz = data["nomzodlar"][idx]
    await _royxatni_tasdiqlash(ustoz, data, bot)
    del PENDING_REGISTRATIONS[req_id]
    await callback.message.edit_text(callback.message.text + "\n\n✅ Tasdiqlandi.")


@router.callback_query(F.data.startswith("reg_ok:"))
async def royxat_tasdiqlash(callback: CallbackQuery, bot: Bot):
    req_id, data = await _oxirgi_pending_topish()
    if not data:
        await callback.answer("So'rov topilmadi.")
        return
    ustoz = data["nomzodlar"][0]
    await _royxatni_tasdiqlash(ustoz, data, bot)
    del PENDING_REGISTRATIONS[req_id]
    await callback.message.edit_text(callback.message.text + "\n\n✅ Tasdiqlandi.")


@router.callback_query(F.data == "reg_no")
async def royxat_rad_etish(callback: CallbackQuery, bot: Bot):
    req_id, data = await _oxirgi_pending_topish()
    if data:
        await bot.send_message(
            data["tg_id"],
            "Kechirasiz, ro'yxatdan o'tish so'rovingiz rad etildi. "
            "Iltimos, ismingizni to'g'ri yozib qayta urinib ko'ring yoki markaz bilan bog'laning."
        )
        del PENDING_REGISTRATIONS[req_id]
    await callback.message.edit_text(callback.message.text + "\n\n❌ Rad etildi.")


async def _royxatni_tasdiqlash(ustoz: dict, data: dict, bot: Bot):
    tg_id = data["tg_id"]
    await ns.clear_telegram_id_if_taken(tg_id)
    await ns.set_ustoz_telegram_id(ustoz["id"], tg_id)
    ism = ns.get_title(ustoz, "Ism")
    await bot.send_message(
        tg_id,
        f"Tabriklaymiz, {ism}! Ro'yxatdan o'tishingiz tasdiqlandi.",
        reply_markup=kb.asosiy_menyu(),
    )
