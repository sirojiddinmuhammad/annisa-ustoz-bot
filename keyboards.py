# keyboards.py
# Barcha inline klaviaturalar shu yerda yig'ilgan.
# Callback ma'lumotlar (guruh/yozilish id, sana) FSM xotirasida saqlanadi,
# tugmalarda faqat qisqa indeks yoki id ishlatiladi — Telegram callback_data
# uzunligi cheklangani uchun.

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config


def asosiy_menyu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Davomat", callback_data="menu_davomat")
    kb.button(text="🚫 Dars qoldirish", callback_data="menu_dars_qoldirish")
    kb.button(text="🌴 Ta'til olish", callback_data="menu_tatil")
    kb.button(text="📅 Bugungi darslar", callback_data="menu_bugungi")
    kb.button(text="💰 Balansim", callback_data="menu_balans")
    kb.adjust(1)
    return kb.as_markup()


def guruhlar_royxati(guruhlar: list[dict], prefix: str) -> InlineKeyboardMarkup:
    """guruhlar — [{"id": ..., "nomi": ...}, ...]"""
    kb = InlineKeyboardBuilder()
    for i, g in enumerate(guruhlar):
        kb.button(text=g["nomi"], callback_data=f"{prefix}_g:{i}")
    kb.adjust(1)
    return kb.as_markup()


def sanalar_royxati(sanalar: list[dict], prefix: str) -> InlineKeyboardMarkup:
    """sanalar — [{"label": "Payshanba, 7-avgust", "value": "2026-08-07"}, ...]"""
    kb = InlineKeyboardBuilder()
    for i, s in enumerate(sanalar):
        kb.button(text=s["label"], callback_data=f"{prefix}_s:{i}")
    kb.adjust(1)
    return kb.as_markup()


HOLAT_BELGISI = {
    config.HOLAT_KELDI: "✅",
    config.HOLAT_KELMADI: "❌",
    config.HOLAT_SABABLI: "🟠",
}


def davomat_royxati(talabalar: list[dict]) -> InlineKeyboardMarkup:
    """talabalar — [{"ismi": ..., "holat": ..., "tatilda": bool}, ...]"""
    kb = InlineKeyboardBuilder()
    for i, t in enumerate(talabalar):
        belgi = HOLAT_BELGISI.get(t["holat"], "✅")
        matn = f"{belgi} {t['ismi']}"
        if t.get("tatilda") and t["holat"] == config.HOLAT_SABABLI:
            matn = f"🟠 {t['ismi']} (ta'tilda)"
        kb.button(text=matn, callback_data=f"dvm_t:{i}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="💾 Saqlash", callback_data="dvm_save"))
    return kb.as_markup()


def mavjud_yozuv_tanlovi() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Tahrirlash", callback_data="dvm_edit")
    kb.button(text="🗑 Davomatni o'chirish", callback_data="dvm_del")
    kb.adjust(1)
    return kb.as_markup()


def ochirish_tasdiq() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ha, o'chirish", callback_data="dvm_del_yes")
    kb.button(text="❌ Yo'q, bekor", callback_data="dvm_del_no")
    kb.adjust(2)
    return kb.as_markup()


def sabablar_royxati(prefix: str = "dq") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, s in enumerate(config.SABABLAR_RO_YXATI):
        kb.button(text=s, callback_data=f"{prefix}_sabab:{i}")
    kb.adjust(1)
    return kb.as_markup()


def barcha_darslarni_qoldirish() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚫 Barcha darslarni qoldirish", callback_data="dq_hammasi")
    kb.adjust(1)
    return kb.as_markup()


def tatil_tasdiq() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data="tat_confirm")
    kb.button(text="❌ Bekor qilish", callback_data="tat_cancel")
    kb.adjust(2)
    return kb.as_markup()


def tatil_qaytish_sorovi() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ha, qaytdim", callback_data="tat_qaytdim")
    kb.button(text="🌴 Ta'tilni uzaytiraman", callback_data="tat_uzaytirish")
    kb.adjust(1)
    return kb.as_markup()


def tatil_bekor_qilish() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Ta'tilni bekor qilish", callback_data="tat_bekor")
    kb.adjust(1)
    return kb.as_markup()


def royxatdan_otish_tasdiq(ustoz_index: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"reg_ok:{ustoz_index}")
    kb.button(text="❌ Rad etish", callback_data="reg_no")
    kb.adjust(1)
    return kb.as_markup()


def royxatdan_otish_tanlov(soni: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in range(soni):
        kb.button(text=f"{i + 1}-variant", callback_data=f"reg_pick:{i}")
    kb.button(text="❌ Hech biri emas", callback_data="reg_no")
    kb.adjust(1)
    return kb.as_markup()
