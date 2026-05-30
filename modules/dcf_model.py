"""
Modulo DCF: calculo de WACC, FCF base, proyeccion y tabla de sensibilidad.
Formula FCF estandar: UODI + D&A - delta_KTNO - CAPEX
"""
import numpy as np
import pandas as pd


def calculate_wacc(metrics: dict, country: dict, override: dict | None = None) -> dict:
    """
    Calcula WACC con datos de mercado y parametros de pais Damodaran.
    override permite que el usuario sobreescriba rf, crp o tax_rate desde la UI.
    """
    ov = override or {}

    rf          = ov.get("rf",        country.get("rf",        0.045))
    mkt_premium = ov.get("mkt_premium", country.get("mkt_premium", 0.055))
    crp         = ov.get("crp",       country.get("crp",       0.0))
    tax_rate    = ov.get("tax_rate",  country.get("tax_rate",  0.21))

    beta        = metrics.get("beta", 1.0) or 1.0
    market_cap  = metrics.get("market_cap", 0) or 0
    total_debt  = metrics.get("total_debt", 0) or 0
    int_expense = metrics.get("interest_expense")

    # Ke (CAPM + prima pais)
    ke = rf + beta * mkt_premium + crp

    # Kd: tasa implicita sobre la deuda
    if int_expense and total_debt > 0:
        kd_pretax = int_expense / total_debt
    else:
        kd_pretax = rf + crp + 0.015          # spread estimado sobre libre de riesgo
    kd = kd_pretax * (1 - tax_rate)

    # Pesos por valor de mercado
    total_capital = market_cap + total_debt
    if total_capital > 0:
        we = market_cap  / total_capital
        wd = total_debt  / total_capital
    else:
        we, wd = 0.70, 0.30

    wacc = ke * we + kd * wd

    return {
        "wacc":         wacc,
        "ke":           ke,
        "kd":           kd,
        "kd_pretax":    kd_pretax,
        "beta":         beta,
        "rf":           rf,
        "mkt_premium":  mkt_premium,
        "crp":          crp,
        "tax_rate":     tax_rate,
        "weight_equity":we,
        "weight_debt":  wd,
        "market_cap":   market_cap,
        "total_debt":   total_debt,
    }


def get_fcf_base(metrics: dict, fcf_history: list[float]) -> dict:
    """
    Determina el FCF base para la proyeccion.
    Primero intenta FCF real de estados financieros (media 3 anios);
    si no, usa freeCashflow del info de yfinance.
    """
    valid = [f for f in fcf_history if f and not np.isnan(f) and f > 0]

    if valid:
        base = float(np.mean(valid[:min(3, len(valid))]))
        method = f"Promedio FCF {min(3,len(valid))} anios"
    else:
        # Calcular desde metricas: UODI + D&A - dKTNO - CAPEX
        ebit    = metrics.get("operating_income", 0) or 0
        tax     = metrics.get("tax_rate_implied", 0.21)
        # D&A aproximada: ebitda - ebit
        ebitda  = metrics.get("ebitda", 0) or 0
        da      = max(ebitda - ebit, 0)
        uodi    = ebit * (1 - tax)

        ktno      = metrics.get("ktno", 0) or 0
        ktno_prev = metrics.get("ktno_prev", 0) or 0
        delta_ktno = ktno - ktno_prev

        capex     = metrics.get("capex", 0) or 0
        base = uodi + da - delta_ktno - capex
        method = "Calculado (UODI + D&A - dKTNO - CAPEX)"

    # Fallback absoluto: freecashflow del info
    if base <= 0:
        raw = metrics.get("free_cashflow", 0) or 0
        if raw and raw > 0:
            base   = float(raw)
            method = "freeCashflow (yfinance info)"

    return {"base_fcf": base, "method": method, "history": valid}


def run_dcf(
    metrics:        dict,
    fcf_data:       dict,
    wacc_data:      dict,
    growth_explicit:float,
    terminal_growth:float,
    explicit_years: int = 5,
) -> dict:
    """
    DCF estandar: periodo explicito + valor terminal Gordon Growth.
    Retorna dict con todos los componentes para graficas y tablas.
    """
    wacc   = wacc_data["wacc"]
    base   = fcf_data["base_fcf"]
    shares = metrics.get("shares", 1) or 1
    debt   = metrics.get("total_debt", 0) or 0
    cash   = metrics.get("total_cash", 0) or 0

    if base <= 0:
        return {"error": "FCF base negativo o nulo — DCF no aplicable para este activo."}
    if wacc <= terminal_growth:
        return {"error": f"WACC ({wacc:.2%}) debe ser mayor que g terminal ({terminal_growth:.2%})."}

    # Proyeccion FCF explicito
    fcfs_proj = [base * (1 + growth_explicit) ** t for t in range(1, explicit_years + 1)]

    # Valor presente periodo explicito
    pv_fcfs = [fcf / (1 + wacc) ** t for t, fcf in enumerate(fcfs_proj, 1)]
    pv_explicit = sum(pv_fcfs)

    # Valor terminal (Gordon Growth)
    tv_fcf      = fcfs_proj[-1] * (1 + terminal_growth)
    terminal_v  = tv_fcf / (wacc - terminal_growth)
    pv_terminal = terminal_v / (1 + wacc) ** explicit_years

    ev_dcf      = pv_explicit + pv_terminal
    equity_dcf  = ev_dcf - debt + cash
    price_share = max(equity_dcf / shares, 0)

    return {
        "base_fcf":        base,
        "growth_explicit": growth_explicit,
        "terminal_growth": terminal_growth,
        "explicit_years":  explicit_years,
        "fcfs_proj":       fcfs_proj,
        "pv_fcfs":         pv_fcfs,
        "pv_explicit":     pv_explicit,
        "terminal_value":  terminal_v,
        "pv_terminal":     pv_terminal,
        "ev_dcf":          ev_dcf,
        "equity_dcf":      equity_dcf,
        "price_per_share": price_share,
        "terminal_pct":    pv_terminal / ev_dcf if ev_dcf > 0 else 0,
        "wacc":            wacc,
        "error":           None,
    }


def dcf_sensitivity(
    metrics:        dict,
    fcf_data:       dict,
    wacc_data:      dict,
    growth_explicit:float,
    explicit_years: int,
) -> pd.DataFrame:
    """
    Tabla de sensibilidad: WACC (+/-2%) x g_terminal (0.5% a 4%).
    """
    w_base  = wacc_data["wacc"]
    w_range = [round(w_base + d, 4) for d in [-0.02, -0.01, 0.0, 0.01, 0.02]]
    g_range = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030, 0.035, 0.040]

    rows = {}
    for g in g_range:
        row = {}
        for w in w_range:
            wd_mod = dict(wacc_data)
            wd_mod["wacc"] = w
            res = run_dcf(metrics, fcf_data, wd_mod, growth_explicit, g, explicit_years)
            price = res.get("price_per_share")
            row[f"WACC {w:.1%}"] = round(price, 1) if price else None
        rows[f"g {g:.1%}"] = row

    return pd.DataFrame(rows).T
