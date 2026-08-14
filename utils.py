# utils.py
# Kichik yordamchi funksiyalar.

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")

def bugun() -> date:
    """Toshkent vaqti bo'yicha bugungi sana.
    DIQQAT: date.today() ishlatilmasin — Railway serveri UTC da ishlaydi,
    shuning uchun Toshkentda 00:00-05:00 oralig'ida bir kun orqada qoladi.
    """
    return datetime.now(TASHKENT_TZ).date()


def hozir() -> datetime:
    """Toshkent vaqti bo'yicha hozirgi payt."""
    return datetime.now(TASHKENT_TZ)


OYLAR = [
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
]

HAFTA_KUNLARI = [
    "Dushanba", "Seshanba", "Chorshanba", "Payshanba",
    "Juma", "Shanba", "Yakshanba",
]


def sana_ozbekcha(d: date) -> str:
    return f"{HAFTA_KUNLARI[d.weekday()]}, {d.day}-{OYLAR[d.month - 1]}"


def sana_qisqa(d: date) -> str:
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def markdown_himoya(matn: str) -> str:
    """Telegram MarkdownV2 uchun maxsus belgilarni himoyalaydi."""
    maxsus = r"_*[]()~`>#+-=|{}.!"
    natija = ""
    for ch in matn:
        if ch in maxsus:
            natija += "\\" + ch
        else:
            natija += ch
    return natija


def yaqin_kunlar(dars_kunlari: list[int], soni: int = 4) -> list[date]:
    """dars_kunlari — hafta kunlari raqami (0=Dushanba...6=Yakshanba) ro'yxati.
    Bugundan boshlab orqaga qarab eng yaqin `soni` ta mos sanani qaytaradi.
    """
    natija = []
    kun = bugun()
    urinish = 0
    while len(natija) < soni and urinish < 60:
        if kun.weekday() in dars_kunlari:
            natija.append(kun)
        kun -= timedelta(days=1)
        urinish += 1
    return natija


def dars_kunlari_raqamga(kun_nomlari: list[str]) -> list[int]:
    """Notiondagi 'Dars kunlari' nomlarini hafta kuni raqamlariga aylantiradi.
    'Harkuni' — haftaning barcha kunlari degani.
    """
    if "Harkuni" in kun_nomlari:
        return list(range(7))
    return [HAFTA_KUNLARI.index(n) for n in kun_nomlari if n in HAFTA_KUNLARI]


def vaqt_tartibi(vaqt: str | None) -> tuple:
    """Guruhlarni dars vaqti bo'yicha saralash uchun kalit.
    Aniq vaqt (21:00) oldinda, 'Kelishilgan' va bo'sh qiymat oxirida turadi.
    """
    if not vaqt:
        return (2, "")
    qismlar = vaqt.split(":")
    if len(qismlar) == 2 and qismlar[0].strip().isdigit():
        try:
            return (0, f"{int(qismlar[0]):02d}:{qismlar[1].strip()}")
        except ValueError:
            pass
    return (1, vaqt)


def summa_format(summa: float) -> str:
    return f"{int(round(summa)):,}".replace(",", " ")


def html_himoya(matn: str) -> str:
    """Telegram HTML rejimi uchun maxsus belgilarni himoyalaydi."""
    return (matn.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


CHIZIQ = "━━━━━━━━━━━━━━━━━━━"


def muddat_sanalari(boshlanish: date) -> list[dict]:
    """Ta'til tugash sanasi uchun tayyor muddatlar."""
    return [
        {"label": "3 kun", "kun": 2},
        {"label": "1 hafta", "kun": 6},
        {"label": "2 hafta", "kun": 13},
        {"label": "1 oy", "kun": 30},
    ]


def belgilanmagan_royxat_matni(yozuvlar: list[dict], ns_modul, cheklov: int = 8) -> str:
    """Belgilanmagan darslar ro'yxatini matn ko'rinishida tayyorlaydi.
    yozuvlar — Darslar grafigi sahifalari.
    """
    qatorlar = []
    # Eng yangi sanadan boshlab
    tartiblangan = sorted(
        yozuvlar,
        key=lambda b: (ns_modul.get_date_start(b, "Sana") or ""),
        reverse=True,
    )
    for b in tartiblangan[:cheklov]:
        nomi = ns_modul.get_title(b, "Nomi")
        sana_iso = ns_modul.get_date_start(b, "Sana")
        if sana_iso:
            d = date.fromisoformat(sana_iso[:10])
            sana_matni = f"{d.day}-{OYLAR[d.month - 1]}"
        else:
            sana_matni = "sanasiz"
        # Nom "Guruh — 2026-08-13" ko'rinishida bo'lsa, guruh qismini ajratamiz
        guruh_nomi = nomi.split(" — ")[0] if " — " in nomi else nomi
        if not guruh_nomi:
            guruh_nomi = "(nomsiz guruh)"
        qatorlar.append(f"     • {sana_matni} — {html_himoya(guruh_nomi)}")

    matn = "\n".join(qatorlar)
    qolgan = len(yozuvlar) - cheklov
    if qolgan > 0:
        matn += f"\n     <i>...va yana {qolgan} ta</i>"
    return matn
