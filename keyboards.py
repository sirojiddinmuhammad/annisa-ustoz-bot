# keyboards.py
# Barcha klaviaturalar shu yerda.
# Asosiy menyu — pastdagi doimiy klaviatura (ReplyKeyboard).
# Ichki oqimlar (guruh/sana tanlash, talabalar ro'yxati) — chat ichida (Inline).

from datetime import date, timedelta

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from utils import sana_ozbekcha

# --- Pastdagi doimiy menyu tugmalari (matn sifatida keladi) ---
BTN_DAVOMAT = "📋 Davomat"
BTN_DARS_QOLDIRISH = "🚫 Dars qoldirish"
BTN_TATIL = "🌴 Ta'til olish"
BTN_BUGUNGI = "📅 Bugungi darslar"
BTN_BALANS = "💰 Balansim"

# Matn kutayotgan handlerlar shu ro'yxatdagi matnlarni e'tiborsiz qoldirishi kerak,
# aks holda menyu tugmasi "sana" yoki "izoh" deb qabul qilinadi.
MENYU_TUGMALARI = [
    BTN_DAVOMAT, BTN_DARS_QOLDIRISH, BTN_TATIL, BTN_BUGUNGI, BTN_BALANS,
]


def asosiy_menyu() -> ReplyKeyboardMarkup:
    """Pastda doimiy turadigan menyu."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_DAVOMAT)],
            [KeyboardButton(text=BTN_DARS_QOLDIRISH), KeyboardButton(text=BTN_TATIL)],
            [KeyboardButton(text=BTN_BUGUNGI), KeyboardButton(text=BTN_BALANS)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Menyudan tanlang",
    )


def guruhlar_royxati(guruhlar: list[dict], prefix: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, g in enumerate(guruhlar):
        vaqt = g.get("vaqt")
        matn = f"📚 {g['nomi']}"
        if vaqt:
            matn += f"  ·  {vaqt}"
        kb.button(text=matn, callback_data=f"{prefix}_g:{i}")
    kb.adjust(1)
    return kb.as_markup()


def sanalar_royxati(sanalar: list[dict], prefix: str) -> InlineKeyboardMarkup:
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
    kb = InlineKeyboardBuilder()
    for i, t in enumerate(talabalar):
        belgi = HOLAT_BELGISI.get(t["holat"], "✅")
        matn = f"{belgi}  {t['ismi']}"
        if t.get("tatilda") and t["holat"] == config.HOLAT_SABABLI:
            matn = f"🟠  {t['ismi']} · ta'tilda"
        kb.button(text=matn, callback_data=f"dvm_t:{i}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="💾  Saqlash", callback_data="dvm_save"))
    return kb.as_markup()


def mavjud_yozuv_tanlovi() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️  Tahrirlash", callback_data="dvm_edit")
    kb.button(text="🗑  Davomatni o'chirish", callback_data="dvm_del")
    kb.adjust(1)
    return kb.as_markup()


def ochirish_tasdiq() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ha, o'chirilsin", callback_data="dvm_del_yes")
    kb.button(text="↩️ Bekor qilish", callback_data="dvm_del_no")
    kb.adjust(1)
    return kb.as_markup()


def sabablar_royxati(prefix: str = "dq") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    belgilar = {
        config.SABAB_KASALLIK: "🤒",
        config.SABAB_SAYOHAT: "✈️",
        config.SABAB_OILAVIY: "👨‍👩‍👧",
        config.SABAB_TEXNIK: "⚙️",
        config.SABAB_BOSHQA: "📝",
    }
    for i, s in enumerate(config.SABABLAR_RO_YXATI):
        kb.button(text=f"{belgilar.get(s, '•')}  {s}", callback_data=f"{prefix}_sabab:{i}")
    kb.adjust(1)
    return kb.as_markup()


def barcha_darslarni_qoldirish() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚫  Bugungi barcha darslarni qoldirish", callback_data="dq_hammasi")
    kb.adjust(1)
    return kb.as_markup()


# --- Ta'til uchun sana tanlash ---

def tatil_boshlanish_sanalari() -> tuple[InlineKeyboardMarkup, list[str]]:
    """7 kunlik ro'yxat. Qaytaradi: (klaviatura, sanalar_iso_royxati)"""
    kb = InlineKeyboardBuilder()
    sanalar = []
    bugun = date.today()
    for i in range(7):
        d = bugun + timedelta(days=i)
        sanalar.append(d.isoformat())
        if i == 0:
            label = f"Bugun · {d.day}-{_oy(d)}"
        elif i == 1:
            label = f"Ertaga · {d.day}-{_oy(d)}"
        else:
            label = sana_ozbekcha(d)
        kb.button(text=label, callback_data=f"tat_b:{i}")
    kb.adjust(1)
    return kb.as_markup(), sanalar


def tatil_muddatlari(boshlanish: date) -> tuple[InlineKeyboardMarkup, list[str]]:
    """Muddat tugmalari. Qaytaradi: (klaviatura, tugash_sanalari_iso)"""
    from utils import muddat_sanalari
    kb = InlineKeyboardBuilder()
    sanalar = []
    for i, m in enumerate(muddat_sanalari(boshlanish)):
        tugash = boshlanish + timedelta(days=m["kun"])
        sanalar.append(tugash.isoformat())
        kb.button(
            text=f"{m['label']} · {tugash.day}-{_oy(tugash)}gacha",
            callback_data=f"tat_m:{i}",
        )
    kb.button(text="📅  Boshqa muddat", callback_data="tat_qolda")
    kb.adjust(1)
    return kb.as_markup(), sanalar


def _oy(d: date) -> str:
    from utils import OYLAR
    return OYLAR[d.month - 1]


def tatil_tasdiq() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data="tat_confirm")
    kb.button(text="↩️ Bekor qilish", callback_data="tat_cancel")
    kb.adjust(1)
    return kb.as_markup()


def tatil_qaytish_sorovi() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Ha, qaytdim", callback_data="tat_qaytdim")
    kb.button(text="🌴 Ta'tilni uzaytiraman", callback_data="tat_uzaytirish")
    kb.adjust(1)
    return kb.as_markup()


def tatil_bekor_qilish() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄  Ta'tilni bekor qilish", callback_data="tat_bekor")
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
