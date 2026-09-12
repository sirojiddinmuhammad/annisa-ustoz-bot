# scheduler.py
# Kunlik avtomatik vazifalar: 02:20 ertalabki eslatma, 23:00 kunlik hisobot,
# oylik hisob (davomatsiz guruhlar) va ta'til nazorati.

import calendar
from datetime import date, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config
import notion_service as ns
import admin_xabar
import keyboards as kb
from utils import (sana_ozbekcha, html_himoya, CHIZIQ,
                   dars_kunlari_raqamga, vaqt_tartibi, bugun,
                   belgilanmagan_royxat_matni)


def sozlash(scheduler: AsyncIOScheduler, bot: Bot):
    scheduler.add_job(
        ertalabki_eslatma, CronTrigger(
            hour=config.ERTALABKI_ESLATMA_SOAT,
            minute=config.ERTALABKI_ESLATMA_DAQIQA,
            timezone=config.TASHKENT_TZ,
        ), kwargs={"bot": bot}, id="ertalabki_eslatma",
    )
    scheduler.add_job(
        kunlik_hisobot, CronTrigger(
            hour=config.KUNLIK_HISOBOT_SOAT,
            minute=config.KUNLIK_HISOBOT_DAQIQA,
            timezone=config.TASHKENT_TZ,
        ), kwargs={"bot": bot}, id="kunlik_hisobot",
    )
    scheduler.add_job(
        tatil_nazorati, CronTrigger(
            hour=config.ERTALABKI_ESLATMA_SOAT,
            minute=config.ERTALABKI_ESLATMA_DAQIQA + 5,
            timezone=config.TASHKENT_TZ,
        ), kwargs={"bot": bot}, id="tatil_nazorati",
    )


async def ertalabki_eslatma(bot: Bot):
    """Har kuni 02:20: bugungi darslar uchun Belgilanmagan ochadi,
    ustozlarga eslatma yuboradi, oylik hisobni tekshiradi."""
    bugun_sana = bugun()
    bugun_iso = bugun_sana.isoformat()
    bugungi_kun_idx = bugun_sana.weekday()

    ustozlar = await ns.get_barcha_ustozlar_faol()

    for ustoz in ustozlar:
        tg_id = ns.get_rich_text(ustoz, "Telegram ID")
        if not tg_id:
            continue
        tg_id = int(tg_id)

        if ns.ustoz_tatilda_mi(ustoz, bugun_sana):
            continue  # ta'tildagi ustozga eslatma yuborilmaydi

        # Davomatsiz guruhlar ham eslatmaga kiradi — ustoz jadvalini to'liq
        # ko'rsin. Lekin ular uchun Darslar grafigiga yozuv OCHILMAYDI,
        # chunki u yerda davomat kiritilmaydi va "Belgilanmagan" bo'lib
        # abadiy osilib qolardi.
        hammasi = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=False)
        if not hammasi:
            continue  # umuman guruhi yo'q ustozga bo'sh eslatma yuborilmaydi

        davomatli_guruhlar = [
            g for g in hammasi if not ns.get_checkbox(g, "Davomat kerak emas")
        ]

        bugungi = []
        for g in hammasi:
            kunlari = dars_kunlari_raqamga(ns.get_multi_select(g, "Dars kunlari"))
            if bugungi_kun_idx not in kunlari:
                continue
            bugungi.append(g)

            if ns.get_checkbox(g, "Davomat kerak emas"):
                continue  # grafik yuritilmaydi

            grafik = await ns.get_grafik_yozuv(g["id"], bugun_iso)
            if not grafik:
                await ns.grafik_yaratish(
                    g["id"], bugun_iso, config.GRAFIK_BELGILANMAGAN,
                    guruh_nomi=ns.get_title(g, "Guruh nomi"),
                )

        # Belgilanmagan darslarni oldindan olamiz — bugun darsi bo'lmasa ham
        # ogohlantirish yuborilishi kerak.
        belgilanmagan = await ns.belgilanmagan_darslar()
        guruh_idlari = {g["id"] for g in davomatli_guruhlar}
        ozimizniki = [
            b for b in belgilanmagan
            if ns.get_relation_ids(b, "Guruh")
            and ns.get_relation_ids(b, "Guruh")[0] in guruh_idlari
            and (ns.get_date_start(b, "Sana") or "")[:10] != bugun_iso
        ]

        matn = (
            f"<b>📅  Bugungi darslar</b>\n"
            f"<i>{sana_ozbekcha(bugun_sana)}</i>\n"
            f"{CHIZIQ}\n"
        )
        if bugungi:
            bugungi.sort(key=lambda x: vaqt_tartibi(ns.get_select(x, "Dars vaqti")))
            for g in bugungi:
                vaqt = ns.get_select(g, "Dars vaqti") or "vaqti belgilanmagan"
                qator = (
                    f"🕐{html_himoya(vaqt)}\u00a0·  "
                    f"📚<b>{html_himoya(ns.get_title(g, 'Guruh nomi'))}</b>"
                )
                if ns.get_checkbox(g, "Davomat kerak emas"):
                    qator += "\u00a0·  💠<i>Davomat shart emas</i>"
                matn += qator + "\n\n"
            matn += f"{CHIZIQ}\nDars tugagach davomat kiriting 👇"
        else:
            matn += "🌿  Bugun darsingiz yo'q."

        if ozimizniki:
            matn = (
                f"<b>⚠️  Belgilanmagan darslar: {len(ozimizniki)} ta</b>\n"
                f"{CHIZIQ}\n"
                + belgilanmagan_royxat_matni(ozimizniki, ns)
                + "\n\n<i>Dars o'tilgan bo'lsa — «📋 Davomat kiritish» dan\no'sha kunni tanlab kiriting.\nDars bo'lmagan bo'lsa — «🚫 Dars qoldirish» dan belgilang.</i>\n\n"
            ) + matn

        try:
            await bot.send_message(tg_id, matn, reply_markup=kb.asosiy_menyu())
        except Exception:
            pass  # ustoz botni bloklagan bo'lishi mumkin

    await _oylik_hisob_tekshiruvi(bugun_sana)
    await _yangi_talabalar_xabari(bot)
    await _takror_nazorati(bot)


async def _yangi_talabalar_xabari(bot: Bot):
    """Oxirgi sutkada qo'shilgan talabalar haqida ustozga xabar beradi.

    Ta'tildagi ustozga ham yuboriladi — qaytganda bilib tursin.
    """
    yozilishlar = await ns.yangi_yozilishlar(soat_orqaga=24)
    if not yozilishlar:
        return

    # Ustoz bo'yicha guruhlaymiz — bitta ustozga bitta xabar ketsin
    ustoz_bo_yicha: dict[str, list] = {}
    guruh_keshi: dict = {}

    for y in yozilishlar:
        guruh_ids = ns.get_relation_ids(y, "Guruh")
        talaba_ids = ns.get_relation_ids(y, "Talaba")
        if not guruh_ids or not talaba_ids:
            continue

        guruh_id = guruh_ids[0]
        if guruh_id not in guruh_keshi:
            try:
                guruh = await ns.get_page(guruh_id)
                ustoz_ids = ns.get_relation_ids(guruh, "Ustoz")
                guruh_keshi[guruh_id] = {
                    "nomi": ns.get_title(guruh, "Guruh nomi"),
                    "ustoz_id": ustoz_ids[0] if ustoz_ids else None,
                }
            except Exception:
                continue

        malumot = guruh_keshi[guruh_id]
        if not malumot["ustoz_id"]:
            continue

        try:
            talaba_ismi = await ns.get_talaba_ismi(talaba_ids[0])
        except Exception:
            continue

        boshlagan = ns.get_date_start(y, "Boshlagan sana")
        ustoz_bo_yicha.setdefault(malumot["ustoz_id"], []).append({
            "talaba": talaba_ismi,
            "guruh": malumot["nomi"],
            "boshlagan": boshlagan[:10] if boshlagan else None,
        })

    for ustoz_id, royxat in ustoz_bo_yicha.items():
        try:
            ustoz = await ns.get_page(ustoz_id)
        except Exception:
            continue
        tg_id = ns.get_rich_text(ustoz, "Telegram ID")
        if not tg_id or not tg_id.isdigit():
            continue

        sarlavha = ("🆕  <b>Guruhingizga yangi talaba qo'shildi</b>"
                    if len(royxat) == 1
                    else f"🆕  <b>Guruhingizga {len(royxat)} ta yangi talaba qo'shildi</b>")
        matn = f"{sarlavha}\n{CHIZIQ}"
        for t in royxat:
            matn += f"\n👤  {html_himoya(t['talaba'])}\n📚  {html_himoya(t['guruh'])}"
            if t["boshlagan"]:
                d = date.fromisoformat(t["boshlagan"])
                matn += f"\n📅  Boshlaydi: {sana_ozbekcha(d)}"
            matn += "\n"

        try:
            await bot.send_message(int(tg_id), matn)
        except Exception:
            pass  # ustoz botni bloklagan bo'lishi mumkin


async def _takror_nazorati(bot: Bot):
    """Zaxira nazorat: oxirgi 3 kunda takroriy Davomat yozuvi bor-yo'qligi.

    Asosiy himoya ns.davomat_yaratish() ichida — u takror yaratilishiga yo'l
    qo'ymaydi. Bu tekshiruv kutilmagan yo'l bilan paydo bo'lgan takrorni
    ushlaydi. Yozuvlar o'chirilmaguncha har kuni eslatib turadi.
    """
    takrorlar = await ns.takroriy_davomatlar(kun_orqaga=3)
    if not takrorlar:
        return

    matn = (
        f"⚠️  <b>Takroriy davomat yozuvlari topildi</b>\n"
        f"{CHIZIQ}\n"
        f"Bir xil talabaga bir kun uchun bir nechta yozuv bor.\n"
        f"Bu puldan ortiqcha yechilishiga olib keladi.\n"
        f"{CHIZIQ}\n"
    )
    for t in takrorlar[:15]:
        matn += f"• {html_himoya(t['nomi'])} — <b>{t['soni']} ta</b>\n"
    if len(takrorlar) > 15:
        matn += f"<i>...va yana {len(takrorlar) - 15} ta</i>\n"
    matn += (
        f"{CHIZIQ}\n"
        f"<i>Notionda ortiqchasini o'chiring. O'chirilmaguncha\n"
        f"bu xabar har kuni takrorlanadi.</i>"
    )
    await admin_xabar.yuborish(matn, bot)


async def _oylik_hisob_tekshiruvi(bugun_sana: date):
    """Davomatsiz guruhlar uchun oylik to'lovni hisoblaydi.
    Agar ustoz shu kuni ta'tilda bo'lsa, sana 1 kunga suriladi (doimiy)."""
    guruhlar_filter = {"property": "Davomat kerak emas", "checkbox": {"equals": True}}
    davomatsiz_guruhlar = await ns.query_all(config.DB_GURUHLAR, guruhlar_filter)

    for guruh in davomatsiz_guruhlar:
        if ns.get_status(guruh, "Guruh holati") != config.GURUH_FAOL:
            continue

        ustoz_ids = ns.get_relation_ids(guruh, "Ustoz")
        ustoz_tatilda = False
        if ustoz_ids:
            ustoz = await ns.get_page(ustoz_ids[0])
            ustoz_tatilda = ns.ustoz_tatilda_mi(ustoz, bugun_sana)

        yozilishlar = await ns.get_guruh_yozilishlari(guruh["id"], holatlar=[config.YOZILISH_OQIYABDI])
        for y in yozilishlar:
            boshlagan = ns.get_date_start(y, "Boshlagan sana")
            if not boshlagan:
                continue
            boshlagan_sana = date.fromisoformat(boshlagan[:10])

            # Oyning oxirgi kuni muammosi: talaba 31-sanada boshlagan bo'lsa,
            # fevralda 31-kun yo'q — bunday oy butunlay o'tkazib yuborilardi.
            # Yechim: kerakli kun oyning oxirgi kunidan katta bo'lsa,
            # hisob oyning OXIRGI kunida bajariladi.
            oyning_oxirgi_kuni = calendar.monthrange(
                bugun_sana.year, bugun_sana.month
            )[1]
            kerakli_kun = min(boshlagan_sana.day, oyning_oxirgi_kuni)

            if bugun_sana.day != kerakli_kun:
                continue

            # Shu oyda allaqachon "Oylik hisob" yozilganmi?
            oy_boshi = bugun_sana.replace(day=1).isoformat()
            filter_ = {
                "and": [
                    {"property": "Yozilish", "relation": {"contains": y["id"]}},
                    {"property": "Holat", "select": {"equals": config.HOLAT_OYLIK_HISOB}},
                    {"property": "Sana", "date": {"on_or_after": oy_boshi}},
                ]
            }
            mavjud = await ns.query_all(config.DB_DAVOMAT, filter_)
            if mavjud:
                continue

            if ustoz_tatilda:
                # Sanani 1 kunga suramiz (doimiy siljish)
                yangi_sana = (boshlagan_sana + timedelta(days=1)).isoformat()
                await ns.update_page(y["id"], {"Boshlagan sana": ns.prop_date(yangi_sana)})
                continue

            talaba_ids = ns.get_relation_ids(y, "Talaba")
            talaba_ismi = await ns.get_talaba_ismi(talaba_ids[0]) if talaba_ids else "?"
            guruh_nomi = ns.get_title(guruh, "Guruh nomi")
            await ns.davomat_yaratish(
                yozilish_id=y["id"], talaba_ismi=talaba_ismi, guruh_nomi=guruh_nomi,
                sana=bugun_sana.isoformat(), holat=config.HOLAT_OYLIK_HISOB,
            )


async def kunlik_hisobot(bot: Bot):
    """Har kuni 23:00 — adminga yig'ma hisobot (guruh va ustoz ismi bilan)."""
    # Telegram xabar uzunligi cheklangan — har bo'limda shuncha qator ko'rsatiladi
    CHEKLOV = 15

    bugun_iso = bugun().isoformat()

    filter_otildi = {
        "and": [
            {"property": "Sana", "date": {"equals": bugun_iso}},
            {"property": "Holat", "select": {"equals": config.GRAFIK_DARS_OTILDI}},
        ]
    }
    filter_qoldirildi = {
        "and": [
            {"property": "Sana", "date": {"equals": bugun_iso}},
            {"property": "Holat", "select": {"equals": config.GRAFIK_DARS_QOLDIRILDI}},
        ]
    }
    otildi = await ns.query_all(config.DB_DARSLAR_GRAFIGI, filter_otildi)
    qoldirildi = await ns.query_all(config.DB_DARSLAR_GRAFIGI, filter_qoldirildi)
    belgilanmagan = await ns.belgilanmagan_darslar(kun_orqaga=0)

    ustozlar = await ns.get_barcha_ustozlar_faol()
    tatildagilar = [u for u in ustozlar if ns.ustoz_tatilda_mi(u, bugun())]

    # Guruh/ustoz nomlari — bitta hisobot ichida kesh orqali, takroriy so'rovsiz
    kesh: dict = {}

    async def royxat(yozuvlar: list[dict], sabab_bilan: bool = False) -> str:
        if not yozuvlar:
            return ""
        qatorlar = []
        for y in yozuvlar[:CHEKLOV]:
            guruh_nomi, ustoz_ismi = await ns.grafik_guruh_va_ustoz(y, kesh)
            qator = f"     • {html_himoya(guruh_nomi)} — {html_himoya(ustoz_ismi)}"
            if sabab_bilan:
                sabab = ns.get_select(y, "Sabab")
                if sabab:
                    qator += f"\n       <i>{html_himoya(sabab)}</i>"
            qatorlar.append(qator)
        matn = "\n".join(qatorlar)
        qolgan = len(yozuvlar) - CHEKLOV
        if qolgan > 0:
            matn += f"\n     <i>...va yana {qolgan} ta</i>"
        return matn + "\n"

    matn = (
        f"<b>📊  Kunlik hisobot</b>\n"
        f"<i>{sana_ozbekcha(bugun())}</i>\n"
        f"{CHIZIQ}\n"
        f"✅  <b>Dars o'tildi: {len(otildi)}</b>\n"
    )
    matn += await royxat(otildi)

    matn += f"\n🚫  <b>Dars qoldirildi: {len(qoldirildi)}</b>\n"
    matn += await royxat(qoldirildi, sabab_bilan=True)

    matn += f"\n⚠️  <b>Belgilanmagan: {len(belgilanmagan)}</b>\n"
    matn += await royxat(belgilanmagan)

    if tatildagilar:
        ismlar = ", ".join(ns.get_title(u, "Ism") for u in tatildagilar)
        matn += f"{CHIZIQ}\n🌴  Ta'tilda: {html_himoya(ismlar)}"

    await admin_xabar.yuborish(matn, bot)


async def tatil_nazorati(bot: Bot):
    """Ta'til tugashidan 1 kun oldin so'raydi, muddati o'tganlarni avtomatik tozalaydi."""
    bugun_sana = bugun()
    ustozlar = await ns.get_barcha_ustozlar_faol()

    for ustoz in ustozlar:
        boshlanish = ns.get_date_start(ustoz, "Ta'til boshlanishi")
        tugash = ns.get_date_start(ustoz, "Ta'til tugashi")
        if not boshlanish or not tugash:
            continue

        tugash_sana = date.fromisoformat(tugash[:10])
        tg_id = ns.get_rich_text(ustoz, "Telegram ID")
        if not tg_id:
            continue
        tg_id = int(tg_id)

        if tugash_sana == bugun_sana + timedelta(days=1):
            try:
                await bot.send_message(
                    tg_id,
                    f"<b>🌴  Ta'til tugayapti</b>\n"
                    f"{CHIZIQ}\n"
                    f"Ta'tilingiz ertaga tugaydi.\n"
                    f"Ertaga qaytasizmi?",
                    reply_markup=kb.tatil_qaytish_sorovi(),
                )
            except Exception:
                pass
        elif tugash_sana < bugun_sana:
            await ns.clear_ustoz_tatil(ustoz["id"])
