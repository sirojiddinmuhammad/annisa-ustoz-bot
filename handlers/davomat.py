# handlers/davomat.py
# Davomat kiritish, tahrirlash va o'chirish — botning markaziy funksiyasi.

from datetime import date

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import config
import notion_service as ns
import keyboards as kb
from states import Davomat
from utils import sana_ozbekcha, yaqin_kunlar, HAFTA_KUNLARI, html_himoya, CHIZIQ

router = Router()

HOLAT_KETMA_KET = [config.HOLAT_KELDI, config.HOLAT_KELMADI, config.HOLAT_SABABLI]


@router.message(F.text == kb.BTN_DAVOMAT)
async def davomat_boshlash(message: Message, state: FSMContext):
    await state.clear()
    ustoz = await ns.find_ustoz_by_telegram_id(message.from_user.id)
    if not ustoz:
        await message.answer("Siz hali ro'yxatdan o'tmagansiz.\n/start ni bosing.")
        return

    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=True)
    if not guruhlar:
        await message.answer("📭  Sizda hozircha faol guruh yo'q.")
        return

    guruh_royxati = [{"id": g["id"], "nomi": ns.get_title(g, "Guruh nomi")} for g in guruhlar]
    await state.update_data(guruhlar=guruh_royxati)
    await state.set_state(Davomat.guruh_tanlash)
    await message.answer(
        "<b>📋  Davomat</b>\n"
        f"{CHIZIQ}\n"
        "Qaysi guruhga davomat kiritasiz?",
        reply_markup=kb.guruhlar_royxati(guruh_royxati, "dvm"),
    )


@router.callback_query(Davomat.guruh_tanlash, F.data.startswith("dvm_g:"))
async def guruh_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    guruh = data["guruhlar"][idx]
    guruh_page = await ns.get_page(guruh["id"])

    kunlari = [HAFTA_KUNLARI.index(n) for n in ns.get_multi_select(guruh_page, "Dars kunlari")
               if n in HAFTA_KUNLARI]
    sanalar = yaqin_kunlar(kunlari or list(range(7)), soni=4)

    sana_royxati = [{"label": sana_ozbekcha(s), "value": s.isoformat()} for s in sanalar]
    await state.update_data(tanlangan_guruh=guruh, sanalar=sana_royxati)
    await state.set_state(Davomat.sana_tanlash)
    await callback.message.edit_text(
        f"<b>📚  {html_himoya(guruh['nomi'])}</b>\n"
        f"{CHIZIQ}\n"
        "Qaysi kun uchun?",
        reply_markup=kb.sanalar_royxati(sana_royxati, "dvm"),
    )


@router.callback_query(Davomat.sana_tanlash, F.data.startswith("dvm_s:"))
async def sana_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    sana = data["sanalar"][idx]["value"]
    guruh = data["tanlangan_guruh"]
    await state.update_data(tanlangan_sana=sana)
    await callback.answer("Yuklanmoqda...")
    await _davomat_ekranini_ochish(callback, state, guruh, sana)


async def _davomat_ekranini_ochish(callback: CallbackQuery, state: FSMContext,
                                     guruh: dict, sana: str):
    grafik = await ns.get_grafik_yozuv(guruh["id"], sana)
    if grafik and ns.get_select(grafik, "Holat") == config.GRAFIK_DARS_OTILDI:
        await _mavjud_yozuvni_korsatish(callback, state, guruh, sana)
        return

    yozilishlar = await ns.get_guruh_yozilishlari(guruh["id"])
    talabalar = []
    for y in yozilishlar:
        talaba_id = ns.get_relation_ids(y, "Talaba")
        if not talaba_id:
            continue
        ismi = await ns.get_talaba_ismi(talaba_id[0])
        tatilda = ns.get_select(y, "Holat") == config.YOZILISH_TATILDA
        talabalar.append({
            "yozilish_id": y["id"],
            "ismi": ismi,
            "holat": config.HOLAT_SABABLI if tatilda else config.HOLAT_KELDI,
            "tatilda": tatilda,
            "chegirmasi_bor": ns.yozilish_chegirmasi_bor_mi(y),
            "davomat_id": None,
        })

    if not talabalar:
        await callback.message.edit_text("📭  Bu guruhda faol talaba topilmadi.")
        await state.clear()
        return

    # Ta'tildagilar pastda tursin
    talabalar.sort(key=lambda t: t["tatilda"])

    await state.update_data(talabalar=talabalar)
    await state.set_state(Davomat.royxat_korish)
    await callback.message.edit_text(_royxat_matni(guruh, sana, len(talabalar)),
                                      reply_markup=kb.davomat_royxati(talabalar))


def _royxat_matni(guruh: dict, sana: str, soni: int) -> str:
    return (
        f"<b>📚  {html_himoya(guruh['nomi'])}</b>\n"
        f"📅  {sana_ozbekcha(date.fromisoformat(sana))}\n"
        f"{CHIZIQ}\n"
        f"<b>Qanday ishlaydi</b>\n"
        f"Ism ustiga bosing — holat almashadi:\n"
        f"✅ Keldi  →  ❌ Kelmadi  →  🟠 Sababli\n\n"
        f"Boshida hamma <b>✅ Keldi</b> turadi.\n"
        f"Faqat kelmaganlarni belgilang.\n"
        f"{CHIZIQ}\n"
        f"👥  Jami: {soni} ta talaba"
    )


async def _mavjud_yozuvni_korsatish(callback: CallbackQuery, state: FSMContext,
                                      guruh: dict, sana: str):
    yozilishlar = await ns.get_guruh_yozilishlari(
        guruh["id"],
        holatlar=[config.YOZILISH_OQIYABDI, config.YOZILISH_TATILDA, config.YOZILISH_TUGATDI],
    )
    talabalar = []
    hisob = {config.HOLAT_KELDI: 0, config.HOLAT_KELMADI: 0, config.HOLAT_SABABLI: 0}
    for y in yozilishlar:
        davomat = await ns.get_davomat_yozuv(y["id"], sana)
        if not davomat:
            continue
        talaba_id = ns.get_relation_ids(y, "Talaba")
        ismi = await ns.get_talaba_ismi(talaba_id[0]) if talaba_id else "?"
        holat = ns.get_select(davomat, "Holat")
        if holat in hisob:
            hisob[holat] += 1
        talabalar.append({
            "yozilish_id": y["id"],
            "ismi": ismi,
            "holat": holat,
            "tatilda": ns.get_select(y, "Holat") == config.YOZILISH_TATILDA,
            "chegirmasi_bor": ns.yozilish_chegirmasi_bor_mi(y),
            "davomat_id": davomat["id"],
        })

    await state.update_data(talabalar=talabalar)
    await state.set_state(Davomat.mavjud_yozuv_korish)

    matn = (
        f"<b>⚠️  Davomat allaqachon kiritilgan</b>\n"
        f"{CHIZIQ}\n"
        f"📚  {html_himoya(guruh['nomi'])}\n"
        f"📅  {sana_ozbekcha(date.fromisoformat(sana))}\n\n"
        f"✅ {hisob[config.HOLAT_KELDI]}   "
        f"❌ {hisob[config.HOLAT_KELMADI]}   "
        f"🟠 {hisob[config.HOLAT_SABABLI]}\n"
        f"{CHIZIQ}\n"
    )
    for t in talabalar:
        belgi = kb.HOLAT_BELGISI.get(t["holat"], "•")
        matn += f"{belgi}  {html_himoya(t['ismi'])}\n"
    matn += f"{CHIZIQ}\nNima qilamiz?"

    await callback.message.edit_text(matn, reply_markup=kb.mavjud_yozuv_tanlovi())


@router.callback_query(Davomat.mavjud_yozuv_korish, F.data == "dvm_edit")
async def tahrirlashga_otish(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    guruh = data["tanlangan_guruh"]
    sana = data["tanlangan_sana"]
    await state.set_state(Davomat.royxat_korish)
    await callback.message.edit_text(
        f"<b>✏️  Tahrirlash</b>\n"
        f"{CHIZIQ}\n"
        f"📚  {html_himoya(guruh['nomi'])}\n"
        f"📅  {sana_ozbekcha(date.fromisoformat(sana))}\n\n"
        f"Ism ustiga bosib holatni o'zgartiring,\n"
        f"so'ng <b>Saqlash</b> ni bosing.",
        reply_markup=kb.davomat_royxati(data["talabalar"]),
    )


@router.callback_query(Davomat.mavjud_yozuv_korish, F.data == "dvm_del")
async def ochirish_sorash(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    talabalar = data["talabalar"]
    if not talabalar:
        await callback.answer("Yozuv topilmadi.")
        return

    davomat_page = await ns.get_page(talabalar[0]["davomat_id"])
    if not ns.davomat_yaratilgan_vaqti_ok_mi(davomat_page):
        await callback.message.edit_text(
            f"<b>🔒  O'chirib bo'lmaydi</b>\n"
            f"{CHIZIQ}\n"
            f"Bu davomat {config.DAVOMAT_OCHIRISH_MUDDATI_KUN} kundan eski.\n"
            f"O'zgartirish uchun adminga murojaat qiling."
        )
        await state.clear()
        return

    await callback.message.edit_text(
        f"<b>🗑  Davomatni o'chirish</b>\n"
        f"{CHIZIQ}\n"
        f"Bu kunning barcha davomat yozuvlari o'chiriladi.\n"
        f"Dars holati «Belgilanmagan» ga qaytadi.\n\n"
        f"Rostdan davom etamizmi?",
        reply_markup=kb.ochirish_tasdiq(),
    )


@router.callback_query(F.data == "dvm_del_no")
async def ochirish_bekor(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("↩️  Bekor qilindi. Hech narsa o'zgarmadi.")


@router.callback_query(F.data == "dvm_del_yes")
async def ochirish_tasdiqlandi(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    talabalar = data["talabalar"]
    guruh = data["tanlangan_guruh"]
    sana = data["tanlangan_sana"]

    await callback.answer("O'chirilmoqda...")
    davomat_sahifalari = [await ns.get_page(t["davomat_id"]) for t in talabalar]
    await ns.davomat_ochirish(davomat_sahifalari)
    await ns.grafik_belgilanmaganga_qaytarish(guruh["id"], sana)

    await state.clear()
    await callback.message.edit_text(
        f"<b>🗑  O'chirildi</b>\n"
        f"{CHIZIQ}\n"
        f"📚  {html_himoya(guruh['nomi'])}\n"
        f"📅  {sana_ozbekcha(date.fromisoformat(sana))}"
    )


@router.callback_query(Davomat.royxat_korish, F.data.startswith("dvm_t:"))
async def holat_almashtirish(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    talabalar = data["talabalar"]
    joriy = talabalar[idx]["holat"]
    keyingi = (HOLAT_KETMA_KET.index(joriy) + 1) % len(HOLAT_KETMA_KET)
    talabalar[idx]["holat"] = HOLAT_KETMA_KET[keyingi]
    await state.update_data(talabalar=talabalar)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=kb.davomat_royxati(talabalar))


@router.callback_query(Davomat.royxat_korish, F.data == "dvm_save")
async def davomat_saqlash(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    talabalar = data["talabalar"]
    guruh = data["tanlangan_guruh"]
    sana = data["tanlangan_sana"]
    guruh_page = await ns.get_page(guruh["id"])

    await callback.answer("Saqlanmoqda...")
    await callback.message.edit_text("⏳  Saqlanmoqda, biroz kuting...")

    hisob = {config.HOLAT_KELDI: 0, config.HOLAT_KELMADI: 0, config.HOLAT_SABABLI: 0}
    dars_bolgan = False

    for t in talabalar:
        holat = t["holat"]
        hisob[holat] = hisob.get(holat, 0) + 1

        if holat in (config.HOLAT_KELDI, config.HOLAT_KELMADI):
            dars_bolgan = True

        if t["tatilda"] and holat != config.HOLAT_SABABLI:
            await bot.send_message(
                config.ADMIN_ID,
                f"ℹ️  <b>Ta'tildagi talaba darsga keldi</b>\n"
                f"{CHIZIQ}\n"
                f"Talaba: {html_himoya(t['ismi'])}\n"
                f"Guruh: {html_himoya(guruh['nomi'])}\n"
                f"Sana: {sana_ozbekcha(date.fromisoformat(sana))}\n"
                f"Belgilandi: {holat}"
            )

        qolda_summa = qolda_ustoz = chegirma_id = None
        if holat in (config.HOLAT_KELDI, config.HOLAT_KELMADI) and t.get("chegirmasi_bor"):
            qolda_summa, qolda_ustoz, chegirma_id = await _chegirma_hisobla(
                t["yozilish_id"], guruh_page, sana
            )

        if t.get("davomat_id"):
            await ns.davomat_holatini_yangilash(t["davomat_id"], holat)
        else:
            await ns.davomat_yaratish(
                yozilish_id=t["yozilish_id"], talaba_ismi=t["ismi"],
                guruh_nomi=guruh["nomi"], sana=sana, holat=holat,
                qolda_summa=qolda_summa, qolda_ustoz_ulushi=qolda_ustoz,
                chegirma_id=chegirma_id,
            )

    if dars_bolgan:
        dars_raqami = await ns.keyingi_dars_raqami(guruh["id"])
        grafik = await ns.get_grafik_yozuv(guruh["id"], sana)
        if grafik:
            await ns.grafik_yangilash(grafik["id"], config.GRAFIK_DARS_OTILDI, dars_raqami)
        else:
            await ns.grafik_yaratish(guruh["id"], sana, config.GRAFIK_DARS_OTILDI, dars_raqami)

    await state.clear()

    # 1-xabar: ustozga tasdiq
    await callback.message.edit_text(
        f"<b>✅  Saqlandi</b>\n"
        f"{CHIZIQ}\n"
        f"📚  {html_himoya(guruh['nomi'])}\n"
        f"📅  {sana_ozbekcha(date.fromisoformat(sana))}\n\n"
        f"👇  Quyidagi xabarni guruhga yuborishingiz mumkin."
    )

    # 2-xabar: guruhga repost uchun toza hisobot
    hisobot = (
        f"<b>📚  {html_himoya(guruh['nomi'])}</b>\n"
        f"📅  {sana_ozbekcha(date.fromisoformat(sana))}\n"
        f"{CHIZIQ}\n"
    )
    for t in talabalar:
        belgi = kb.HOLAT_BELGISI.get(t["holat"], "•")
        hisobot += f"{belgi}  {html_himoya(t['ismi'])}\n"
    hisobot += (
        f"{CHIZIQ}\n"
        f"✅ Keldi: {hisob[config.HOLAT_KELDI]}   "
        f"❌ Kelmadi: {hisob[config.HOLAT_KELMADI]}   "
        f"🟠 Sababli: {hisob[config.HOLAT_SABABLI]}"
    )
    await callback.message.answer(hisobot)


async def _chegirma_hisobla(yozilish_id: str, guruh_page: dict, sana: str):
    chegirma = await ns.get_faol_chegirma(yozilish_id)
    if not chegirma:
        return None, None, None

    boshlanish = ns.get_date_start(chegirma, "Boshlanish sana")
    if boshlanish and sana < boshlanish[:10]:
        return None, None, None

    limit = ns.get_number(chegirma, "Dars soni") or 0
    joriy = await ns.chegirmali_darslar_soni(chegirma["id"])
    if joriy >= limit:
        await ns.chegirmani_tugat(chegirma["id"], sana)
        return None, None, None

    talaba_toladi, ustoz_ulushi = ns.chegirmali_summa_hisobla(
        ns.guruh_dars_narxi(guruh_page),
        ns.guruh_ustoz_ulushi_foiz(guruh_page),
        ns.get_number(chegirma, "Chegirma %") or 0,
        ns.get_select(chegirma, "Kim ko'taradi"),
    )

    if joriy + 1 >= limit:
        await ns.chegirmani_tugat(chegirma["id"], sana)

    return talaba_toladi, ustoz_ulushi, chegirma["id"]
