# notion_service.py
# Notion API bilan bevosita ishlaydigan barcha funksiyalar shu yerda.
# Diqqat: formula/rollup natijalarini API o'qiy olmaydi ("omitted" muammosi).
# Shuning uchun pul hisoblari kerak bo'lganda bot xom (raw) ma'lumotdan
# o'zi hisoblab chiqadi — Notion formulalariga tayanmaydi.

import httpx
from datetime import date, datetime, timedelta

import config
from utils import bugun

NOTION_API = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {config.NOTION_TOKEN}",
    "Notion-Version": "2025-09-03",
    "Content-Type": "application/json",
}


async def _request(method: str, path: str, json: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(
            method, f"{NOTION_API}{path}", headers=HEADERS, json=json
        )
        resp.raise_for_status()
        return resp.json()


async def query_all(data_source_id: str, filter_: dict | None = None,
                     sorts: list | None = None) -> list[dict]:
    """Bazadan barcha mos yozuvlarni sahifalab (pagination) yig'ib qaytaradi.
    Diqqat: Notion API 2025-09-03 versiyasida so'rov data_source_id orqali
    yuboriladi, database_id orqali emas — /v1/databases/.../query endi
    ishlamaydi (404 qaytaradi)."""
    results = []
    body: dict = {}
    if filter_:
        body["filter"] = filter_
    if sorts:
        body["sorts"] = sorts

    cursor = None
    while True:
        if cursor:
            body["start_cursor"] = cursor
        data = await _request("POST", f"/data_sources/{data_source_id}/query", body)
        results.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
    return results


async def get_page(page_id: str) -> dict:
    return await _request("GET", f"/pages/{page_id}")


async def create_page(data_source_id: str, properties: dict) -> dict:
    body = {
        "parent": {"type": "data_source_id", "data_source_id": data_source_id},
        "properties": properties,
    }
    return await _request("POST", "/pages", body)


async def update_page(page_id: str, properties: dict) -> dict:
    return await _request("PATCH", f"/pages/{page_id}", {"properties": properties})


async def archive_page(page_id: str) -> dict:
    """Notion trash'iga tashlaydi (30 kun tiklanadi)."""
    return await _request("PATCH", f"/pages/{page_id}", {"archived": True})


# ---------------------------------------------------------------------------
# Property o'qish yordamchilari
# ---------------------------------------------------------------------------

def get_title(page: dict, prop_name: str) -> str:
    prop = page["properties"].get(prop_name, {})
    parts = prop.get("title", [])
    return "".join(p["plain_text"] for p in parts)


def get_rich_text(page: dict, prop_name: str) -> str:
    prop = page["properties"].get(prop_name, {})
    parts = prop.get("rich_text", [])
    return "".join(p["plain_text"] for p in parts)


def get_select(page: dict, prop_name: str) -> str | None:
    prop = page["properties"].get(prop_name, {})
    sel = prop.get("select")
    return sel["name"] if sel else None


def get_status(page: dict, prop_name: str) -> str | None:
    """Notionda "Status" turi "Select" dan boshqa — alohida o'qiladi.
    Masalan Guruhlar bazasidagi "Guruh holati"."""
    prop = page["properties"].get(prop_name, {})
    st = prop.get("status")
    return st["name"] if st else None


def get_number(page: dict, prop_name: str) -> float | None:
    return page["properties"].get(prop_name, {}).get("number")


def get_checkbox(page: dict, prop_name: str) -> bool:
    return bool(page["properties"].get(prop_name, {}).get("checkbox"))


def get_date_start(page: dict, prop_name: str) -> str | None:
    d = page["properties"].get(prop_name, {}).get("date")
    return d["start"] if d else None


def get_relation_ids(page: dict, prop_name: str) -> list[str]:
    rels = page["properties"].get(prop_name, {}).get("relation", [])
    return [r["id"] for r in rels]


def get_multi_select(page: dict, prop_name: str) -> list[str]:
    items = page["properties"].get(prop_name, {}).get("multi_select", [])
    return [i["name"] for i in items]


# ---------------------------------------------------------------------------
# Property yozish yordamchilari
# ---------------------------------------------------------------------------

def prop_title(text: str) -> dict:
    return {"title": [{"text": {"content": text}}]}


def prop_select(name: str) -> dict:
    return {"select": {"name": name}}


def prop_date(iso_date: str) -> dict:
    return {"date": {"start": iso_date}}


def prop_relation(page_ids: list[str]) -> dict:
    return {"relation": [{"id": pid} for pid in page_ids]}


def prop_number(value: float) -> dict:
    return {"number": value}


def prop_checkbox(value: bool) -> dict:
    return {"checkbox": value}


# ---------------------------------------------------------------------------
# Ustozlar
# ---------------------------------------------------------------------------

async def find_ustozlar_by_name(ism: str) -> list[dict]:
    """Ism bo'yicha qidiradi (aniq mos yoki qisman)."""
    filter_ = {"property": "Ism", "title": {"contains": ism}}
    return await query_all(config.DB_USTOZLAR, filter_)


async def find_ustoz_by_telegram_id(tg_id: int) -> dict | None:
    filter_ = {"property": "Telegram ID", "rich_text": {"equals": str(tg_id)}}
    results = await query_all(config.DB_USTOZLAR, filter_)
    return results[0] if results else None


async def set_ustoz_telegram_id(ustoz_page_id: str, tg_id: int) -> None:
    await update_page(ustoz_page_id, {
        "Telegram ID": {"rich_text": [{"text": {"content": str(tg_id)}}]}
    })


async def clear_telegram_id_if_taken(tg_id: int) -> None:
    """Shu ID boshqa ustozga bog'langan bo'lsa, tozalaydi."""
    existing = await find_ustoz_by_telegram_id(tg_id)
    if existing:
        await update_page(existing["id"], {
            "Telegram ID": {"rich_text": []}
        })


async def get_ustoz_page(ustoz_page_id: str) -> dict:
    return await get_page(ustoz_page_id)


async def set_ustoz_tatil(ustoz_page_id: str, boshlanish: str, tugash: str) -> None:
    await update_page(ustoz_page_id, {
        "Ta'til boshlanishi": prop_date(boshlanish),
        "Ta'til tugashi": prop_date(tugash),
    })


async def clear_ustoz_tatil(ustoz_page_id: str) -> None:
    await update_page(ustoz_page_id, {
        "Ta'til boshlanishi": {"date": None},
        "Ta'til tugashi": {"date": None},
    })


def ustoz_tatilda_mi(ustoz_page: dict, tekshiriladigan_sana: date) -> bool:
    boshlanish = get_date_start(ustoz_page, "Ta'til boshlanishi")
    tugash = get_date_start(ustoz_page, "Ta'til tugashi")
    if not boshlanish or not tugash:
        return False
    b = date.fromisoformat(boshlanish[:10])
    t = date.fromisoformat(tugash[:10])
    return b <= tekshiriladigan_sana <= t


async def get_barcha_ustozlar_faol() -> list[dict]:
    """Telegram ID bor barcha ustozlar (ya'ni ro'yxatdan o'tganlar)."""
    filter_ = {"property": "Telegram ID", "rich_text": {"is_not_empty": True}}
    return await query_all(config.DB_USTOZLAR, filter_)


# ---------------------------------------------------------------------------
# Guruhlar
# ---------------------------------------------------------------------------

async def get_ustoz_faol_guruhlari(ustoz_page_id: str, davomatli_faqat: bool = True) -> list[dict]:
    """Ustozning Faol holatidagi guruhlari.
    davomatli_faqat=True bo'lsa, 'Davomat kerak emas' belgili guruhlar chiqarib tashlanadi.
    """
    filter_ = {
        "and": [
            {"property": "Ustoz", "relation": {"contains": ustoz_page_id}},
            {"property": "Guruh holati", "status": {"equals": config.GURUH_FAOL}},
        ]
    }
    guruhlar = await query_all(config.DB_GURUHLAR, filter_)
    if davomatli_faqat:
        guruhlar = [g for g in guruhlar if not get_checkbox(g, "Davomat kerak emas")]
    return guruhlar


def guruh_dars_narxi(guruh: dict) -> float:
    """1 dars narxi = Oylik to'lov / Chastota (formulaga tayanmasdan o'zimiz hisoblaymiz)."""
    oylik = get_number(guruh, "Oylik to'lov") or 0
    chastota = get_number(guruh, "Chastota") or 1
    return round(oylik / chastota) if chastota else 0


def guruh_ustoz_ulushi_foiz(guruh: dict) -> float:
    return get_number(guruh, "Ustoz ulushi %") or 0


# ---------------------------------------------------------------------------
# Yozilishlar
# ---------------------------------------------------------------------------

async def get_guruh_yozilishlari(guruh_id: str, holatlar: list[str] | None = None) -> list[dict]:
    if holatlar is None:
        holatlar = [config.YOZILISH_OQIYABDI, config.YOZILISH_TATILDA]
    filter_ = {
        "and": [
            {"property": "Guruh", "relation": {"contains": guruh_id}},
            {"or": [{"property": "Holat", "select": {"equals": h}} for h in holatlar]},
        ]
    }
    return await query_all(config.DB_YOZILISHLAR, filter_)


def yozilish_chegirmasi_bor_mi(yozilish: dict) -> bool:
    """Diqqat: "Chegirmasi bor" — Notionda formula, uni API o'qiy olmaydi.
    Shuning uchun "Chegirmalar" relation maydonini tekshiramiz — agar
    yozilishga birorta chegirma bog'langan bo'lsa, tekshiruv davom etadi.
    """
    return bool(get_relation_ids(yozilish, "Chegirmalar"))


async def yozilish_holatini_ozgartirish(yozilish_id: str, yangi_holat: str) -> None:
    """Yozilish holatini o'zgartiradi (O'qiyabdi / Ta'tilda).

    Davomatda ustoz "Ta'til" belgilasa — talaba Ta'tilda holatiga o'tadi va
    keyingi darslarda avtomat shunday belgilanib turadi (puli yechilmaydi).
    Ustoz "Keldi" belgilasa — O'qiyabdi ga qaytadi.
    """
    await update_page(yozilish_id, {"Holat": prop_select(yangi_holat)})


async def yozilishni_yopish(yozilish_id: str, sana: str, sabab: str,
                             ustoz_ismi: str) -> None:
    """Talabani guruhdan chiqarish — Yozilish holati "Tugatdi" ga o'tadi va
    shu kundan boshlab talaba davomat ro'yxatida ko'rinmaydi.
    Sabab Izohga yoziladi, shunda keyinchalik kursni haqiqatan tugatgan
    talabalar chiqarilganlardan farqlanadi."""
    mavjud_izoh = ""
    try:
        sahifa = await get_page(yozilish_id)
        mavjud_izoh = get_rich_text(sahifa, "Izoh")
    except Exception:
        pass

    yangi_izoh = f"{ustoz_ismi} chiqardi ({sana}): {sabab}"
    if mavjud_izoh:
        yangi_izoh = f"{mavjud_izoh}\n{yangi_izoh}"

    await update_page(yozilish_id, {
        "Holat": prop_select(config.YOZILISH_TUGATDI),
        "Tugagan sana": prop_date(sana),
        "Izoh": {"rich_text": [{"text": {"content": yangi_izoh[:1900]}}]},
    })


async def oxirgi_davomatlar(yozilish_id: str, soni: int = 5) -> list[dict]:
    """Yozilishning eng oxirgi Davomat yozuvlari — sana bo'yicha, yangisidan
    boshlab. Ketma-ket kelmagan darslarni sanash uchun ishlatiladi."""
    filter_ = {"property": "Yozilish", "relation": {"contains": yozilish_id}}
    sorts = [{"property": "Sana", "direction": "descending"}]
    natija = await query_all(config.DB_DAVOMAT, filter_, sorts)
    return natija[:soni]


async def get_talaba_ismi(talaba_id: str) -> str:
    page = await get_page(talaba_id)
    return get_title(page, "Ism")


# ---------------------------------------------------------------------------
# Chegirmalar
# ---------------------------------------------------------------------------

async def get_faol_chegirma(yozilish_id: str) -> dict | None:
    filter_ = {
        "and": [
            {"property": "Yozilish", "relation": {"contains": yozilish_id}},
            {"property": "Holat", "select": {"equals": config.CHEGIRMA_FAOL}},
        ]
    }
    results = await query_all(config.DB_CHEGIRMALAR, filter_)
    return results[0] if results else None


async def chegirmali_darslar_soni(chegirma_id: str, yozilish_id: str) -> int:
    """Shu chegirmaning FAQAT shu talabaga (Yozilishga) tegishli Davomat
    yozuvlari soni. Diqqat: bitta Chegirma yozuvi bir nechta talabaga
    (Yozilishga) baravar biriktirilgan bo'lishi mumkin — shuning uchun umumiy
    son emas, har talabaning o'zi uchun alohida sanaladi."""
    filter_ = {
        "and": [
            {"property": "Chegirma", "relation": {"contains": chegirma_id}},
            {"property": "Yozilish", "relation": {"contains": yozilish_id}},
        ]
    }
    results = await query_all(config.DB_DAVOMAT, filter_)
    return len(results)


async def chegirma_barcha_talabalar_tugadimi(chegirma: dict, limit: float) -> bool:
    """Chegirmaga bog'langan HAR BIR talaba o'z limitiga yetganmi — shundagina
    umumiy Chegirma yozuvini 'Tugagan' qilish mumkin, aks holda boshqa
    talabalar hali chegirmadan mahrum qolib ketadi."""
    yozilish_idlari = get_relation_ids(chegirma, "Yozilish")
    for y_id in yozilish_idlari:
        soni = await chegirmali_darslar_soni(chegirma["id"], y_id)
        if soni < limit:
            return False
    return True


async def chegirmani_tugat(chegirma_id: str, sana: str) -> None:
    await update_page(chegirma_id, {
        "Holat": prop_select(config.CHEGIRMA_TUGAGAN),
        "Tugash sana": prop_date(sana),
    })


async def chegirmani_qayta_faollashtir(chegirma_id: str) -> None:
    await update_page(chegirma_id, {
        "Holat": prop_select(config.CHEGIRMA_FAOL),
        "Tugash sana": {"date": None},
    })


def chegirmali_summa_hisobla(dars_narxi: float, ustoz_ulushi_foiz: float,
                              chegirma_foiz: float, kim_kotaradi: str) -> tuple[float, float]:
    """Qaytaradi: (talaba_toladigan_summa, ustoz_ulushi_summasi)"""
    talaba_toladi = round(dars_narxi * (100 - chegirma_foiz) / 100)

    if kim_kotaradi == config.CHEGIRMA_MARKAZ_ZARARIGA:
        ustoz_ulushi = round(dars_narxi * ustoz_ulushi_foiz / 100)
    elif kim_kotaradi == config.CHEGIRMA_MARKAZ_BEZARAR:
        ustoz_ulushi = talaba_toladi
    else:  # Markaz/Ustoz — ikkalasi baravar ko'taradi
        ustoz_ulushi = round(talaba_toladi * ustoz_ulushi_foiz / 100)

    return talaba_toladi, ustoz_ulushi


# ---------------------------------------------------------------------------
# Davomat
# ---------------------------------------------------------------------------

async def get_davomat_yozuv(yozilish_id: str, sana: str) -> dict | None:
    filter_ = {
        "and": [
            {"property": "Yozilish", "relation": {"contains": yozilish_id}},
            {"property": "Sana", "date": {"equals": sana}},
        ]
    }
    results = await query_all(config.DB_DAVOMAT, filter_)
    return results[0] if results else None


async def get_guruh_davomat_kuni(guruh_id: str, sana: str, yozilish_idlari: list[str]) -> dict[str, dict]:
    """Guruhning shu kundagi barcha Davomat yozuvlarini {yozilish_id: davomat_page} shaklida qaytaradi."""
    natija = {}
    for y_id in yozilish_idlari:
        yozuv = await get_davomat_yozuv(y_id, sana)
        if yozuv:
            natija[y_id] = yozuv
    return natija


async def davomat_yaratish(
    yozilish_id: str, talaba_ismi: str, guruh_nomi: str, sana: str, holat: str,
    qolda_summa: float | None = None, qolda_ustoz_ulushi: float | None = None,
    chegirma_id: str | None = None,
) -> dict:
    nomi = f"{talaba_ismi} — {guruh_nomi} — {sana}"
    properties = {
        "Nomi": prop_title(nomi),
        "Yozilish": prop_relation([yozilish_id]),
        "Sana": prop_date(sana),
        "Holat": prop_select(holat),
    }
    if qolda_summa is not None:
        properties["Qo'lda summa"] = prop_number(qolda_summa)
    if qolda_ustoz_ulushi is not None:
        properties["Qo'lda ustoz ulushi"] = prop_number(qolda_ustoz_ulushi)
    if chegirma_id:
        properties["Chegirma"] = prop_relation([chegirma_id])
    return await create_page(config.DB_DAVOMAT, properties)


async def davomat_holatini_yangilash(davomat_page_id: str, yangi_holat: str) -> None:
    """Mavjud yozuvni yangilaydi — o'chirib qayta yaratmaydi (chegirma bog'lanishi saqlanadi)."""
    await update_page(davomat_page_id, {"Holat": prop_select(yangi_holat)})


async def davomat_ochirish(davomat_sahifalari: list[dict]) -> None:
    """Davomat yozuvlarini trash'ga tashlaydi, bog'liq chegirmani kerak bo'lsa qayta faollashtiradi."""
    for d in davomat_sahifalari:
        chegirma_ids = get_relation_ids(d, "Chegirma")
        await archive_page(d["id"])
        if chegirma_ids:
            chegirma = await get_page(chegirma_ids[0])
            tugash_sana = get_date_start(chegirma, "Tugash sana")
            davomat_sanasi = get_date_start(d, "Sana")
            holat = get_select(chegirma, "Holat")
            if (holat == config.CHEGIRMA_TUGAGAN and tugash_sana and davomat_sanasi
                    and tugash_sana[:10] == davomat_sanasi[:10]):
                await chegirmani_qayta_faollashtir(chegirma_ids[0])


def davomat_yaratilgan_vaqti_ok_mi(davomat_page: dict) -> bool:
    """O'chirish uchun: yozuv 1 haftadan eski bo'lmasligi kerak."""
    created = davomat_page.get("created_time")
    if not created:
        return False
    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    farq = datetime.now(created_dt.tzinfo) - created_dt
    return farq <= timedelta(days=config.DAVOMAT_OCHIRISH_MUDDATI_KUN)


# ---------------------------------------------------------------------------
# Darslar grafigi
# ---------------------------------------------------------------------------

async def get_grafik_yozuv(guruh_id: str, sana: str) -> dict | None:
    filter_ = {
        "and": [
            {"property": "Guruh", "relation": {"contains": guruh_id}},
            {"property": "Sana", "date": {"equals": sana}},
        ]
    }
    results = await query_all(config.DB_DARSLAR_GRAFIGI, filter_)
    return results[0] if results else None


async def keyingi_dars_raqami(guruh_id: str) -> int:
    """Faqat 'Dars o'tildi' holatidagi yozuvlarni sanaga qarab sanaydi."""
    filter_ = {
        "and": [
            {"property": "Guruh", "relation": {"contains": guruh_id}},
            {"property": "Holat", "select": {"equals": config.GRAFIK_DARS_OTILDI}},
        ]
    }
    sorts = [{"property": "Sana", "direction": "ascending"}]
    results = await query_all(config.DB_DARSLAR_GRAFIGI, filter_, sorts)
    return len(results) + 1


async def grafik_yaratish(guruh_id: str, sana: str, holat: str,
                           dars_raqami: int | None = None,
                           sabab: str | None = None, izoh: str | None = None,
                           guruh_nomi: str | None = None) -> dict:
    properties = {
        "Guruh": prop_relation([guruh_id]),
        "Sana": prop_date(sana),
        "Holat": prop_select(holat),
    }
    if guruh_nomi:
        properties["Nomi"] = prop_title(f"{guruh_nomi} — {sana}")
    if dars_raqami is not None:
        properties["Dars raqami"] = prop_number(dars_raqami)
    if sabab:
        properties["Sabab"] = prop_select(sabab)
    if izoh:
        properties["Izoh"] = {"rich_text": [{"text": {"content": izoh}}]}
    return await create_page(config.DB_DARSLAR_GRAFIGI, properties)


async def grafik_yangilash(grafik_page_id: str, holat: str,
                            dars_raqami: int | None = None,
                            sabab: str | None = None) -> None:
    properties = {"Holat": prop_select(holat)}
    if dars_raqami is not None:
        properties["Dars raqami"] = prop_number(dars_raqami)
    if sabab:
        properties["Sabab"] = prop_select(sabab)
    await update_page(grafik_page_id, properties)


async def grafik_belgilanmaganga_qaytarish(guruh_id: str, sana: str) -> None:
    yozuv = await get_grafik_yozuv(guruh_id, sana)
    if yozuv:
        await update_page(yozuv["id"], {
            "Holat": prop_select(config.GRAFIK_BELGILANMAGAN),
            "Dars raqami": {"number": None},
        })


async def grafik_guruh_va_ustoz(grafik_yozuv: dict, kesh: dict) -> tuple[str, str]:
    """Darslar grafigi yozuvidan (guruh nomi, ustoz ismi) ni qaytaradi.

    Diqqat: grafikdagi "Ustoz" — rollup, API uni o'qiy olmaydi. Shuning uchun
    guruh sahifasi orqali olinadi. `kesh` — bitta hisobot ichida bir guruh
    qayta-qayta so'ralmasligi uchun: {guruh_id: (guruh_nomi, ustoz_ismi)}.
    """
    guruh_ids = get_relation_ids(grafik_yozuv, "Guruh")
    if not guruh_ids:
        return "(guruhsiz)", "—"

    guruh_id = guruh_ids[0]
    if guruh_id in kesh:
        return kesh[guruh_id]

    try:
        guruh = await get_page(guruh_id)
        guruh_nomi = get_title(guruh, "Guruh nomi") or "(nomsiz)"
        ustoz_ismi = "—"
        ustoz_ids = get_relation_ids(guruh, "Ustoz")
        if ustoz_ids:
            ustoz = await get_page(ustoz_ids[0])
            ustoz_ismi = get_title(ustoz, "Ism") or "—"
    except Exception:
        guruh_nomi, ustoz_ismi = "(o'qib bo'lmadi)", "—"

    kesh[guruh_id] = (guruh_nomi, ustoz_ismi)
    return guruh_nomi, ustoz_ismi


async def belgilanmagan_darslar(kun_orqaga: int = config.BELGILANMAGAN_TEKSHIRUV_KUN) -> list[dict]:
    chegara = (bugun() - timedelta(days=kun_orqaga)).isoformat()
    filter_ = {
        "and": [
            {"property": "Holat", "select": {"equals": config.GRAFIK_BELGILANMAGAN}},
            {"property": "Sana", "date": {"on_or_after": chegara}},
        ]
    }
    return await query_all(config.DB_DARSLAR_GRAFIGI, filter_)


# ---------------------------------------------------------------------------
# Oyliklar (Balansim uchun)
# ---------------------------------------------------------------------------

async def get_ustoz_oyliklari(ustoz_id: str) -> list[dict]:
    filter_ = {"property": "Ustoz", "relation": {"contains": ustoz_id}}
    return await query_all(config.DB_OYLIKLAR, filter_)
