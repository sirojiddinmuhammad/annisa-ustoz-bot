# handlers/admin_nomidan.py
# Admin ustoz nomidan ishlash rejimini yoqadi/o'chiradi.

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
import notion_service as ns
import keyboards as kb
import admin_rejim
from utils import html_himoya, CHIZIQ

router = Router()


class Nomidan(StatesGroup):
    ustoz_tanlash = State()


@router.message(Command("nomidan"))
async def boshlash(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return  # oddiy ustozlar uchun bu buyruq mavjud emas

    await state.clear()

    # Allaqachon rejimda bo'lsa — chiqishni taklif qilamiz
    if admin_rejim.rejimda_mi(message.from_user.id):
        malumot = admin_rejim.rejim_malumoti(message.from_user.id)
        await message.answer(
            f"👤  Siz hozir <b>{html_himoya(malumot['ismi'])}</b> nomidan ishlayapsiz.\n"
            f"{CHIZIQ}\n"
            f"Chiqish uchun /chiqish yozing."
        )
        return

    kutish = await message.answer("⏳  Ustozlar yuklanmoqda...")
    ustozlar = await ns.get_barcha_ustozlar_faol()
    if not ustozlar:
        await kutish.edit_text("📭  Ro'yxatdan o'tgan ustoz topilmadi.")
        return

    royxat = [
        {"id": u["id"], "ismi": ns.get_title(u, "Ism")}
        for u in ustozlar
    ]
    royxat.sort(key=lambda x: x["ismi"])

    await state.update_data(ustozlar=royxat)
    await state.set_state(Nomidan.ustoz_tanlash)
    await kutish.edit_text(
        f"<b>👤  Ustoz nomidan ishlash</b>\n"
        f"{CHIZIQ}\n"
        f"Kimning nomidan ishlaysiz?\n\n"
        f"<i>Bu rejimda siz o'sha ustozning guruhlarini ko'rasiz va\n"
        f"uning o'rniga ish bajara olasiz. Har bir o'zgarish haqida\n"
        f"ustozning o'ziga xabar boradi.</i>",
        reply_markup=kb.ustozlar_royxati(royxat),
    )


@router.callback_query(Nomidan.ustoz_tanlash, F.data.startswith("nom_u:"))
async def ustoz_tanlandi(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_ID:
        return

    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    tanlangan = data["ustozlar"][idx]

    ustoz = await ns.get_page(tanlangan["id"])
    admin_rejim.rejimni_yoqish(callback.from_user.id, ustoz)

    await state.clear()
    await callback.message.edit_text(
        f"<b>👤  {html_himoya(tanlangan['ismi'])} nomidan ishlayapsiz</b>\n"
        f"{CHIZIQ}\n"
        f"Menyudagi barcha tugmalar shu ustozning ma'lumotlari\n"
        f"bilan ishlaydi.\n\n"
        f"Chiqish uchun /chiqish yozing.",
        reply_markup=None,
    )


@router.callback_query(F.data == "nom_bekor")
async def bekor(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("↩️  Bekor qilindi.")


@router.message(Command("chiqish"))
async def chiqish(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return

    await state.clear()
    malumot = admin_rejim.rejimni_ochirish(message.from_user.id)
    if malumot:
        await message.answer(
            f"<b>🚪  Rejimdan chiqdingiz</b>\n"
            f"{CHIZIQ}\n"
            f"<b>{html_himoya(malumot['ismi'])}</b> nomidan ishlash tugatildi.",
            reply_markup=kb.asosiy_menyu(),
        )
    else:
        await message.answer("Siz hech kimning nomidan ishlamayapsiz.")
