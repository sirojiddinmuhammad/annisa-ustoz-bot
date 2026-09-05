# admin_xabar.py
# Adminga ketadigan barcha bildirishnomalar shu yerdan o'tadi.
#
# Agar ADMIN_BOT_TOKEN berilgan bo'lsa, xabar ADMIN BOT nomidan yuboriladi —
# shunda hamma admin bildirishnomalari bir joyda to'planadi va ustozlar
# botining chatida aralashib yotmaydi.
#
# Token berilmagan bo'lsa yoki admin bot javob bermasa, xabar eskicha
# ustozlar boti orqali yuboriladi. Ya'ni bildirishnoma hech qachon
# yo'qolmaydi — bu muhim, chunki ular pul va davomat bilan bog'liq.

import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config

logger = logging.getLogger(__name__)

# Admin bot ulanishi bir marta yaratiladi va qayta ishlatiladi
_admin_bot: Bot | None = None


def _olish() -> Bot | None:
    global _admin_bot
    if not config.ADMIN_BOT_TOKEN:
        return None
    if _admin_bot is None:
        _admin_bot = Bot(
            token=config.ADMIN_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return _admin_bot


async def yuborish(matn: str, bot: Bot | None = None, reply_markup=None) -> None:
    """Adminga xabar yuboradi.

    bot — ustozlar botining nusxasi (zaxira yo'l uchun). Berilmasa va admin
    bot ham sozlanmagan bo'lsa, xabar yuborilmaydi, faqat logga yoziladi.
    """
    admin_bot = _olish()

    if admin_bot is not None:
        try:
            await admin_bot.send_message(config.ADMIN_ID, matn,
                                          reply_markup=reply_markup)
            return
        except Exception as e:
            # Admin bot ishlamasa ham xabar yo'qolmasin — ustozlar boti orqali
            logger.warning("Admin botga yuborib bo'lmadi: %s", e)

    if bot is not None:
        try:
            await bot.send_message(config.ADMIN_ID, matn, reply_markup=reply_markup)
        except Exception as e:
            logger.error("Adminga xabar yuborilmadi: %s", e)
    else:
        logger.error("Adminga xabar yuborilmadi (bot yo'q): %s", matn[:80])


async def yopish() -> None:
    """Bot to'xtaganda admin bot ulanishini yopadi."""
    global _admin_bot
    if _admin_bot is not None:
        try:
            await _admin_bot.session.close()
        except Exception:
            pass
        _admin_bot = None
