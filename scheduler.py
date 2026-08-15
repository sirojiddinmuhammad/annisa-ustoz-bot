# scheduler.py
# Kunlik avtomatik vazifalar: 02:20 ertalabki eslatma, 23:00 kunlik hisobot,
# oylik hisob (davomatsiz guruhlar) va ta'til nazorati.

from datetime import date, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config
import notion_service as ns
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

        davomatli_guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz["id"], davomatli_faqat=True)
        if not davomatli_guruhlar:
            continue  # umuman guruhi yo'q ustozga bo'sh eslatma yuborilmaydi

        bugungi = []
        for g in davomatli_guruhlar:
            kunlari = dars_kunlari_raqamga(ns.get_multi_select(g, "Dars kunlari"))
            if bugungi_kun_idx in kunlari:
                bugungi.append(g)
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
                matn += (
                    f"\n🕐  <b>{html_himoya(vaqt)}</b>\n"
                    f"📚  {html_himoya(ns.get_title(g, 'Guruh nomi'))}\n"
                )
            matn += f"{CHIZIQ}\nDars tugagach davomat kiriting 👇"
        else:
            matn += "🌿  Bugun darsingiz yo'q."

        if ozimizniki:
            matn = (
                f"<b>⚠️  Belgilanmagan darslar: {len(ozimizniki)} ta</b>\n"
                f"{CHIZIQ}\n"
                + belgilanmagan_royxat_matni(ozimizniki, ns)
                + "\n\n<i>Davomat bo'limidan o'sha kunni tanlab kiriting.</i>\n\n"
            ) + matn

        try:
            await bot.send_message(tg_id, matn, reply_markup=kb.asosiy_menyu())
        except Exception:
            pass  # ustoz botni bloklagan bo'lishi mumkin

    await _oylik_hisob_tekshiruvi(bugun_sana)


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

            if boshlagan_sana.day != bugun_sana.day:
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
    """Har kuni 23:00 — adminga yig'ma hisobot."""
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

    matn = (
        f"<b>📊  Kunlik hisobot</b>\n"
        f"{sana_ozbekcha(bugun())}\n"
        f"{CHIZIQ}\n"
        f"✅  Dars o'tildi:  <b>{len(otildi)}</b>\n"
        f"🚫  Dars qoldirildi:  <b>{len(qoldirildi)}</b>\n"
        f"⚠️  Belgilanmagan:  <b>{len(belgilanmagan)}</b>\n"
    )
    if tatildagilar:
        ismlar = ", ".join(ns.get_title(u, "Ism") for u in tatildagilar)
        matn += f"{CHIZIQ}\n🌴  Ta'tilda: {html_himoya(ismlar)}"

    await bot.send_message(config.ADMIN_ID, matn)


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
