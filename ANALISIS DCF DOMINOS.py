"""
DCF Institucional — Domino's Pizza (DPZ)
Metodología: Free Cash Flow to Firm (FCFF) descontado al WACC
Fecha: 2026-05-29
"""

import yfinance as yf
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

TICKER = "DPZ"
RF      = 0.0440   # Treasury 10Y (~4.40%, mayo 2026)
MRP     = 0.0500   # Market Risk Premium — Damodaran 2025 (4.5–5.5%)
TAX     = 0.21     # Tasa impositiva efectiva DPZ (~21%)
G_TERM  = 0.030    # Crecimiento perpetuo terminal (3.0%)

# ─────────────────────────────────────────────────────────────────────────────
# 1. EXTRACCIÓN DE DATOS
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 65)
print("  MODELO DCF INSTITUCIONAL — DOMINO'S PIZZA (DPZ)")
print("=" * 65)
print("\n[1] Descargando datos financieros...\n")

dpz  = yf.Ticker(TICKER)
info = dpz.info

# Precio de mercado actual
price_mkt = info.get("currentPrice") or info.get("regularMarketPrice")

# Acciones en circulación
shares_out = info.get("sharesOutstanding", 0)

# Beta (regresión 5Y mensual vs SPY)
beta_raw = info.get("beta", 1.0)

# Deuda neta desde balance
bs = dpz.balance_sheet
is_ = dpz.income_stmt
cf = dpz.cashflow

print(f"  Precio mercado actual : ${price_mkt:,.2f}")
print(f"  Acciones en circulación: {shares_out/1e6:.2f}M")
print(f"  Beta (5Y mensual)      : {beta_raw:.2f}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. WACC
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2] Calculando WACC...\n")

# Ke (CAPM)
ke = RF + beta_raw * MRP

# Deuda total y equity (market cap)
total_debt = info.get("totalDebt", 0)
market_cap = info.get("marketCap", 0)
cash       = info.get("totalCash", 0)
net_debt   = total_debt - cash
firm_value_mkt = market_cap + net_debt

E_pct = market_cap / firm_value_mkt if firm_value_mkt else 0.5
D_pct = net_debt   / firm_value_mkt if firm_value_mkt else 0.5

# Kd — costo de deuda: interest expense / total debt
try:
    interest_exp = abs(float(is_.loc["Interest Expense"].iloc[0]))
    kd_pre = interest_exp / total_debt if total_debt else 0.05
except Exception:
    kd_pre = 0.055   # default conservador

kd = kd_pre * (1 - TAX)

wacc = E_pct * ke + D_pct * kd

print(f"  Rf                     : {RF*100:.2f}%")
print(f"  Beta                   : {beta_raw:.2f}")
print(f"  Prima mercado (MRP)    : {MRP*100:.2f}%")
print(f"  Ke (CAPM)              : {ke*100:.2f}%")
print(f"  Kd (pre-tax)           : {kd_pre*100:.2f}%")
print(f"  Kd (after-tax)         : {kd*100:.2f}%")
print(f"  Peso Equity E/(E+D)    : {E_pct*100:.1f}%")
print(f"  Peso Deuda D/(E+D)     : {D_pct*100:.1f}%")
print(f"  >> WACC                : {wacc*100:.2f}%")

# ─────────────────────────────────────────────────────────────────────────────
# 3. HISTORIAL DE FCF (últimos 4 años)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3] FCF histórico (FCFF)...\n")

def safe_row(df, *candidates):
    for c in candidates:
        for idx in df.index:
            if c.lower() in str(idx).lower():
                return df.loc[idx]
    return pd.Series(dtype=float)

ebit_row   = safe_row(is_, "EBIT", "Operating Income")
da_row     = safe_row(cf, "Depreciation", "D&A", "Depreciation And Amortization")
capex_row  = safe_row(cf, "Capital Expenditure", "Capex", "Purchase Of PPE")
wcap_row   = safe_row(cf, "Change In Working Capital", "Changes In Working Capital")

years_hist = []
fcfs_hist  = []

n_cols = min(4, is_.shape[1])
for i in range(n_cols):
    try:
        yr    = is_.columns[i].year if hasattr(is_.columns[i], 'year') else str(is_.columns[i])[:4]
        ebit  = float(ebit_row.iloc[i])  if len(ebit_row)  > i else 0
        da    = abs(float(da_row.iloc[i]))   if len(da_row)   > i else 0
        capex = abs(float(capex_row.iloc[i])) if len(capex_row) > i else 0
        try:
            dwc = float(wcap_row.iloc[i]) if len(wcap_row) > i else 0
        except Exception:
            dwc = 0

        nopat = ebit * (1 - TAX)
        fcf   = nopat + da - capex - dwc
        years_hist.append(yr)
        fcfs_hist.append(fcf)

        print(f"  {yr} | EBIT: ${ebit/1e6:>7.1f}M | NOPAT: ${nopat/1e6:>7.1f}M | "
              f"D&A: ${da/1e6:>6.1f}M | CAPEX: ${capex/1e6:>6.1f}M | FCF: ${fcf/1e6:>7.1f}M")
    except Exception as e:
        pass

# FCF base = promedio ponderado últimos 2-3 años (más peso al más reciente)
if len(fcfs_hist) >= 3:
    weights  = np.array([0.2, 0.3, 0.5])
    fcf_base = np.dot(weights, fcfs_hist[-3:])
elif len(fcfs_hist) >= 2:
    fcf_base = 0.4 * fcfs_hist[-2] + 0.6 * fcfs_hist[-1]
else:
    fcf_base = fcfs_hist[-1] if fcfs_hist else 0

print(f"\n  FCF base (ponderado)   : ${fcf_base/1e6:.1f}M")

# ─────────────────────────────────────────────────────────────────────────────
# 4. PROYECCIÓN DE FCF (5 años) — 3 escenarios
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4] Proyección FCF — 3 escenarios (5 años)...\n")

SCENARIOS = {
    "Pesimista": {"g1": 0.03, "g2": 0.025},
    "Base"     : {"g1": 0.055, "g2": 0.04},
    "Optimista": {"g1": 0.08,  "g2": 0.06},
}

N_PROJ  = 5
results = {}

header = f"{'Año':<6}" + "".join(f"{'Pesimista':>14}{'Base':>14}{'Optimista':>14}")
print("  " + header)
print("  " + "-" * 50)

for yr_idx in range(1, N_PROJ + 1):
    row = f"  Año {yr_idx}"
    fcfs_row = {}
    for scen, params in SCENARIOS.items():
        g = params["g1"] if yr_idx <= 3 else params["g2"]
        prev = results.get(scen, [fcf_base])
        fcf_t = prev[-1] * (1 + g)
        fcfs_row[scen] = fcf_t
        if scen not in results:
            results[scen] = []
        results[scen].append(fcf_t)
        row += f"  ${fcf_t/1e6:>10.1f}M"
    print(row)

# ─────────────────────────────────────────────────────────────────────────────
# 5. VALOR TERMINAL + VAN + PRECIO POR ACCIÓN
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5] Valor Terminal, VAN y Precio por Acción...\n")

prices = {}
print(f"  {'Escenario':<12} {'VT ($M)':>12} {'EV ($M)':>12} {'NetDebt($M)':>13} {'Equity($M)':>12} {'P/Acc':>10} {'Upside':>8}")
print("  " + "-" * 82)

for scen, fcfs in results.items():
    # Descuento FCFs
    pv_fcfs = sum(f / (1 + wacc) ** (t + 1) for t, f in enumerate(fcfs))

    # Valor terminal (Gordon Growth sobre FCF_5)
    vt       = fcfs[-1] * (1 + G_TERM) / (wacc - G_TERM)
    pv_vt    = vt / (1 + wacc) ** N_PROJ
    ev       = pv_fcfs + pv_vt

    # Equity value
    eq_val   = ev - net_debt
    price_dcf = eq_val / shares_out if shares_out else 0
    upside   = (price_dcf - price_mkt) / price_mkt * 100

    prices[scen] = price_dcf
    print(f"  {scen:<12} {vt/1e6:>12,.0f} {ev/1e6:>12,.0f} {net_debt/1e6:>13,.0f} "
          f"{eq_val/1e6:>12,.0f} {price_dcf:>10,.2f} {upside:>+7.1f}%")

# ─────────────────────────────────────────────────────────────────────────────
# 6. ANÁLISIS DE SENSIBILIDAD — WACC vs g_terminal
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6] Sensibilidad — Precio Acción ($) | WACC vs g_terminal [escenario Base]\n")

wacc_range = [wacc - 0.015, wacc - 0.010, wacc - 0.005, wacc,
              wacc + 0.005, wacc + 0.010, wacc + 0.015]
g_range    = [0.020, 0.025, 0.030, 0.035, 0.040]

fcfs_base = results["Base"]

header2 = f"  {'WACC \\ g':>9}" + "".join(f"{g*100:>8.1f}%" for g in g_range)
print(header2)
print("  " + "-" * (10 + 9 * len(g_range)))

for w in wacc_range:
    row2 = f"  {w*100:>8.2f}%"
    for g in g_range:
        if w <= g:
            row2 += f"{'  N/A':>9}"
            continue
        pv_f  = sum(f / (1 + w) ** (t + 1) for t, f in enumerate(fcfs_base))
        vt_s  = fcfs_base[-1] * (1 + g) / (w - g)
        pv_vt_s = vt_s / (1 + w) ** N_PROJ
        ev_s  = pv_f + pv_vt_s
        eq_s  = ev_s - net_debt
        p_s   = eq_s / shares_out if shares_out else 0
        row2 += f"{p_s:>9.2f}"
    print(row2)

# ─────────────────────────────────────────────────────────────────────────────
# 7. RESUMEN EJECUTIVO
# ─────────────────────────────────────────────────────────────────────────────
price_base = prices["Base"]
upside_base = (price_base - price_mkt) / price_mkt * 100

recomendacion = (
    "COMPRA FUERTE" if upside_base > 20 else
    "COMPRA"        if upside_base > 8  else
    "MANTENER"      if upside_base > -8 else
    "REDUCIR"       if upside_base > -20 else
    "VENTA"
)

print("\n" + "=" * 65)
print("  RESUMEN EJECUTIVO — DCF INSTITUCIONAL DPZ")
print("=" * 65)
print(f"  Ticker                 : {TICKER}")
print(f"  Fecha análisis         : 2026-05-29")
print(f"  Precio mercado         : ${price_mkt:,.2f}")
print(f"  ─────────────────────────────────────────")
print(f"  Precio DCF Pesimista   : ${prices['Pesimista']:,.2f}")
print(f"  Precio DCF Base        : ${prices['Base']:,.2f}  << Precio Objetivo")
print(f"  Precio DCF Optimista   : ${prices['Optimista']:,.2f}")
print(f"  ─────────────────────────────────────────")
print(f"  Upside / (Downside)    : {upside_base:+.1f}%")
print(f"  WACC aplicado          : {wacc*100:.2f}%")
print(f"  Tasa crecimiento term. : {G_TERM*100:.1f}%")
print(f"  ─────────────────────────────────────────")
print(f"  RECOMENDACION          : ***  {recomendacion}  ***")
print("=" * 65)

print("""
  RIESGOS PRINCIPALES:
  1. Franquiciados bajo presión: modelo asset-light concentra riesgo
     operativo en red de franquicias (~99% del sistema).
  2. Deuda neta elevada (leverage > 6x EBITDA histórico), sensible
     a subidas de tasas.
  3. Competencia intensa en delivery (Papa John's, Pizza Hut, apps
     de terceros como DoorDash/Uber Eats erosionando márgenes).
  4. Desaceleración de mismo-restaurante ventas (SSS) en EE.UU.
  5. Costos de insumos (queso, trigo) volátiles que comprimen
     márgenes del franquiciado y royalties de DPZ.
""")
