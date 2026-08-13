# states.py
# Barcha suhbat bosqichlari (Finite State Machine) shu yerda tavsiflanadi.

from aiogram.fsm.state import State, StatesGroup


class RoyxatdanOtish(StatesGroup):
    ism_kutilmoqda = State()


class Davomat(StatesGroup):
    guruh_tanlash = State()
    sana_tanlash = State()
    royxat_korish = State()  # talabalar ro'yxati bilan davomat belgilash
    mavjud_yozuv_korish = State()  # allaqachon kiritilgan kun uchun tanlov ekrani


class DarsQoldirish(StatesGroup):
    guruh_tanlash = State()
    sana_tanlash = State()
    sabab_tanlash = State()
    izoh_kutilmoqda = State()


class Tatil(StatesGroup):
    boshlanish_sana = State()
    tugash_sana = State()
    tasdiq = State()


class BekorQilishTasdiq(StatesGroup):
    kutilmoqda = State()
