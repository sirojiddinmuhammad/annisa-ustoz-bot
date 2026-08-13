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


def summa_format(summa: float) -> str:
    return f"{int(round(summa)):,}".replace(",", " ")
