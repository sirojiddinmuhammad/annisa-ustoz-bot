# handlers/talaba_chiqarish.py
# Talabani guruhdan chiqarish.
#
# Muammo: ustoz talabani og'zaki chiqarib yuborsa, Yozilish hamon "O'qiyabdi"
# bo'lib qoladi. Talaba davomat ro'yxatida chiqaveradi va "Darsga kelmadi"
# deb belgilanadi — bu esa pul yechilishini anglatadi. Natijada allaqachon
# ketgan talabaning balansi minusga ketib boraveradi.
#
# Yechim: ustoz botdan chiqarsa, Yozilish "Tugatdi" ga o'tadi va talaba
# ro'yxatdan yo'qoladi.

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
import notion_service as ns
import keyboards as kb
from utils import bugun, html_himoya, CHIZIQ, sana_qisqa

router = Router()


class Chiqarish(StatesGroup):
    guruh_tanlash = State()
    talaba_tanlash = State()
    sabab_kutilmoqda = State()
    tasdiq = State()


@router.message(F.text == kb.BTN_CHIQARISH)
async def boshlash(message: Message, state: FSMContext):
    await state.clear()
    ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
    if not ustoz:
        await message.answer("Siz hali ro'yxatdan o'tmagansiz.\n/start ni bosing.")
        return

    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=False)
    if not guruhlar:
        await message.answer("📭  Sizda hozircha faol guruh yo'q.")
        return

    guruh_royxati = [
        {"id": g["id"], "nomi": ns.get_title(g, "Guruh nomi"),
         "vaqt": ns.get_select(g, "Dars vaqti")}
        for g in guruhlar
    ]
    await state.update_data(guruhlar=guruh_royxati, ustoz_id=ustoz["id"],
                             ustoz_ismi=ns.get_title(ustoz, "Ism"))
    await state.set_state(Chiqarish.guruh_tanlash)
    await message.answer(
        f"<b>🚪  Talabani chiqarish</b>\n"
        f"{CHIZIQ}\n"
        f"Talaba guruhdan chiqarilsa, davomat ro'yxatida\n"
        f"ko'rinmaydi va undan pul yechilmaydi.\n\n"
        f"Qaysi guruhdan?",
        reply_markup=kb.guruhlar_royxati(guruh_royxati, "chq"),
    )


@router.callback_query(Chiqarish.guruh_tanlash, F.data.startswith("chq_g:"))
async def guruh_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    guruh = data["guruhlar"][idx]

    await callback.answer("Yuklanmoqda...")
    yozilishlar = await ns.get_guruh_yozilishlari(guruh["id"])

    talabalar = []
    for y in yozilishlar:
        talaba_ids = ns.get_relation_ids(y, "Talaba")
        if not talaba_ids:
            continue
        talabalar.append({
            "yozilish_id": y["id"],
            "talaba_id": talaba_ids[0],
            "ismi": await ns.get_talaba_ismi(talaba_ids[0]),
        })

    if not talabalar:
        await callback.message.edit_text("📭  Bu guruhda faol talaba topilmadi.")
        await state.clear()
        return

    await state.update_data(tanlangan_guruh=guruh, talabalar=talabalar)
    await state.set_state(Chiqarish.talaba_tanlash)
    await callback.message.edit_text(
        f"<b>🚪  Talabani chiqarish</b>\n"
        f"{CHIZIQ}\n"
        f"📚  {html_himoya(guruh['nomi'])}\n\n"
        f"Kimni chiqaramiz?",
        reply_markup=kb.chiqarish_talabalar(talabalar),
    )


@router.callback_query(Chiqarish.talaba_tanlash, F.data.startswith("chq_t:"))
async def talaba_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    talaba = data["talabalar"][idx]

    await state.update_data(tanlangan_talaba=talaba)
    await state.set_state(Chiqarish.sabab_kutilmoqda)
    await callback.message.edit_text(
        f"<b>🚪  Talabani chiqarish</b>\n"
        f"{CHIZIQ}\n"
        f"👤  {html_himoya(talaba['ismi'])}\n"
        f"📚  {html_himoya(data['tanlangan_guruh']['nomi'])}\n\n"
        f"Sababini yozing.\n"
        f"<i>Masalan: darsga kelmayapti, boshqa shaharga ko'chdi</i>"
    )


@router.message(Chiqarish.sabab_kutilmoqda, ~F.text.in_(kb.MENYU_TUGMALARI))
async def sabab_qabul(message: Message, state: FSMContext):
    sabab = (message.text or "").strip()
    if len(sabab) < 3:
        await message.answer("Sababni biroz to'liqroq yozing.")
        return

    data = await state.get_data()
    talaba = data["tanlangan_talaba"]
    guruh = data["tanlangan_guruh"]

    await state.update_data(sabab=sabab)
    await state.set_state(Chiqarish.tasdiq)
    await message.answer(
        f"<b>🚪  Tasdiqlang</b>\n"
        f"{CHIZIQ}\n"
        f"👤  {html_himoya(talaba['ismi'])}\n"
        f"📚  {html_himoya(guruh['nomi'])}\n"
        f"📝  {html_himoya(sabab)}\n"
        f"{CHIZIQ}\n"
        f"Talaba shu guruhdan chiqariladi va davomat\n"
        f"ro'yxatida boshqa ko'rinmaydi.\n\n"
        f"Davom etamizmi?",
        reply_markup=kb.chiqarish_tasdiq(),
    )


@router.callback_query(F.data == "chq_cancel")
async def bekor(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("↩️  Bekor qilindi. Hech narsa o'zgarmadi.")


@router.callback_query(Chiqarish.tasdiq, F.data == "chq_yes")
async def tasdiqlandi(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    talaba = data["tanlangan_talaba"]
    guruh = data["tanlangan_guruh"]
    sabab = data["sabab"]
    ustoz_ismi = data["ustoz_ismi"]
    sana = bugun().isoformat()

    await callback.answer("Bajarilmoqda...")
    await ns.yozilishni_yopish(talaba["yozilish_id"], sana, sabab, ustoz_ismi)

    await state.clear()
    await callback.message.edit_text(
        f"<b>✅  Chiqarildi</b>\n"
        f"{CHIZIQ}\n"
        f"👤  {html_himoya(talaba['ismi'])}\n"
        f"📚  {html_himoya(guruh['nomi'])}\n"
        f"📅  {sana_qisqa(bugun())}\n\n"
        f"Talaba endi davomat ro'yxatida ko'rinmaydi."
    )

    # Adminga xabar — balansni ham qo'shishga urinamiz
    balans_matni = await _balans_matni(talaba["talaba_id"])
    await bot.send_message(
        config.ADMIN_ID,
        f"<b>🚪  Talaba guruhdan chiqarildi</b>\n"
        f"{CHIZIQ}\n"
        f"Talaba: {html_himoya(talaba['ismi'])}\n"
        f"Guruh: {html_himoya(guruh['nomi'])}\n"
        f"Ustoz: {html_himoya(ustoz_ismi)}\n"
        f"Sana: {sana_qisqa(bugun())}\n"
        f"Sabab: {html_himoya(sabab)}\n"
        f"{CHIZIQ}\n"
        f"{balans_matni}"
    )


async def _balans_matni(talaba_id: str) -> str:
    """Talaba balansi. Notionda "Balans" — formula, API uni ba'zan o'qiy
    olmaydi ("omitted"). Shunday holatda ogohlantirish beramiz, chunki
    chiqarilgan talabaning qarzi yoki ortiqcha puli qolgan bo'lishi mumkin."""
    try:
        sahifa = await ns.get_page(talaba_id)
        balans = ns.get_number(sahifa, "Balans")
        if balans is None:
            return "💰  Balansni Notionda tekshiring."
        belgi = "🔴" if balans < 0 else "🟢"
        return f"{belgi}  Balans: {int(round(balans)):,}".replace(",", " ") + " so'm"
    except Exception:
        return "💰  Balansni Notionda tekshiring."
