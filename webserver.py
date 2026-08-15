# webserver.py
# Telegram Mini App uchun kichik web server.
# Bot polling bilan PARALLEL ishlaydi — bir-birini bloklamaydi.

import logging
import os
from pathlib import Path

from aiohttp import web

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
QOLLANMA_FAYL = STATIC_DIR / "qollanma.html"


async def qollanma_handler(request: web.Request) -> web.Response:
    """Qo'llanma sahifasini qaytaradi."""
    if not QOLLANMA_FAYL.exists():
        return web.Response(text="Qo'llanma fayli topilmadi.", status=404)
    return web.FileResponse(
        QOLLANMA_FAYL,
        headers={"Cache-Control": "public, max-age=300"},
    )


async def health_handler(request: web.Request) -> web.Response:
    """Railway healthcheck uchun."""
    return web.Response(text="ok")


def yaratish() -> web.Application:
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/qollanma", qollanma_handler)
    return app


async def ishga_tushirish() -> web.AppRunner:
    """Serverni fon rejimida ishga tushiradi va runner'ni qaytaradi."""
    port = int(os.environ.get("PORT", 8080))
    app = yaratish()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Web server ishga tushdi — port %s", port)
    return runner
