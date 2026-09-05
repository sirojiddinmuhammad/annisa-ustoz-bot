# money_service.py
# Notion formula/rollup natijalarini API o'qiy olmasligi mumkin ("omitted").
# Shuning uchun "Balansim" bo'limi uchun bot Davomat yozuvlaridagi xom
# ma'lumotdan (Holat, Qo'lda summa, Qo'lda ustoz ulushi) o'zi hisoblab chiqadi —
# bu Notiondagi Sarflangan/Ustoz ulushi formulalari bilan bir xil natija beradi.

import config
from utils import bugun
import notion_service as ns


def davomat_sarflangan_va_ustoz_ulushi(davomat: dict, guruh: dict) -> tuple[float, float]:
    """Bitta Davomat yozuvi uchun (Sarflangan, Ustoz ulushi) ni Notion formulasi
    bilan bir xil mantiqda hisoblaydi.
    """
    holat = ns.get_select(davomat, "Holat")
    qolda_summa = ns.get_number(davomat, "Qo'lda summa")
    qolda_ustoz_ulushi = ns.get_number(davomat, "Qo'lda ustoz ulushi")

    if qolda_summa is not None:
        sarflangan = qolda_summa
    elif holat == config.HOLAT_OYLIK_HISOB:
        sarflangan = ns.get_number(guruh, "Oylik to'lov") or 0
    elif holat in (config.HOLAT_KELDI, config.HOLAT_KELMADI):
        sarflangan = ns.guruh_dars_narxi(guruh)
    else:  # Ta'til — pul yechilmaydi
        sarflangan = 0

    if qolda_ustoz_ulushi is not None:
        ustoz_ulushi = qolda_ustoz_ulushi
    else:
        foiz = ns.guruh_ustoz_ulushi_foiz(guruh)
        ustoz_ulushi = round(sarflangan * foiz / 100)

    return sarflangan, ustoz_ulushi


async def ustoz_balansi_hisobla(ustoz_page: dict) -> dict:
    """Ustozning jami ishlab topgani, berilgan oyliklari, balansi va shu oygi
    daromadini hisoblaydi. Avval Notiondagi tayyor qiymatni o'qishga urinadi,
    bo'lmasa (omitted chiqsa) xom ma'lumotdan o'zi hisoblaydi.
    """
    ishlab_topgani = ns.get_number(ustoz_page, "Ishlab topgani")
    berilgan = ns.get_number(ustoz_page, "Berilgan oyliklar")
    balans = ns.get_number(ustoz_page, "Ustoz balansi")

    if ishlab_topgani is not None and berilgan is not None and balans is not None:
        # Notion qiymatlarni to'g'ri qaytardi — qo'shimcha hisoblash shart emas.
        # Shu oyni baribir xom ma'lumotdan hisoblaymiz (formula buni bermaydi).
        shu_oy = await _shu_oy_daromadi(ustoz_page["id"])
        return {
            "ishlab_topgani": ishlab_topgani,
            "berilgan_oyliklar": berilgan,
            "balans": balans,
            "shu_oy": shu_oy,
        }

    # --- Zaxira: xom ma'lumotdan o'zi hisoblaydi ---
    return await _xom_malumotdan_hisobla(ustoz_page)


async def _shu_oy_daromadi(ustoz_id: str) -> float:
    import datetime as dt
    bugun_sana = bugun()
    oy_boshi = bugun_sana.replace(day=1).isoformat()

    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz_id, davomatli_faqat=False)
    jami = 0.0
    for guruh in guruhlar:
        yozilishlar = await ns.get_guruh_yozilishlari(
            guruh["id"], holatlar=[config.YOZILISH_OQIYABDI, config.YOZILISH_TATILDA, config.YOZILISH_TUGATDI]
        )
        for y in yozilishlar:
            filter_ = {
                "and": [
                    {"property": "Yozilish", "relation": {"contains": y["id"]}},
                    {"property": "Sana", "date": {"on_or_after": oy_boshi}},
                ]
            }
            davomatlar = await ns.query_all(config.DB_DAVOMAT, filter_)
            for d in davomatlar:
                _, ulush = davomat_sarflangan_va_ustoz_ulushi(d, guruh)
                jami += ulush
    return jami


async def _xom_malumotdan_hisobla(ustoz_page: dict) -> dict:
    ustoz_id = ustoz_page["id"]
    guruhlar = await ns.get_ustoz_faol_guruhlari(ustoz_id, davomatli_faqat=False)

    jami_ishlab_topgan = 0.0
    shu_oy = 0.0
    import datetime as dt
    oy_boshi = bugun().replace(day=1).isoformat()

    for guruh in guruhlar:
        yozilishlar = await ns.get_guruh_yozilishlari(
            guruh["id"], holatlar=[config.YOZILISH_OQIYABDI, config.YOZILISH_TATILDA, config.YOZILISH_TUGATDI]
        )
        for y in yozilishlar:
            davomatlar = await ns.query_all(
                config.DB_DAVOMAT,
                {"property": "Yozilish", "relation": {"contains": y["id"]}},
            )
            for d in davomatlar:
                _, ulush = davomat_sarflangan_va_ustoz_ulushi(d, guruh)
                jami_ishlab_topgan += ulush
                sana = ns.get_date_start(d, "Sana")
                if sana and sana[:10] >= oy_boshi:
                    shu_oy += ulush

    oyliklar = await ns.get_ustoz_oyliklari(ustoz_id)
    berilgan = sum(ns.get_number(o, "Summa") or 0 for o in oyliklar)

    return {
        "ishlab_topgani": jami_ishlab_topgan,
        "berilgan_oyliklar": berilgan,
        "balans": jami_ishlab_topgan - berilgan,
        "shu_oy": shu_oy,
    }
