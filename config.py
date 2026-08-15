# config.py
# Barcha sozlamalar va Notion baza ID'lari shu yerda saqlanadi.

import os
from zoneinfo import ZoneInfo

# --- Telegram tokenlari (Railway Variables orqali beriladi) ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

# Mini App havolasi. Railway'da domen yaratilgach shu ko'rinishda beriladi:
#   https://loyiha-nomi.up.railway.app/qollanma
# Bo'sh bo'lsa bot ishlaydi, faqat qo'llanma tugmasi ogohlantirish beradi.
# Diqqat: Telegram Mini App faqat HTTPS qabul qiladi — http:// bo'lsa
# Telegram tugmani rad etadi va bot xato beradi, shuning uchun tekshiramiz.
_webapp_url = os.environ.get("WEBAPP_URL", "").strip()
WEBAPP_URL = _webapp_url if _webapp_url.startswith("https://") else ""

# --- Vaqt zonasi ---
TASHKENT_TZ = ZoneInfo("Asia/Tashkent")

# --- Notion baza (data source) ID'lari ---
DB_USTOZLAR = "952ac188-93a2-433a-98bd-628028b69e23"
DB_GURUHLAR = "1fa6f318-9629-4970-a2fd-4e133c02a204"
DB_TALABALAR = "d9ce3228-ad86-49ed-b2fb-61319165eb82"
DB_YOZILISHLAR = "83a9b84e-2ef0-4d9f-906e-a7584b702d4e"
DB_DAVOMAT = "425e5738-e16f-4d32-9f64-05002fa4fda6"
DB_CHEGIRMALAR = "5cdeb330-526e-409b-b6c3-1333489f301a"
DB_OYLIKLAR = "60fcb464-f409-458a-b630-79585f56fae6"
DB_DARSLAR_GRAFIGI = "d72512cc-8544-40d5-91af-0703a789cf01"
DB_ARXIV = "28e0c58e-711a-4632-a27e-4ac73548eb85"

# --- Ish qoidalari (biznes konstantalar) ---

# Davomatni "o'chirish" faqat shu muddat ichida kiritilgan yozuvlar uchun ishlaydi
DAVOMAT_OCHIRISH_MUDDATI_KUN = 7

# Yangi talaba belgisi (🆕) uchun: Yozilish "Boshlagan sana"si shu necha kun ichida bo'lsa
YANGI_TALABA_MUDDATI_KUN = 7

# "Belgilanmagan" darslarni ogohlantirish uchun qanchа orqaga qarab tekshiriladi
BELGILANMAGAN_TEKSHIRUV_KUN = 14

# Kunlik ishlar vaqti (Asia/Tashkent)
ERTALABKI_ESLATMA_SOAT = 2
ERTALABKI_ESLATMA_DAQIQA = 20

KUNLIK_HISOBOT_SOAT = 23
KUNLIK_HISOBOT_DAQIQA = 0

# --- Davomat Holat qiymatlari (Notion select variantlari) ---
HOLAT_KELDI = "Darsda qatnashdi"
HOLAT_KELMADI = "Darsga kelmadi"
HOLAT_SABABLI = "Sababli"
HOLAT_OYLIK_HISOB = "Oylik hisob"

# --- Yozilish Holat qiymatlari ---
YOZILISH_OQIYABDI = "O'qiyabdi"
YOZILISH_TATILDA = "Ta'tilda"
YOZILISH_TUGATDI = "Tugatdi"

# --- Darslar grafigi Holat qiymatlari ---
GRAFIK_BELGILANMAGAN = "Belgilanmagan"
GRAFIK_DARS_OTILDI = "Dars o'tildi"
GRAFIK_DARS_QOLDIRILDI = "Dars qoldirildi"

# --- Dars qoldirish sabablari ---
SABAB_KASALLIK = "Kasallik"
SABAB_SAYOHAT = "Sayohat"
SABAB_OILAVIY = "Oilaviy sabab"
SABAB_TEXNIK = "Texnik muammo"
SABAB_BOSHQA = "Boshqa"
SABAB_TATIL = "Ta'til"

SABABLAR_RO_YXATI = [
    SABAB_KASALLIK,
    SABAB_SAYOHAT,
    SABAB_OILAVIY,
    SABAB_TEXNIK,
    SABAB_BOSHQA,
]

# --- Chegirmalar "Kim ko'taradi" qiymatlari ---
CHEGIRMA_MARKAZ_USTOZ = "Markaz/Ustoz"
CHEGIRMA_MARKAZ_ZARARIGA = "Markaz zarariga"
CHEGIRMA_MARKAZ_BEZARAR = "Markaz bezarar"

# --- Guruh holati ---
GURUH_FAOL = "Faol"
GURUH_BOSHLANMAGAN = "Boshlanmagan"
GURUH_TUGAGAN = "Tugagan"

# --- Chegirma holati ---
CHEGIRMA_FAOL = "Faol"
CHEGIRMA_TUGAGAN = "Tugagan"
