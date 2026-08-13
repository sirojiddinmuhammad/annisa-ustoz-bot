# utils.py
# Kichik yordamchi funksiyalar.

from datetime import date, timedelta

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
    kun = date.today()
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
