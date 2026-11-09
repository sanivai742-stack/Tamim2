import asyncio, os, random, secrets, logging, time
import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton)
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
NP_KEY = os.environ["NP_API_KEY"]
NP_API = "https://www.npnetworkbd.cam/api/user"
OTP_GROUP_URL = os.getenv("OTP_GROUP_URL", "https://t.me/yourgroup")
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/yoursupport")
NUMBERS_PER_REQUEST = int(os.getenv("NUMBERS_PER_REQUEST", "3"))  # প্রতি getnum এ ১টা নাম্বার বরাদ্দ হয়
POLL_SECONDS = 3          # docs: প্রতি ৩ সেকেন্ডে inbox চেক
POLL_TIMEOUT = 300        # ৫ মিনিট

COUNTRY_DATA = """1 US USA/Canada|7 RU Russia|76 KZ Kazakhstan|77 KZ Kazakhstan|20 EG Egypt|27 ZA South Africa|30 GR Greece|31 NL Netherlands|32 BE Belgium|33 FR France|34 ES Spain|36 HU Hungary|39 IT Italy|40 RO Romania|41 CH Switzerland|43 AT Austria|44 GB UK|45 DK Denmark|46 SE Sweden|47 NO Norway|48 PL Poland|49 DE Germany|51 PE Peru|52 MX Mexico|53 CU Cuba|54 AR Argentina|55 BR Brazil|56 CL Chile|57 CO Colombia|58 VE Venezuela|60 MY Malaysia|61 AU Australia|62 ID Indonesia|63 PH Philippines|64 NZ New Zealand|65 SG Singapore|66 TH Thailand|81 JP Japan|82 KR South Korea|84 VN Vietnam|86 CN China|90 TR Turkey|91 IN India|92 PK Pakistan|93 AF Afghanistan|94 LK Sri Lanka|95 MM Myanmar|98 IR Iran|211 SS South Sudan|212 MA Morocco|213 DZ Algeria|216 TN Tunisia|218 LY Libya|220 GM Gambia|221 SN Senegal|222 MR Mauritania|223 ML Mali|224 GN Guinea|225 CI Ivory Coast|226 BF Burkina Faso|227 NE Niger|228 TG Togo|229 BJ Benin|230 MU Mauritius|231 LR Liberia|232 SL Sierra Leone|233 GH Ghana|234 NG Nigeria|235 TD Chad|236 CF Central African Rep.|237 CM Cameroon|238 CV Cape Verde|239 ST Sao Tome|240 GQ Equatorial Guinea|241 GA Gabon|242 CG Congo|243 CD DR Congo|244 AO Angola|245 GW Guinea-Bissau|248 SC Seychelles|249 SD Sudan|250 RW Rwanda|251 ET Ethiopia|252 SO Somalia|253 DJ Djibouti|254 KE Kenya|255 TZ Tanzania|256 UG Uganda|257 BI Burundi|258 MZ Mozambique|260 ZM Zambia|261 MG Madagascar|262 RE Reunion|263 ZW Zimbabwe|264 NA Namibia|265 MW Malawi|266 LS Lesotho|267 BW Botswana|268 SZ Eswatini|269 KM Comoros|291 ER Eritrea|351 PT Portugal|352 LU Luxembourg|353 IE Ireland|354 IS Iceland|355 AL Albania|356 MT Malta|357 CY Cyprus|358 FI Finland|359 BG Bulgaria|370 LT Lithuania|371 LV Latvia|372 EE Estonia|373 MD Moldova|374 AM Armenia|375 BY Belarus|376 AD Andorra|377 MC Monaco|378 SM San Marino|380 UA Ukraine|381 RS Serbia|382 ME Montenegro|383 XK Kosovo|385 HR Croatia|386 SI Slovenia|387 BA Bosnia|389 MK North Macedonia|420 CZ Czechia|421 SK Slovakia|423 LI Liechtenstein|500 FK Falkland Is.|501 BZ Belize|502 GT Guatemala|503 SV El Salvador|504 HN Honduras|505 NI Nicaragua|506 CR Costa Rica|507 PA Panama|509 HT Haiti|591 BO Bolivia|592 GY Guyana|593 EC Ecuador|595 PY Paraguay|597 SR Suriname|598 UY Uruguay|670 TL Timor-Leste|673 BN Brunei|674 NR Nauru|675 PG Papua New Guinea|676 TO Tonga|677 SB Solomon Is.|678 VU Vanuatu|679 FJ Fiji|685 WS Samoa|686 KI Kiribati|852 HK Hong Kong|853 MO Macau|855 KH Cambodia|856 LA Laos|880 BD Bangladesh|886 TW Taiwan|960 MV Maldives|961 LB Lebanon|962 JO Jordan|963 SY Syria|964 IQ Iraq|965 KW Kuwait|966 SA Saudi Arabia|967 YE Yemen|968 OM Oman|970 PS Palestine|971 AE UAE|972 IL Israel|973 BH Bahrain|974 QA Qatar|975 BT Bhutan|976 MN Mongolia|977 NP Nepal|992 TJ Tajikistan|993 TM Turkmenistan|994 AZ Azerbaijan|995 GE Georgia|996 KG Kyrgyzstan|998 UZ Uzbekistan"""


def _flag(iso: str) -> str:
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in iso)


PREFIX_COUNTRY = {}
for _item in COUNTRY_DATA.split("|"):
    _code, _iso, _name = _item.strip().split(" ", 2)
    PREFIX_COUNTRY[_code] = f"{_flag(_iso)} {_name}"

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
state: dict[int, dict] = {}
polls: dict[int, asyncio.Task] = {}


def country_of(rng: str) -> str:
    for L in (3, 2, 1):
        if rng[:L] in PREFIX_COUNTRY:
            return PREFIX_COUNTRY[rng[:L]]
    return "🌍 " + rng


async def np_call(action: str, body: dict | None = None) -> dict:
    headers = {"mauthapi": NP_KEY}
    try:
        async with httpx.AsyncClient(timeout=30) as h:
            if body is None:
                r = await h.get(NP_API, params={"action": action}, headers=headers)
            else:
                r = await h.post(NP_API, json={"action": action, **body}, headers=headers)
        return r.json()
    except Exception as e:
        logging.error("NP API error: %s", e)
        return {}


def main_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="☎️ GET NUMBER")],
        [KeyboardButton(text="💰 BALANCE"), KeyboardButton(text="📊 LIVE TRAFFIC")],
        [KeyboardButton(text="⚙️ TOOLS"), KeyboardButton(text="🟢 SUPPORT")],
    ])


@dp.message(CommandStart())
async def start(m: Message):
    await m.answer("👋 Welcome Dear\n\n👇 Select An Option To Use Our Bot", reply_markup=main_kb())


SERVICE_MENU = [  # (বাটনের লেখা, প্যানেলের sid) - প্যানেলে sid অন্য হলে এখানে বদলান
    ("🔑 FB FORGOT", "FACEBOOK"),
    ("📘 FACEBOOK", "FACEBOOK"),
    ("🟢 WHATSAPP", "WHATSAPP"),
    ("📸 INSTAGRAM", "INSTAGRAM"),
]

# ISO: (কান্ট্রি কোড, নাম) - রেঞ্জ এই কোড দিয়ে শুরু হলে ওই দেশের ধরা হবে
COUNTRIES = {
    "IT": ("39", "Italy"),
    "FR": ("33", "France"),
    "ET": ("251", "Ethiopia"),
    "CM": ("237", "Cameroon"),
    "AM": ("374", "Armenia"),
    "MG": ("261", "Madagascar"),
    "NG": ("234", "Nigeria"),
}


async def load_live(uid: int) -> dict:
    d = await np_call("liveaccess")
    services = (d.get("data") or {}).get("services") or []
    live = {s["sid"].upper(): s.get("ranges") or [] for s in services}
    state.setdefault(uid, {})["live"] = live
    return live


def country_ranges(uid: int) -> dict:
    st = state.get(uid) or {}
    rs = (st.get("live") or {}).get(st.get("sid", ""), [])
    out = {}
    for iso, (code, _name) in COUNTRIES.items():
        found = [r for r in rs if r.startswith(code)]
        if found:
            out[iso] = found
    return out


def services_kb():
    rows = []
    for i in range(0, len(SERVICE_MENU), 2):
        rows.append([InlineKeyboardButton(text=SERVICE_MENU[j][0], callback_data=f"svc:{j}")
                     for j in range(i, min(i + 2, len(SERVICE_MENU)))])
    rows.append([InlineKeyboardButton(text="❌ CLOSE", callback_data="close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def countries_kb(cr: dict):
    btns = [InlineKeyboardButton(text=f"{_flag(iso)} {iso} · {len(rs)}", callback_data=f"ct:{iso}")
            for iso, rs in cr.items()]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    rows.append([InlineKeyboardButton(text="⬅️ BACK", callback_data="back")])
    rows.append([InlineKeyboardButton(text="❌ CLOSE", callback_data="close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def countries_text(label: str, cr: dict) -> str:
    lines = [f"📍 Select a country for {label}:", ""]
    for iso, rs in cr.items():
        shown = ", ".join(rs[:4]) + (" …" if len(rs) > 4 else "")
        lines.append(f"{_flag(iso)} {COUNTRIES[iso][1]} ({len(rs)}): {shown}")
    return "\n".join(lines)


async def show_countries(c: CallbackQuery):
    uid = c.from_user.id
    st = state.get(uid) or {}
    if "sid" not in st:
        await c.answer("আবার GET NUMBER চাপুন", show_alert=True)
        return
    await load_live(uid)
    cr = country_ranges(uid)
    if not cr:
        await c.message.edit_text(f"❌ {st['label']} এ এখন কোনো দেশের রেঞ্জ লাইভ নেই।",
                                  reply_markup=countries_kb({}))
        await c.answer()
        return
    await c.message.edit_text(countries_text(st["label"], cr), reply_markup=countries_kb(cr))
    await c.answer()


@dp.message(F.text == "☎️ GET NUMBER")
async def get_number(m: Message):
    await m.answer("📍 Select a service:", reply_markup=services_kb())


@dp.callback_query(F.data == "back")
async def back(c: CallbackQuery):
    await c.message.edit_text("📍 Select a service:", reply_markup=services_kb())
    await c.answer()


@dp.callback_query(F.data == "close")
async def close(c: CallbackQuery):
    uid = c.from_user.id
    if uid in polls:
        polls.pop(uid).cancel()
    try:
        await c.message.delete()
    except Exception:
        pass
    await c.answer()


@dp.callback_query(F.data.startswith("svc:"))
async def pick_service(c: CallbackQuery):
    j = int(c.data.split(":")[1])
    label, sid = SERVICE_MENU[j]
    st = state.setdefault(c.from_user.id, {})
    st["sid"], st["label"] = sid, label
    await show_countries(c)


@dp.callback_query(F.data == "chgc")
async def change_country(c: CallbackQuery):
    await show_countries(c)


@dp.callback_query(F.data.startswith("ct:"))
async def pick_country(c: CallbackQuery):
    st = state.setdefault(c.from_user.id, {})
    st["iso"] = c.data.split(":")[1]
    await allocate(c)


@dp.callback_query(F.data == "chg")
async def change_number(c: CallbackQuery):
    if "iso" not in (state.get(c.from_user.id) or {}):
        await c.answer("আবার GET NUMBER চাপুন", show_alert=True)
        return
    await allocate(c)


def number_kb(nums, otp=None):
    rows = []
    if otp:
        rows.append([InlineKeyboardButton(text=f"🔑 Copy OTP: {otp}", copy_text=CopyTextButton(text=str(otp)))])
    rows += [[InlineKeyboardButton(text=f"📋 +{n}", copy_text=CopyTextButton(text=f"+{n}"))] for n in nums]
    rows += [
        [InlineKeyboardButton(text="🔄 Change Number", callback_data="chg")],
        [InlineKeyboardButton(text="🌍 Change Country", callback_data="chgc")],
        [InlineKeyboardButton(text="🔔 Otp Group", url=OTP_GROUP_URL)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def allocate(c: CallbackQuery):
    uid = c.from_user.id
    st = state[uid]
    iso = st["iso"]
    if uid in polls:
        polls.pop(uid).cancel()
    await c.answer("⏳ নাম্বার আনছি...")

    await load_live(uid)
    ranges = country_ranges(uid).get(iso, [])
    if not ranges:
        await c.message.answer("❌ এই দেশের রেঞ্জ এখন লাইভ নেই, অন্য দেশ বাছুন।")
        return

    nums, used, last_msg = [], [], ""
    attempts = 0
    while len(nums) < NUMBERS_PER_REQUEST and attempts < NUMBERS_PER_REQUEST + len(ranges) + 2:
        attempts += 1
        rng = random.choice(ranges)
        res = await np_call("getnum", {"range": rng, "requestId": secrets.token_hex(8)})
        meta = res.get("meta") or {}
        if meta.get("code") == 200 and res.get("data"):
            n = res["data"]["no_plus_number"]
            if n not in nums:
                nums.append(n)
                used.append(rng)
        else:
            last_msg = res.get("message") or "No number"
    if not nums:
        await c.message.answer(f"❌ নাম্বার পাওয়া যায়নি: {last_msg}")
        return

    head = (f"{_flag(iso)} {COUNTRIES[iso][1]} · {st['label']}\n"
            f"📡 Range: {', '.join(sorted(set(used)))}\n\n")
    msg = await c.message.edit_text(head + "⏳ Waiting for OTP...", reply_markup=number_kb(nums))
    polls[uid] = asyncio.create_task(poll_otp(uid, msg, head, nums))


async def poll_otp(uid: int, msg: Message, head: str, nums: list[str]):
    deadline = time.time() + POLL_TIMEOUT
    try:
        while time.time() < deadline:
            await asyncio.sleep(POLL_SECONDS)
            d = await np_call("inbox")
            for n in d.get("numbers") or []:
                if n.get("number") in nums and n.get("otp"):
                    await msg.edit_text(f"{head}✅ +{n['number']}\n🔑 OTP: <code>{n['otp']}</code>",
                                        parse_mode="HTML", reply_markup=number_kb(nums, otp=n["otp"]))
                    return
        await msg.edit_text(head + "⏰ OTP আসেনি। Change Number চাপুন।", reply_markup=number_kb(nums))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logging.error("poll error: %s", e)
    finally:
        if polls.get(uid) is asyncio.current_task():
            polls.pop(uid, None)


@dp.message(F.text == "📊 LIVE TRAFFIC")
async def live(m: Message):
    d = await np_call("liveaccess")
    services = (d.get("data") or {}).get("services") or []
    if not services:
        await m.answer("কোনো লাইভ ট্রাফিক নেই।")
        return
    lines = []
    for s in services:
        ago = int(time.time() - s["last_at"] / 1000)
        lines.append(f"• <b>{s['sid']}</b> — {len(s['ranges'])} ranges, last {ago // 60}m ago")
    await m.answer("📊 Live Traffic\n\n" + "\n".join(lines), parse_mode="HTML")


@dp.message(F.text == "💰 BALANCE")
async def balance(m: Message):
    await m.answer("💰 Balance: 0.00")  # ইউজার ব্যালেন্স সিস্টেম পরে যোগ হবে


@dp.message(F.text == "🟢 SUPPORT")
async def support(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Contact", url=SUPPORT_URL)]])
    await m.answer("Support:", reply_markup=kb)


@dp.message(F.text == "⚙️ TOOLS")
async def tools(m: Message):
    await m.answer("⚙️ Tools coming soon")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
