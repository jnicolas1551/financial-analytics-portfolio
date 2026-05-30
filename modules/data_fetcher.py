"""
Descarga y estructuracion de datos financieros via yfinance.
Incluye deteccion de pais, tipo de cambio y peers automaticos.
"""
import numpy as np
import pandas as pd
import yfinance as yf
import warnings

from modules.country_data import get_country_params, get_sector_peers

warnings.filterwarnings("ignore")


def _safe(info: dict, key: str, default=None):
    v = info.get(key, default)
    if v is None:
        return default
    if isinstance(v, float) and np.isnan(v):
        return default
    return v


def get_fx_rate(from_ccy: str, to_ccy: str = "USD") -> float:
    """Tipo de cambio spot via yfinance. Retorna 1.0 si falla."""
    if from_ccy == to_ccy:
        return 1.0
    try:
        pair   = f"{from_ccy}{to_ccy}=X"
        stock  = yf.Ticker(pair)
        # fast_info es un objeto FastInfo, no un dict — usar getattr
        rate   = getattr(stock.fast_info, "last_price", None)
        if not rate:
            rate = stock.info.get("regularMarketPrice")
        return float(rate) if rate else 1.0
    except Exception:
        return 1.0


def fetch_company_data(ticker: str) -> dict:
    """
    Descarga todos los datos financieros de un ticker desde Yahoo Finance.
    Retorna dict con metricas, historial, estados financieros y datos de pais.
    """
    stock = yf.Ticker(ticker)
    info  = stock.info

    # --- Historial de precios ---
    history = stock.history(period="5y")

    # --- Estados financieros ---
    try:
        income_stmt   = stock.income_stmt
    except Exception:
        income_stmt   = pd.DataFrame()
    try:
        balance_sheet = stock.balance_sheet
    except Exception:
        balance_sheet = pd.DataFrame()
    try:
        cashflow      = stock.cashflow
    except Exception:
        cashflow      = pd.DataFrame()

    # --- Valores clave del info ---
    current_price  = _safe(info, "currentPrice") or _safe(info, "regularMarketPrice", 0)
    market_cap     = _safe(info, "marketCap", 0)
    total_debt     = _safe(info, "totalDebt", 0)
    total_cash     = _safe(info, "totalCash", 0)
    shares         = _safe(info, "sharesOutstanding", 0)
    ebitda         = _safe(info, "ebitda", 0)
    total_revenue  = _safe(info, "totalRevenue", 0)
    ev             = _safe(info, "enterpriseValue") or max((market_cap + total_debt - total_cash), 0)
    country_raw    = _safe(info, "country", "United States")
    sector         = _safe(info, "sector", "")
    industry       = _safe(info, "industry", "")
    currency       = _safe(info, "currency", "USD")

    # --- Balance sheet: activos, patrimonio ---
    total_assets = None
    total_equity = None
    if not balance_sheet.empty:
        for k in ["Total Assets", "TotalAssets"]:
            if k in balance_sheet.index:
                total_assets = float(balance_sheet.loc[k].iloc[0])
                break
        for k in ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"]:
            if k in balance_sheet.index:
                v = balance_sheet.loc[k].iloc[0]
                if pd.notna(v):
                    total_equity = float(v)
                break

    # --- KTNO ---
    ktno = ktno_prev = None
    if not balance_sheet.empty and len(balance_sheet.columns) >= 2:
        try:
            inv_k = next((k for k in balance_sheet.index if "inventor" in k.lower()), None)
            rec_k = next((k for k in balance_sheet.index if "receivable" in k.lower()), None)
            pay_k = next((k for k in balance_sheet.index if "payable" in k.lower()
                          and "tax" not in k.lower() and "income" not in k.lower()), None)
            if inv_k and rec_k and pay_k:
                def _row(key, col):
                    v = balance_sheet.loc[key].iloc[col]
                    return float(v) if pd.notna(v) else 0.0
                ktno      = _row(inv_k, 0) + _row(rec_k, 0) - _row(pay_k, 0)
                ktno_prev = _row(inv_k, 1) + _row(rec_k, 1) - _row(pay_k, 1)
        except Exception:
            pass

    # --- CAPEX ---
    capex = capex_prev = None
    if not cashflow.empty:
        for k in cashflow.index:
            if "capital expenditure" in k.lower() or "capex" in k.lower():
                s = cashflow.loc[k].dropna()
                if len(s) >= 1:
                    capex = abs(float(s.iloc[0]))
                if len(s) >= 2:
                    capex_prev = abs(float(s.iloc[1]))
                break

    # --- Gasto financiero (para Kd) ---
    interest_expense = None
    if not income_stmt.empty:
        for k in income_stmt.index:
            if "interest" in k.lower() and "expense" in k.lower():
                v = income_stmt.loc[k].iloc[0]
                if pd.notna(v):
                    interest_expense = abs(float(v))
                    break

    # --- Historial FCF ---
    fcf_history: list[float] = []
    if not cashflow.empty:
        for k in cashflow.index:
            if "free cash flow" in k.lower():
                s = cashflow.loc[k].dropna()
                fcf_history = [float(v) for v in s.values if pd.notna(v)]
                break
    if not fcf_history:
        raw = _safe(info, "freeCashflow", 0)
        if raw:
            fcf_history = [float(raw)]

    # FCF historico de crecimiento (CAGR ultimos 3 anos)
    fcf_growth_hist = None
    valid_fcf = [f for f in fcf_history if f and f > 0]
    if len(valid_fcf) >= 2:
        n = min(len(valid_fcf), 3)
        if valid_fcf[0] > 0 and valid_fcf[n-1] > 0:
            fcf_growth_hist = (valid_fcf[0] / valid_fcf[n-1]) ** (1 / n) - 1

    # Q de Tobin
    q_tobin = None
    if total_assets and total_assets > 0 and market_cap:
        q_tobin = market_cap / total_assets

    # --- Datos de pais y WACC ---
    country_params = get_country_params(country_raw)

    # Tipo de cambio a USD
    fx_to_usd = get_fx_rate(currency, "USD")

    # --- Peers automaticos ---
    auto_peers = get_sector_peers(sector, industry, ticker)

    metrics = {
        "ticker":           ticker.upper(),
        "name":             _safe(info, "longName", ticker),
        "sector":           sector,
        "industry":         industry,
        "country":          country_raw,
        "currency":         currency,
        "exchange":         _safe(info, "exchange", ""),
        "website":          _safe(info, "website", ""),
        "description":      (_safe(info, "longBusinessSummary", "") or "")[:400],
        # Precio y capital
        "current_price":    current_price,
        "market_cap":       market_cap,
        "enterprise_value": ev,
        "shares":           shares,
        "total_debt":       total_debt,
        "total_cash":       total_cash,
        "total_assets":     total_assets,
        "total_equity":     total_equity,
        # Resultados
        "ebitda":           ebitda,
        "total_revenue":    total_revenue,
        "trailing_eps":     _safe(info, "trailingEps", 0),
        "forward_eps":      _safe(info, "forwardEps", 0),
        "net_income":       _safe(info, "netIncomeToCommon", 0),
        "operating_income": _safe(info, "operatingIncome", 0),
        # Multiplos
        "trailing_pe":      _safe(info, "trailingPE"),
        "forward_pe":       _safe(info, "forwardPE"),
        "ev_ebitda":        _safe(info, "enterpriseToEbitda"),
        "ev_revenue":       _safe(info, "enterpriseToRevenue"),
        "price_to_book":    _safe(info, "priceToBook"),
        "q_tobin":          q_tobin,
        # Margenes y rentabilidad
        "ebitda_margin":    _safe(info, "ebitdaMargins"),
        "operating_margin": _safe(info, "operatingMargins"),
        "gross_margin":     _safe(info, "grossMargins"),
        "profit_margin":    _safe(info, "profitMargins"),
        "return_on_equity": _safe(info, "returnOnEquity"),
        "return_on_assets": _safe(info, "returnOnAssets"),
        # Dividendo
        "dividend_yield":   _safe(info, "dividendYield", 0),
        "dividend_rate":    _safe(info, "dividendRate", 0),
        # WACC inputs
        "beta":             _safe(info, "beta", 1.0),
        "interest_expense": interest_expense,
        # FCF y balance operativo
        "free_cashflow":    _safe(info, "freeCashflow", 0),
        "operating_cf":     _safe(info, "operatingCashflow", 0),
        "ktno":             ktno,
        "ktno_prev":        ktno_prev,
        "capex":            capex,
        "capex_prev":       capex_prev,
        # Crecimiento
        "revenue_growth":   _safe(info, "revenueGrowth"),
        "earnings_growth":  _safe(info, "earningsGrowth"),
        "fcf_growth_hist":  fcf_growth_hist,
        # FX
        "fx_to_usd":        fx_to_usd,
    }

    return {
        "metrics":       metrics,
        "history":       history,
        "income_stmt":   income_stmt,
        "balance_sheet": balance_sheet,
        "cashflow":      cashflow,
        "fcf_history":   fcf_history,
        "country":       country_params,
        "auto_peers":    auto_peers,
    }


def fetch_peers_data(peer_tickers: list[str]) -> list[dict]:
    """Descarga metricas resumidas de cada peer para analisis comparativo."""
    results = []
    for t in peer_tickers:
        try:
            info = yf.Ticker(t).info
            mc   = _safe(info, "marketCap", 0) or 0
            debt = _safe(info, "totalDebt", 0) or 0
            cash = _safe(info, "totalCash", 0) or 0
            ev   = _safe(info, "enterpriseValue") or max(mc + debt - cash, 0)
            ta   = None
            try:
                bs = yf.Ticker(t).balance_sheet
                if not bs.empty:
                    for k in ["Total Assets", "TotalAssets"]:
                        if k in bs.index:
                            ta = float(bs.loc[k].iloc[0])
                            break
            except Exception:
                pass
            results.append({
                "ticker":        t.upper(),
                "name":          (_safe(info, "longName", t) or t)[:35],
                "current_price": _safe(info, "currentPrice") or _safe(info, "regularMarketPrice", 0),
                "market_cap":    mc,
                "enterprise_value": ev,
                "total_debt":    debt,
                "total_cash":    cash,
                "shares":        _safe(info, "sharesOutstanding", 0),
                "ebitda":        _safe(info, "ebitda", 0),
                "total_revenue": _safe(info, "totalRevenue", 0),
                "trailing_eps":  _safe(info, "trailingEps", 0),
                "trailing_pe":   _safe(info, "trailingPE"),
                "ev_ebitda":     _safe(info, "enterpriseToEbitda"),
                "ev_revenue":    _safe(info, "enterpriseToRevenue"),
                "ebitda_margin": _safe(info, "ebitdaMargins"),
                "return_on_equity": _safe(info, "returnOnEquity"),
                "dividend_yield":_safe(info, "dividendYield", 0),
                "q_tobin":       (mc / ta) if (ta and ta > 0) else None,
                "beta":          _safe(info, "beta", 1.0),
            })
        except Exception:
            pass
    return results
