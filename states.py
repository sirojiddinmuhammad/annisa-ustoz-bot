# states.py
# Barcha suhbat bosqichlari (Finite State Machine).

from aiogram.fsm.state import State, StatesGroup


class RoyxatdanOtish(StatesGroup):
    ism_kutilmoqda = State()


class Davomat(StatesGroup):
    guruh_tanlash = State()
    sana_tanlash = State()
    royxat_korish = State()
    mavjud_yozuv_korish = State()


class DarsQoldirish(StatesGroup):
    guruh_tanlash = State()
    sana_tanlash = State()
    sabab_tanlash = State()
    izoh_kutilmoqda = State()


class Tatil(StatesGroup):
    boshlanish_tanlash = State()
    muddat_tanlash = State()
    qolda_sana = State()
    tasdiq = State()


class BekorQilishTasdiq(StatesGroup):
    kutilmoqda = State()
