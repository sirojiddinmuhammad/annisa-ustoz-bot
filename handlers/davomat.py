# handlers/davomat.py
# Davomat kiritish, tahrirlash va o'chirish — botning markaziy funksiyasi.

from datetime import date

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

import config
import notion_service as ns
import keyboards as kb
from states import Davomat
from utils import sana_ozbekcha, yaqin_kunlar, HAFTA_KUNLARI, markdown_himoya

router = Router()

HOLAT_KETMA_KET = [config.HOLAT_KELDI, config.HOLAT_KELMADI, config.HOLAT_SABABLI]


async def _ustoz_yoki_xato(callback: CallbackQuery):
    ustoz = await ns.find_ustoz_by_telegram_id(callback.from_user.id)
    if not ustoz:
        await callback.message.answer("Siz ro'yxatdan o'tmagansiz. /start ni bosing.")
        return None
    return ustoz


@router.callback_query(F.data == "menu_davomat")
async def davomat_boshlash(callback: CallbackQuery, state: FSMContext):
    ustoz = await _ustoz_yoki_xato(callback)
    if not ustoz:
        return
    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=True)
    if not guruhlar:
        await callback.message.edit_text("Sizda hozircha faol (davomatli) guruh yo'q.")
        return

    guruh_royxati = [{"id": g["id"], "nomi": ns.get_title(g, "Guruh nomi")} for g in guruhlar]
    await state.update_data(guruhlar=guruh_royxati)
    await state.set_state(Davomat.guruh_tanlash)
    await callback.message.edit_text(
        "Qaysi guruh?", reply_markup=kb.guruhlar_royxati(guruh_royxati, "dvm")
    )


@router.callback_query(Davomat.guruh_tanlash, F.data.startswith("dvm_g:"))
async def guruh_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    guruh = data["guruhlar"][idx]
    guruh_page = await ns.get_page(guruh["id"])

    dars_kunlari_nomlari = ns.get_multi_select(guruh_page, "Dars kunlari")
    dars_kunlari_idx = [HAFTA_KUNLARI.index(n) for n in dars_kunlari_nomlari if n in HAFTA_KUNLARI]
    if not dars_kunlari_idx:
        sanalar = yaqin_kunlar(list(range(7)), soni=4)  # aniqlanmagan bo'lsa oxirgi 4 kun
    else:
        sanalar = yaqin_kunlar(dars_kunlari_idx, soni=4)

    sana_royxati = [{"label": sana_ozbekcha(s), "value": s.isoformat()} for s in sanalar]
    await state.update_data(tanlangan_guruh=guruh, sanalar=sana_royxati)
    await state.set_state(Davomat.sana_tanlash)
    await callback.message.edit_text(
        f"Guruh: {guruh['nomi']}\nQaysi kun uchun?",
        reply_markup=kb.sanalar_royxati(sana_royxati, "dvm"),
    )


@router.callback_query(Davomat.sana_tanlash, F.data.startswith("dvm_s:"))
async def sana_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    sana = data["sanalar"][idx]["value"]
    guruh = data["tanlangan_guruh"]
    await state.update_data(tanlangan_sana=sana)
    await _davomat_ekranini_ochish(callback, state, guruh, sana)


async def _davomat_ekranini_ochish(callback: CallbackQuery, state: FSMContext, guruh: dict, sana: str):
    grafik = await ns.get_grafik_yozuv(guruh["id"], sana)
    allaqachon_bor = grafik and ns.get_select(grafik, "Holat") == config.GRAFIK_DARS_OTILDI

    if allaqachon_bor:
        await _mavjud_yozuvni_korsatish(callback, state, guruh, sana)
        return

    yozilishlar = await ns.get_guruh_yozilishlari(guruh["id"])
    talabalar = []
    for y in yozilishlar:
        talaba_id = ns.get_relation_ids(y, "Talaba")
        if not talaba_id:
            continue
        ismi = await ns.get_talaba_ismi(talaba_id[0])
        yozilish_holati = ns.get_select(y, "Holat")
        tatilda = yozilish_holati == config.YOZILISH_TATILDA
        talabalar.append({
            "yozilish_id": y["id"],
            "ismi": ismi,
            "holat": config.HOLAT_SABABLI if tatilda else config.HOLAT_KELDI,
            "tatilda": tatilda,
            "chegirmasi_bor": ns.yozilish_chegirmasi_bor_mi(y),
            "davomat_id": None,  # yangi yozuv
        })

    if not talabalar:
        await callback.message.edit_text("Bu guruhda faol talaba topilmadi.")
        return

    await state.update_data(talabalar=talabalar, rejim="yangi")
    await state.set_state(Davomat.royxat_korish)
    await callback.message.edit_text(
        f"📚 {guruh['nomi']}\n📅 {sana_ozbekcha(date.fromisoformat(sana))}\n\n"
        "Talabani bosib holatini o'zgartiring:",
        reply_markup=kb.davomat_royxati(talabalar),
    )


async def _mavjud_yozuvni_korsatish(callback: CallbackQuery, state: FSMContext, guruh: dict, sana: str):
    yozilishlar = await ns.get_guruh_yozilishlari(
        guruh["id"], holatlar=[config.YOZILISH_OQIYABDI, config.YOZILISH_TATILDA, config.YOZILISH_TUGATDI]
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

    await state.update_data(talabalar=talabalar, rejim="mavjud")
    await state.set_state(Davomat.mavjud_yozuv_korish)

    matn = (
        f"⚠️ {guruh['nomi']} guruhiga {sana_ozbekcha(date.fromisoformat(sana))} uchun "
        f"davomat allaqachon kiritilgan.\n\n"
        f"✅ Keldi: {hisob[config.HOLAT_KELDI]}   "
        f"❌ Kelmadi: {hisob[config.HOLAT_KELMADI]}   "
        f"🟠 Sababli: {hisob[config.HOLAT_SABABLI]}\n\n"
    )
    for t in talabalar:
        belgi = kb.HOLAT_BELGISI.get(t["holat"], "•")
        matn += f"{belgi} {t['ismi']}\n"
    matn += "\nNima qilasiz?"

    await callback.message.edit_text(matn, reply_markup=kb.mavjud_yozuv_tanlovi())


@router.callback_query(Davomat.mavjud_yozuv_korish, F.data == "dvm_edit")
async def tahrirlashga_otish(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(rejim="tahrirlash")
    await state.set_state(Davomat.royxat_korish)
    await callback.message.edit_text(
        "Holatlarni tahrirlang:", reply_markup=kb.davomat_royxati(data["talabalar"])
    )


@router.callback_query(Davomat.mavjud_yozuv_korish, F.data == "dvm_del")
async def ochirish_sorash(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    talabalar = data["talabalar"]
    if not talabalar:
        await callback.answer("Yozuv topilmadi.")
        return

    # Eng eski davomat yozuvini olib, muddatni tekshiramiz
    birinchi_id = talabalar[0]["davomat_id"]
    davomat_page = await ns.get_page(birinchi_id)
    if not ns.davomat_yaratilgan_vaqti_ok_mi(davomat_page):
        await callback.message.edit_text(
            f"Bu davomat {config.DAVOMAT_OCHIRISH_MUDDATI_KUN} kundan eski. "
            "O'zgartirish uchun adminga murojaat qiling."
        )
        await state.clear()
        return

    await callback.message.edit_text(
        "Rostdan ham bu kunning davomatini butunlay o'chirasizmi?\n"
        "Bu amalni qaytarib bo'lmaydi.",
        reply_markup=kb.ochirish_tasdiq(),
    )


@router.callback_query(F.data == "dvm_del_no")
async def ochirish_bekor(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Bekor qilindi. Hech narsa o'zgarmadi.")


@router.callback_query(F.data == "dvm_del_yes")
async def ochirish_tasdiqlandi(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    talabalar = data["talabalar"]
    guruh = data["tanlangan_guruh"]
    sana = data["tanlangan_sana"]

    davomat_sahifalari = [await ns.get_page(t["davomat_id"]) for t in talabalar]
    await ns.davomat_ochirish(davomat_sahifalari)
    await ns.grafik_belgilanmaganga_qaytarish(guruh["id"], sana)

    await state.clear()
    await callback.message.edit_text(
        f"🗑 {guruh['nomi']} guruhining {sana_ozbekcha(date.fromisoformat(sana))} "
        "kungi davomati o'chirildi."
    )


@router.callback_query(Davomat.royxat_korish, F.data.startswith("dvm_t:"))
async def holat_almashtirish(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    talabalar = data["talabalar"]
    joriy = talabalar[idx]["holat"]
    keyingi_idx = (HOLAT_KETMA_KET.index(joriy) + 1) % len(HOLAT_KETMA_KET)
    talabalar[idx]["holat"] = HOLAT_KETMA_KET[keyingi_idx]
    await state.update_data(talabalar=talabalar)
    await callback.message.edit_reply_markup(reply_markup=kb.davomat_royxati(talabalar))


@router.callback_query(Davomat.royxat_korish, F.data == "dvm_save")
async def davomat_saqlash(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    talabalar = data["talabalar"]
    guruh = data["tanlangan_guruh"]
    sana = data["tanlangan_sana"]
    guruh_page = await ns.get_page(guruh["id"])

    hisob = {config.HOLAT_KELDI: 0, config.HOLAT_KELMADI: 0, config.HOLAT_SABABLI: 0}
    dars_bolgan = False

    for t in talabalar:
        holat = t["holat"]
        hisob[holat] = hisob.get(holat, 0) + 1

        if holat in (config.HOLAT_KELDI, config.HOLAT_KELMADI):
            dars_bolgan = True

        # Ta'tildagi talaba kelib qolsa — adminga xabar
        if t["tatilda"] and holat != config.HOLAT_SABABLI:
            await bot.send_message(
                config.ADMIN_ID,
                f"ℹ️ {t['ismi']} ({guruh['nomi']}) ta'tilda edi, lekin "
                f"{sana_ozbekcha(date.fromisoformat(sana))} kuni "
                f"\"{holat}\" deb belgilandi."
            )

        qolda_summa = None
        qolda_ustoz_ulushi = None
        chegirma_id = None

        if holat in (config.HOLAT_KELDI, config.HOLAT_KELMADI) and t.get("chegirmasi_bor"):
            qolda_summa, qolda_ustoz_ulushi, chegirma_id = await _chegirma_hisobla(
                t["yozilish_id"], guruh_page, sana
            )

        if t.get("davomat_id"):
            await ns.davomat_holatini_yangilash(t["davomat_id"], holat)
            # Eslatma: tahrirlashda chegirma qayta hisoblanmaydi — mavjud
            # bog'lanish saqlanadi. Chegirma faqat yangi yozuvda qo'llanadi.
        else:
            await ns.davomat_yaratish(
                yozilish_id=t["yozilish_id"],
                talaba_ismi=t["ismi"],
                guruh_nomi=guruh["nomi"],
                sana=sana,
                holat=holat,
                qolda_summa=qolda_summa,
                qolda_ustoz_ulushi=qolda_ustoz_ulushi,
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

    matn = (
        "✅ Saqlandi!\n"
        f"📚 {guruh['nomi']}\n"
        f"📅 {sana_ozbekcha(date.fromisoformat(sana))}\n\n"
        f"✅ Keldi: {hisob[config.HOLAT_KELDI]}   "
        f"❌ Kelmadi: {hisob[config.HOLAT_KELMADI]}   "
        f"🟠 Sababli: {hisob[config.HOLAT_SABABLI]}\n\n"
    )
    for t in talabalar:
        belgi = kb.HOLAT_BELGISI.get(t["holat"], "•")
        matn += f"{belgi} {t['ismi']}\n"

    await callback.message.edit_text(matn)


async def _chegirma_hisobla(yozilish_id: str, guruh_page: dict, sana: str):
    """Qaytaradi: (qolda_summa, qolda_ustoz_ulushi, chegirma_id) yoki (None, None, None)"""
    chegirma = await ns.get_faol_chegirma(yozilish_id)
    if not chegirma:
        return None, None, None

    boshlanish = ns.get_date_start(chegirma, "Boshlanish sana")
    if boshlanish and sana < boshlanish[:10]:
        return None, None, None

    dars_soni_limit = ns.get_number(chegirma, "Dars soni") or 0
    joriy_soni = await ns.chegirmali_darslar_soni(chegirma["id"])
    if joriy_soni >= dars_soni_limit:
        # Limit allaqachon to'lgan — ehtiyot chorasi sifatida chegirmani tugatamiz
        await ns.chegirmani_tugat(chegirma["id"], sana)
        return None, None, None

    dars_narxi = ns.guruh_dars_narxi(guruh_page)
    ustoz_foiz = ns.guruh_ustoz_ulushi_foiz(guruh_page)
    chegirma_foiz = ns.get_number(chegirma, "Chegirma %") or 0
    kim_kotaradi = ns.get_select(chegirma, "Kim ko'taradi")

    talaba_toladi, ustoz_ulushi = ns.chegirmali_summa_hisobla(
        dars_narxi, ustoz_foiz, chegirma_foiz, kim_kotaradi
    )

    if joriy_soni + 1 >= dars_soni_limit:
        await ns.chegirmani_tugat(chegirma["id"], sana)

    return talaba_toladi, ustoz_ulushi, chegirma["id"]
