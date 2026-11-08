"""The countries that get their own gold price page.

units: which weights the local market quotes (see UNITS)
karats: purities shown, most popular first
zones: IANA time zones used to detect a visitor's country in the browser
note: short, factual local market context (keep claims conservative and verifiable)
"""

GRAMS_PER_OUNCE = 31.1034768

UNITS = {
    "gram": ("1 Gram", 1.0),
    "10g": ("10 Grams", 10.0),
    "tola": ("1 Tola", 11.6638),
    "sovereign": ("1 Sovereign (8 g)", 8.0),
    "tael": ("1 Tael", 37.429),
    "ounce": ("1 Ounce", GRAMS_PER_OUNCE),
    "kg": ("1 Kilogram", 1000.0),
}

KARATS = {"24K": 0.999, "22K": 0.9167, "21K": 0.875, "18K": 0.75, "14K": 0.585}

COUNTRIES = [
    {"code": "US", "name": "the USA", "short": "USA", "slug": "usa", "currency": "USD", "symbol": "$",
     "units": ["ounce", "gram", "kg"], "karats": ["24K", "22K", "18K", "14K"],
     "zones": ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "America/Phoenix",
               "America/Anchorage", "Pacific/Honolulu", "America/Detroit", "America/Indiana/Indianapolis"],
     "note": "In the United States, gold is traded in US dollars per troy ounce, the global benchmark unit. "
             "Jewelry is usually sold in 10K, 14K and 18K, while coins and bars are typically 22K or 24K."},
    {"code": "GB", "name": "the UK", "short": "UK", "slug": "uk", "currency": "GBP", "symbol": "£",
     "units": ["gram", "ounce", "kg"], "karats": ["24K", "22K", "18K", "14K"], "zones": ["Europe/London"],
     "note": "In the UK, investment gold is exempt from VAT. The British gold sovereign coin contains about "
             "7.32 grams of pure gold (22K), and UK jewelry is hallmarked by assay offices."},
    {"code": "CA", "name": "Canada", "short": "Canada", "slug": "canada", "currency": "CAD", "symbol": "C$",
     "units": ["ounce", "gram", "kg"], "karats": ["24K", "22K", "18K", "14K"],
     "zones": ["America/Toronto", "America/Vancouver", "America/Edmonton", "America/Winnipeg", "America/Halifax",
               "America/Regina", "America/St_Johns"],
     "note": "Canada is home to the Royal Canadian Mint, whose Gold Maple Leaf coin is minted in 99.99% pure gold. "
             "Prices in Canada move with both the global gold price and the Canadian dollar."},
    {"code": "AU", "name": "Australia", "short": "Australia", "slug": "australia", "currency": "AUD", "symbol": "A$",
     "units": ["ounce", "gram", "kg"], "karats": ["24K", "22K", "18K", "14K"],
     "zones": ["Australia/Sydney", "Australia/Melbourne", "Australia/Brisbane", "Australia/Perth",
               "Australia/Adelaide", "Australia/Hobart", "Australia/Darwin"],
     "note": "Australia is one of the world's largest gold producers, and the Perth Mint is one of its best-known "
             "refiners. Local prices follow the global spot price converted into Australian dollars."},
    {"code": "NZ", "name": "New Zealand", "short": "New Zealand", "slug": "new-zealand", "currency": "NZD",
     "symbol": "NZ$", "units": ["ounce", "gram", "kg"], "karats": ["24K", "22K", "18K", "14K"],
     "zones": ["Pacific/Auckland"],
     "note": "In New Zealand, gold prices follow the global spot price converted into New Zealand dollars."},
    {"code": "IN", "name": "India", "short": "India", "slug": "india", "currency": "INR", "symbol": "₹",
     "units": ["10g", "gram", "sovereign"], "karats": ["24K", "22K", "18K"],
     "zones": ["Asia/Kolkata", "Asia/Calcutta"],
     "note": "India is one of the world's largest gold consumers. Gold rates are usually quoted per 10 grams, "
             "22K is the most popular purity for jewellery, and in South India gold is often counted in sovereigns "
             "(8 grams). Jewellery buyers also pay 3% GST plus making charges."},
    {"code": "PK", "name": "Pakistan", "short": "Pakistan", "slug": "pakistan", "currency": "PKR", "symbol": "Rs",
     "units": ["tola", "10g", "gram"], "karats": ["24K", "22K", "21K", "18K"], "zones": ["Asia/Karachi"],
     "note": "In Pakistan, the gold rate is traditionally quoted per tola (11.66 grams) and per 10 grams, "
             "with 24K and 22K the most commonly quoted purities."},
    {"code": "BD", "name": "Bangladesh", "short": "Bangladesh", "slug": "bangladesh", "currency": "BDT",
     "symbol": "৳", "units": ["tola", "gram"], "karats": ["22K", "21K", "18K"], "zones": ["Asia/Dhaka"],
     "note": "In Bangladesh, gold is commonly priced per vori (bhori), which equals one tola or about 11.66 grams."},
    {"code": "NP", "name": "Nepal", "short": "Nepal", "slug": "nepal", "currency": "NPR", "symbol": "Rs",
     "units": ["tola", "10g", "gram"], "karats": ["24K", "22K"], "zones": ["Asia/Kathmandu", "Asia/Katmandu"],
     "note": "In Nepal, fine gold is usually quoted per tola (11.66 grams)."},
    {"code": "LK", "name": "Sri Lanka", "short": "Sri Lanka", "slug": "sri-lanka", "currency": "LKR", "symbol": "Rs",
     "units": ["sovereign", "gram"], "karats": ["24K", "22K"], "zones": ["Asia/Colombo"],
     "note": "In Sri Lanka, gold is commonly priced per sovereign or pawn, which equals 8 grams."},
    {"code": "AE", "name": "the UAE", "short": "UAE", "slug": "uae", "currency": "AED", "symbol": "AED",
     "units": ["gram", "tola", "ounce"], "karats": ["24K", "22K", "21K", "18K"], "zones": ["Asia/Dubai"],
     "note": "The UAE dirham is pegged to the US dollar at 3.6725, so local prices track the global gold price "
             "closely. Dubai is a major gold trading hub, and retail prices are quoted per gram for 24K, 22K, 21K and 18K."},
    {"code": "SA", "name": "Saudi Arabia", "short": "Saudi Arabia", "slug": "saudi-arabia", "currency": "SAR",
     "symbol": "SAR", "units": ["gram", "ounce", "kg"], "karats": ["24K", "22K", "21K", "18K"], "zones": ["Asia/Riyadh"],
     "note": "The Saudi riyal is pegged to the US dollar at 3.75. In Saudi Arabia, 21K is widely used for jewelry, "
             "and prices are quoted per gram."},
    {"code": "QA", "name": "Qatar", "short": "Qatar", "slug": "qatar", "currency": "QAR", "symbol": "QAR",
     "units": ["gram", "ounce"], "karats": ["24K", "22K", "21K", "18K"], "zones": ["Asia/Qatar"],
     "note": "The Qatari riyal is pegged to the US dollar at 3.64, so local gold prices follow the global price closely."},
    {"code": "KW", "name": "Kuwait", "short": "Kuwait", "slug": "kuwait", "currency": "KWD", "symbol": "KWD",
     "units": ["gram", "ounce"], "karats": ["24K", "22K", "21K", "18K"], "zones": ["Asia/Kuwait"],
     "note": "In Kuwait, gold prices are quoted in Kuwaiti dinars per gram for the main purities."},
    {"code": "OM", "name": "Oman", "short": "Oman", "slug": "oman", "currency": "OMR", "symbol": "OMR",
     "units": ["gram", "ounce"], "karats": ["24K", "22K", "21K", "18K"], "zones": ["Asia/Muscat"],
     "note": "The Omani rial is pegged to the US dollar, so local gold prices track the global price closely."},
    {"code": "BH", "name": "Bahrain", "short": "Bahrain", "slug": "bahrain", "currency": "BHD", "symbol": "BHD",
     "units": ["gram", "ounce"], "karats": ["24K", "22K", "21K", "18K"], "zones": ["Asia/Bahrain"],
     "note": "The Bahraini dinar is pegged to the US dollar, so local gold prices follow the global price closely."},
    {"code": "EG", "name": "Egypt", "short": "Egypt", "slug": "egypt", "currency": "EGP", "symbol": "EGP",
     "units": ["gram", "ounce"], "karats": ["24K", "21K", "18K"], "zones": ["Africa/Cairo"],
     "note": "In Egypt, 21K is the most traded purity for jewelry, and prices are quoted in Egyptian pounds per gram."},
    {"code": "JO", "name": "Jordan", "short": "Jordan", "slug": "jordan", "currency": "JOD", "symbol": "JOD",
     "units": ["gram", "ounce"], "karats": ["24K", "21K", "18K"], "zones": ["Asia/Amman"],
     "note": "The Jordanian dinar is pegged to the US dollar, and gold is quoted per gram, with 21K popular for jewelry."},
    {"code": "TR", "name": "Turkey", "short": "Turkey", "slug": "turkey", "currency": "TRY", "symbol": "₺",
     "units": ["gram", "ounce"], "karats": ["24K", "22K", "18K", "14K"], "zones": ["Europe/Istanbul"],
     "note": "Gold is a popular way to save in Turkey. Gram gold (gram altın) is widely quoted, and Turkish lira "
             "movements have a large effect on local prices."},
    {"code": "MY", "name": "Malaysia", "short": "Malaysia", "slug": "malaysia", "currency": "MYR", "symbol": "RM",
     "units": ["gram", "ounce"], "karats": ["24K", "22K", "18K"], "zones": ["Asia/Kuala_Lumpur"],
     "note": "In Malaysia, 24K gold is often labeled 999 and 22K gold 916, and prices are quoted per gram in ringgit."},
    {"code": "SG", "name": "Singapore", "short": "Singapore", "slug": "singapore", "currency": "SGD", "symbol": "S$",
     "units": ["gram", "ounce", "kg"], "karats": ["24K", "22K", "18K"], "zones": ["Asia/Singapore"],
     "note": "Singapore exempts investment-grade gold from GST, and it is a regional hub for precious metals trading."},
    {"code": "PH", "name": "the Philippines", "short": "Philippines", "slug": "philippines", "currency": "PHP",
     "symbol": "₱", "units": ["gram", "ounce"], "karats": ["24K", "22K", "18K", "14K"], "zones": ["Asia/Manila"],
     "note": "In the Philippines, gold is quoted per gram in pesos, and prices follow the global spot price."},
    {"code": "ID", "name": "Indonesia", "short": "Indonesia", "slug": "indonesia", "currency": "IDR", "symbol": "Rp",
     "units": ["gram", "ounce"], "karats": ["24K", "22K", "18K"],
     "zones": ["Asia/Jakarta", "Asia/Makassar", "Asia/Jayapura", "Asia/Pontianak"],
     "note": "In Indonesia, gold is widely bought in small bars and quoted per gram in rupiah."},
    {"code": "HK", "name": "Hong Kong", "short": "Hong Kong", "slug": "hong-kong", "currency": "HKD", "symbol": "HK$",
     "units": ["tael", "gram", "ounce"], "karats": ["24K", "22K", "18K"], "zones": ["Asia/Hong_Kong"],
     "note": "In Hong Kong, gold is traditionally priced per tael (about 37.43 grams). The Hong Kong dollar is "
             "linked to the US dollar."},
    {"code": "ZA", "name": "South Africa", "short": "South Africa", "slug": "south-africa", "currency": "ZAR",
     "symbol": "R", "units": ["ounce", "gram", "kg"], "karats": ["24K", "22K", "18K"], "zones": ["Africa/Johannesburg"],
     "note": "South Africa is a historic gold producer and home of the Krugerrand, a one-ounce gold coin."},
    {"code": "NG", "name": "Nigeria", "short": "Nigeria", "slug": "nigeria", "currency": "NGN", "symbol": "₦",
     "units": ["gram", "ounce"], "karats": ["24K", "22K", "18K"], "zones": ["Africa/Lagos"],
     "note": "In Nigeria, gold prices in naira depend heavily on the naira exchange rate as well as the global price."},
    {"code": "KE", "name": "Kenya", "short": "Kenya", "slug": "kenya", "currency": "KES", "symbol": "KSh",
     "units": ["gram", "ounce"], "karats": ["24K", "22K", "18K"], "zones": ["Africa/Nairobi"],
     "note": "In Kenya, gold is quoted per gram in shillings and follows the global spot price."},
    {"code": "GH", "name": "Ghana", "short": "Ghana", "slug": "ghana", "currency": "GHS", "symbol": "GH₵",
     "units": ["gram", "ounce"], "karats": ["24K", "22K", "18K"], "zones": ["Africa/Accra"],
     "note": "Ghana is Africa's largest gold producer, and local prices follow the global price converted into cedis."},
    {"code": "EU", "name": "Europe (Euro)", "short": "Europe", "slug": "europe", "currency": "EUR", "symbol": "€",
     "units": ["gram", "ounce", "kg"], "karats": ["24K", "22K", "18K", "14K"],
     "zones": ["Europe/Berlin", "Europe/Paris", "Europe/Madrid", "Europe/Rome", "Europe/Amsterdam", "Europe/Brussels",
               "Europe/Vienna", "Europe/Dublin", "Europe/Lisbon", "Europe/Athens", "Europe/Helsinki"],
     "note": "In the euro area, investment gold is generally exempt from VAT, and prices follow the global price "
             "converted into euros."},
]

BY_CODE = {c["code"]: c for c in COUNTRIES}


def weights_for(c):
    """Rows of the price-by-weight table: everyday sizes plus the local traditional units."""
    rows = [("1 Gram", 1.0)]
    if "sovereign" in c["units"]:
        rows.append(("1 Sovereign (8 g)", 8.0))
    rows.append(("10 Grams", 10.0))
    if "tola" in c["units"]:
        rows.append(("1 Tola (11.66 g)", 11.6638))
    rows.append(("20 Grams", 20.0))
    if "tael" in c["units"]:
        rows.append(("1 Tael (37.43 g)", 37.429))
    rows += [("1 Troy Ounce (31.1 g)", GRAMS_PER_OUNCE), ("50 Grams", 50.0), ("100 Grams", 100.0),
             ("250 Grams", 250.0), ("Half Kilo (500 g)", 500.0), ("1 Kilogram", 1000.0)]
    return sorted(rows, key=lambda r: r[1])

# Blogger caps a blog at about 24 live static pages, so only the biggest gold markets get their
# own page. Every other country is still served by the auto-detecting widget on the hub page.
PAGE_CODES = ["AE", "SA", "QA", "KW", "OM", "BH", "IN", "PK", "BD", "NP", "LK", "US", "GB", "CA", "AU", "NZ"]
PAGE_COUNTRIES = [BY_CODE[code] for code in PAGE_CODES]
