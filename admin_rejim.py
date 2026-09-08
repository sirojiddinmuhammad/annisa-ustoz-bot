# admin_rejim.py
# Admin biror ustoz nomidan botdan foydalanishi uchun.
#
# Nima uchun kerak: ustoz davomat kiritishni unutsa yoki admin bot to'g'ri
# ishlayotganini tekshirmoqchi bo'lsa, uning o'rniga kirib ish bajaradi.
#
# Ishlash tamoyili: barcha handlerlar ustozni `haqiqiy_ustoz()` orqali oladi.
# Admin rejimda bo'lsa, bu funksiya adminning o'zini emas, TANLANGAN ustozni
# qaytaradi. Shu tufayli handlerlarni qayta yozish shart emas.
#
# Rejim xotirada saqlanadi — bot qayta ishga tushganda o'zi tugaydi.
# Bu ataylab: adminning rejimda unutib qolishi xavfli.

import config
import notion_service as ns

# {admin_tg_id: {"ustoz_id": ..., "ismi": ..., "tg_id": int | None}}
_faol_rejim: dict[int, dict] = {}


def rejimda_mi(tg_id: int) -> bool:
    return tg_id in _faol_rejim


def rejim_malumoti(tg_id: int) -> dict | None:
    return _faol_rejim.get(tg_id)


def rejimni_yoqish(admin_tg_id: int, ustoz: dict) -> None:
    ustoz_tg = ns.get_rich_text(ustoz, "Telegram ID")
    _faol_rejim[admin_tg_id] = {
        "ustoz_id": ustoz["id"],
        "ismi": ns.get_title(ustoz, "Ism"),
        "tg_id": int(ustoz_tg) if ustoz_tg and ustoz_tg.isdigit() else None,
    }


def rejimni_ochirish(admin_tg_id: int) -> dict | None:
    return _faol_rejim.pop(admin_tg_id, None)


async def haqiqiy_ustoz(tg_id: int) -> dict | None:
    """Handlerlar ustozni SHU funksiya orqali olishi kerak.

    Admin rejimda bo'lsa — tanlangan ustoz sahifasi qaytadi.
    Aks holda — odatdagidek Telegram ID bo'yicha topiladi.
    """
    malumot = _faol_rejim.get(tg_id)
    if malumot:
        try:
            return await ns.get_page(malumot["ustoz_id"])
        except Exception:
            _faol_rejim.pop(tg_id, None)  # sahifa o'chirilgan bo'lsa rejimni yopamiz

    return await ns.find_ustoz_by_telegram_id(tg_id)


def sarlavha(tg_id: int) -> str:
    """Admin rejimda bo'lsa, har xabar tepasiga qo'yiladigan ogohlantirish.
    Adminning qaysi rejimda ekanini unutib qo'yishining oldini oladi."""
    malumot = _faol_rejim.get(tg_id)
    if not malumot:
        return ""
    return (
        f"👤  <b>{malumot['ismi']}</b> nomidan ishlayapsiz\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
    )


async def ustozni_ogohlantirish(admin_tg_id: int, matn: str, bot) -> None:
    """Admin ustoz nomidan yozuv yaratganda ustozning o'ziga xabar beradi.
    Faqat o'zgarish kiritadigan amallarda chaqiriladi — ko'rish amallarida emas.
    """
    malumot = _faol_rejim.get(admin_tg_id)
    if not malumot or not malumot["tg_id"]:
        return
    try:
        await bot.send_message(
            malumot["tg_id"],
            f"ℹ️  <b>Administrator sizning nomingizdan ish bajardi</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{matn}"
        )
    except Exception:
        pass  # ustoz botni bloklagan bo'lishi mumkin — asosiy ish to'xtamasin


def izoh_qoshimchasi(tg_id: int) -> str:
    """Notion yozuvlariga qo'shiladigan iz — keyinchalik kim kiritganini
    aniqlash uchun."""
    malumot = _faol_rejim.get(tg_id)
    if not malumot:
        return ""
    return f" [Admin kiritdi: {malumot['ismi']} nomidan]"
