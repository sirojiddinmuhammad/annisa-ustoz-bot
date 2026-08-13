# Annisaa Markazi — Ustozlar Boti

Telegram bot orqali ustozlar davomat oladi, dars qoldiradi, ta'til oladi va
o'z balansini ko'radi. Barcha ma'lumot Notion CRM'ga yoziladi.

## O'rnatishdan oldin — Notionda bajarilishi shart bo'lgan ishlar

Bot ishlashi uchun **Ustozlar** bazasiga ikkita yangi maydon qo'shilishi kerak
(hozircha qo'shilmagan):

| Maydon | Turi |
|---|---|
| Ta'til boshlanishi | Date |
| Ta'til tugashi | Date |

Bundan tashqari **Telegram ID** maydoni Ustozlar bazasida **Text (rich_text)**
turida bo'lishi kerak — kod shunga mo'ljallangan.

## O'rnatish (lokal test uchun)

```bash
pip install -r requirements.txt --break-system-packages
cp .env.example .env   # va qiymatlarni to'ldiring
export $(cat .env | xargs)
python main.py
```

## Railway'ga joylash

1. Yangi Railway loyiha yarating, shu papkani GitHub repo sifatida ulang.
2. Railway → Variables bo'limida quyidagilarni kiriting:
   - `BOT_TOKEN`
   - `NOTION_TOKEN`
   - `ADMIN_ID`
3. Railway `Procfile`ni o'zi taniydi (`worker: python main.py`).

## Loyiha tuzilmasi

```
config.py            — barcha sozlamalar, Notion baza ID'lari
notion_service.py     — Notion API bilan ishlaydigan barcha funksiyalar
money_service.py       — pul hisobini Python orqali qayta hisoblash (zaxira)
states.py              — FSM holatlari
keyboards.py           — barcha inline klaviaturalar
utils.py                — sana formatlash va h.k.
scheduler.py            — kunlik avtomatik vazifalar (02:20, 23:00)
main.py                 — kirish nuqtasi
handlers/
  registration.py       — /start, ro'yxatdan o'tish
  davomat.py             — davomat kiritish/tahrirlash/o'chirish
  dars_qoldirish.py      — dars qoldirish
  tatil.py                — ustoz ta'tili
  balansim.py             — balans ko'rish
  bugungi.py               — bugungi darslar ro'yxati
```

## Ma'lum cheklovlar va eslatmalar

- **Formula/rollup qiymatlari API orqali o'qilmaydi** ("omitted" muammosi).
  Shuning uchun Davomatga yozilganda pul avtomatik Notion formulasi orqali
  hisoblanadi (bot faqat kerak bo'lganda "Qo'lda summa" / "Qo'lda ustoz
  ulushi" yozadi), "Balansim" uchun esa bot xom ma'lumotdan o'zi qayta
  hisoblaydi (`money_service.py`).
- **Kutayotgan ro'yxatdan o'tish so'rovlari** xotirada (`PENDING_REGISTRATIONS`)
  saqlanadi — bot qayta ishga tushsa, tasdiqlanmagan so'rovlar yo'qoladi,
  ustoz qayta `/start` bosishi kerak bo'ladi.
- **"Dars kunlari"** va **"Sabab"** maydonlari Notionda **multi-select** deb
  faraz qilingan, qiymatlar `utils.HAFTA_KUNLARI` bilan bir xil yozilishda
  bo'lishi kerak (masalan "Payshanba", "Juma").
- **Admin funksiyalari** (kunlik hisobot, ro'yxatdan o'tish tasdig'i, turli
  xabarlar) hozircha shu botning o'zida, `ADMIN_ID` orqali ishlaydi. Kelishilgan
  reja bo'yicha bular keyinchalik **alohida Admin botga** ko'chiriladi.
- **Notion API cheklovi** — sekundiga ~3 so'rov. Guruh kattaligiga qarab
  davomat saqlash bir necha soniya davom etishi mumkin, bu normal holat.
