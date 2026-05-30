"""
Datos de pais para calculo de WACC.
Basado en tabla de Damodaran Country Risk Premium (2024).
Tasa libre de riesgo = bono soberano 10 anios.
CRP = prima de riesgo pais (EMBI+ o equivalente CDS).
"""

COUNTRY_DB: dict = {
    "United States": {
        "nombre": "Estados Unidos", "rf": 0.0457, "crp": 0.00,
        "tax_rate": 0.21, "mkt_premium": 0.055, "currency": "USD",
    },
    "Colombia": {
        "nombre": "Colombia", "rf": 0.1150, "crp": 0.0285,
        "tax_rate": 0.35, "mkt_premium": 0.065, "currency": "COP",
    },
    "Mexico": {
        "nombre": "Mexico", "rf": 0.0980, "crp": 0.0168,
        "tax_rate": 0.30, "mkt_premium": 0.060, "currency": "MXN",
    },
    "Brazil": {
        "nombre": "Brasil", "rf": 0.1290, "crp": 0.0330,
        "tax_rate": 0.34, "mkt_premium": 0.065, "currency": "BRL",
    },
    "Chile": {
        "nombre": "Chile", "rf": 0.0620, "crp": 0.0075,
        "tax_rate": 0.27, "mkt_premium": 0.057, "currency": "CLP",
    },
    "Peru": {
        "nombre": "Peru", "rf": 0.0780, "crp": 0.0165,
        "tax_rate": 0.30, "mkt_premium": 0.062, "currency": "PEN",
    },
    "Argentina": {
        "nombre": "Argentina", "rf": 0.2200, "crp": 0.1850,
        "tax_rate": 0.35, "mkt_premium": 0.090, "currency": "ARS",
    },
    "Canada": {
        "nombre": "Canada", "rf": 0.0370, "crp": 0.00,
        "tax_rate": 0.265, "mkt_premium": 0.055, "currency": "CAD",
    },
    "United Kingdom": {
        "nombre": "Reino Unido", "rf": 0.0425, "crp": 0.00,
        "tax_rate": 0.25, "mkt_premium": 0.055, "currency": "GBP",
    },
    "Germany": {
        "nombre": "Alemania", "rf": 0.0260, "crp": 0.00,
        "tax_rate": 0.298, "mkt_premium": 0.055, "currency": "EUR",
    },
    "France": {
        "nombre": "Francia", "rf": 0.0310, "crp": 0.00,
        "tax_rate": 0.25, "mkt_premium": 0.055, "currency": "EUR",
    },
    "Spain": {
        "nombre": "Espania", "rf": 0.0350, "crp": 0.0042,
        "tax_rate": 0.25, "mkt_premium": 0.056, "currency": "EUR",
    },
    "Italy": {
        "nombre": "Italia", "rf": 0.0395, "crp": 0.0088,
        "tax_rate": 0.24, "mkt_premium": 0.057, "currency": "EUR",
    },
    "Japan": {
        "nombre": "Japon", "rf": 0.0085, "crp": 0.00,
        "tax_rate": 0.2974, "mkt_premium": 0.055, "currency": "JPY",
    },
    "China": {
        "nombre": "China", "rf": 0.0285, "crp": 0.0063,
        "tax_rate": 0.25, "mkt_premium": 0.060, "currency": "CNY",
    },
    "India": {
        "nombre": "India", "rf": 0.0720, "crp": 0.0120,
        "tax_rate": 0.25, "mkt_premium": 0.062, "currency": "INR",
    },
    "Australia": {
        "nombre": "Australia", "rf": 0.0440, "crp": 0.00,
        "tax_rate": 0.30, "mkt_premium": 0.056, "currency": "AUD",
    },
    "South Korea": {
        "nombre": "Corea del Sur", "rf": 0.0350, "crp": 0.0038,
        "tax_rate": 0.24, "mkt_premium": 0.057, "currency": "KRW",
    },
    "Switzerland": {
        "nombre": "Suiza", "rf": 0.0085, "crp": 0.00,
        "tax_rate": 0.145, "mkt_premium": 0.053, "currency": "CHF",
    },
    "Netherlands": {
        "nombre": "Paises Bajos", "rf": 0.0280, "crp": 0.00,
        "tax_rate": 0.258, "mkt_premium": 0.055, "currency": "EUR",
    },
    "Sweden": {
        "nombre": "Suecia", "rf": 0.0290, "crp": 0.00,
        "tax_rate": 0.206, "mkt_premium": 0.055, "currency": "SEK",
    },
    "Taiwan": {
        "nombre": "Taiwan", "rf": 0.0175, "crp": 0.0038,
        "tax_rate": 0.20, "mkt_premium": 0.058, "currency": "TWD",
    },
    "Hong Kong": {
        "nombre": "Hong Kong", "rf": 0.0430, "crp": 0.0063,
        "tax_rate": 0.165, "mkt_premium": 0.058, "currency": "HKD",
    },
    "Singapore": {
        "nombre": "Singapur", "rf": 0.0340, "crp": 0.00,
        "tax_rate": 0.17, "mkt_premium": 0.055, "currency": "SGD",
    },
    "South Africa": {
        "nombre": "Sudafrica", "rf": 0.1020, "crp": 0.0255,
        "tax_rate": 0.27, "mkt_premium": 0.068, "currency": "ZAR",
    },
    "Saudi Arabia": {
        "nombre": "Arabia Saudita", "rf": 0.0490, "crp": 0.0063,
        "tax_rate": 0.20, "mkt_premium": 0.057, "currency": "SAR",
    },
}

DEFAULT_COUNTRY: dict = {
    "nombre": "Global (default)", "rf": 0.05, "crp": 0.02,
    "tax_rate": 0.25, "mkt_premium": 0.06, "currency": "USD",
}

# Peers curados por sector (yfinance info['sector'] / info['industry'])
SECTOR_PEERS: dict = {
    "Technology":              ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "ORCL", "CRM", "ADBE"],
    "Consumer Cyclical":       ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "CMG", "YUM"],
    "Consumer Defensive":      ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "MDLZ"],
    "Financial Services":      ["JPM", "BAC", "WFC", "GS", "MS", "C", "AXP", "BLK"],
    "Healthcare":              ["JNJ", "UNH", "PFE", "ABT", "TMO", "MRK", "DHR", "AMGN"],
    "Industrials":             ["HON", "UPS", "CAT", "DE", "LMT", "RTX", "GE", "MMM"],
    "Energy":                  ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "OXY", "HAL"],
    "Utilities":               ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL"],
    "Real Estate":             ["AMT", "PLD", "CCI", "EQIX", "PSA", "SPG", "WELL", "DLR"],
    "Basic Materials":         ["LIN", "APD", "ECL", "DD", "DOW", "NEM", "FCX", "NUE"],
    "Communication Services":  ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "T", "VZ"],
    # Industrias especificas
    "Restaurants":             ["MCD", "SBUX", "YUM", "CMG", "DRI", "YUMC", "TXRH", "QSR"],
    "Software—Application":    ["CRM", "ADBE", "NOW", "INTU", "WDAY", "SNOW", "HUBS"],
    "Semiconductors":          ["NVDA", "AMD", "INTC", "QCOM", "AVGO", "AMAT", "LRCX"],
    "Internet Retail":         ["AMZN", "EBAY", "SHOP", "MELI", "SE", "PDD"],
    "Airlines":                ["DAL", "UAL", "AAL", "LUV", "ALK", "JBLU"],
    "Auto Manufacturers":      ["TSLA", "GM", "F", "TM", "HMC", "RIVN", "STLA"],
    "Banks—Diversified":       ["JPM", "BAC", "WFC", "C", "USB", "TFC", "PNC"],
    "Biotechnology":           ["AMGN", "GILD", "BIIB", "REGN", "VRTX", "MRNA"],
    "Insurance—Diversified":   ["BRK-B", "AIG", "MET", "PRU", "AFL", "ALL"],
    "Telecom Services":        ["T", "VZ", "TMUS", "AMX", "BCE", "VOD"],
    "Discount Stores":         ["WMT", "TGT", "COST", "DG", "DLTR", "BJ"],
    "Oil & Gas E&P":           ["COP", "EOG", "DVN", "PXD", "FANG", "CTRA"],
    # BVC Colombia
    "Financiero BVC":          ["PFBCOLOM.CL", "CORFICOLCF.CL", "BVC.CL"],
    "Energia BVC":             ["ECOPETROL.CL", "ISA.CL", "CELSIA.CL", "TGAS.CL"],
    "Consumo BVC":             ["NUTRESA.CL", "BOGOTA.CL"],
}


def get_country_params(country_name: str) -> dict:
    params = COUNTRY_DB.get(country_name, DEFAULT_COUNTRY).copy()
    params["detected"] = country_name in COUNTRY_DB
    params["country_name"] = country_name
    return params


def get_sector_peers(sector: str, industry: str, exclude_ticker: str) -> list[str]:
    """
    Devuelve hasta 6 peers para un sector dado.
    Primero busca por industria especifica, luego por sector amplio.
    """
    exclude = exclude_ticker.upper().split(".")[0]
    candidates = (
        SECTOR_PEERS.get(industry, []) or
        SECTOR_PEERS.get(sector, [])
    )
    peers = [t for t in candidates if exclude not in t.upper()]
    return peers[:6]
