---
name: python-finanzas-cuant
description: >
  Skill de Python para automatización de finanzas cuantitativas: valoración de empresas
  (DCF, múltiplos, DDM, NAV) y construcción/optimización de portafolios (Markowitz,
  Sharpe, frontera eficiente). Úsala siempre que el usuario pida código Python relacionado
  con: yfinance, estados financieros, WACC, flujos de caja, backtesting, optimización de
  portafolio, matrices de covarianza, métricas de riesgo, automatización de análisis
  financiero, scraping de datos financieros, o cualquier script con propósito de inversión
  o valoración. También aplica para estructurar proyectos de finanzas cuantitativas,
  pipelines de datos financieros, o dashboards de análisis. Si hay código + finanzas, úsala.
---

# Skill: Python para Finanzas Cuantitativas

## Contexto del usuario
- Ingeniero civil con MAF en EAFIT, perfil cuantitativo
- Stack: Python + yfinance + Excel/CSV
- Mercados: S&P 500 y BVC Colombia
- Código en inglés, comentarios/explicaciones en español

---

## 1. Stack de Librerías

```python
# Core
import pandas as pd
import numpy as np

# Datos financieros
import yfinance as yf

# Optimización
from scipy.optimize import minimize
import scipy.stats as stats

# Visualización
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px  # preferir para dashboards interactivos

# Excel I/O
import openpyxl
from openpyxl import load_workbook

# Utilidades
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')
```

---

## 2. Patrones de Código Estándar

### 2.1 Descarga de datos con yfinance
```python
def get_financial_data(ticker: str, period: str = "5y") -> dict:
    """
    Descarga datos históricos y estados financieros.
    
    Args:
        ticker: Símbolo (ej: 'AAPL', 'PFBCOLOM.CL' para BVC)
        period: '1y', '3y', '5y', 'max'
    
    Returns:
        dict con prices, income_stmt, balance_sheet, cashflow
    """
    stock = yf.Ticker(ticker)
    
    return {
        "prices": stock.history(period=period),
        "income_stmt": stock.income_stmt,
        "balance_sheet": stock.balance_sheet,
        "cashflow": stock.cashflow,
        "info": stock.info
    }

# Nota BVC: tickers colombianos en Yahoo usan sufijo .CL
# Ej: PFBCOLOM.CL, ECOPETROL.CL, ISA.CL, NUTRESA.CL
```

### 2.2 Cálculo de WACC
```python
def get_wacc_inputs() -> dict:
    """
    Solicita al usuario los parámetros macroeconómicos para el WACC.
    Llamar una vez antes de correr modelos; retorna dict reutilizable.
    """
    print("=" * 50)
    print("  PARÁMETROS MACROECONÓMICOS — WACC")
    print("=" * 50)
    print("Referencias:")
    print("  Rf USA:       Treasury 10Y  → https://fred.stlouisfed.org (DGS10)")
    print("  Rf Colombia:  TES 10Y       → ~11.5% (BanRep)")
    print("  Prima mercado:              → 5.5% Damodaran (default)")
    print("  Prima país Colombia:        → EMBI+ ~2.5%")
    print("  Impuesto USA: 21%  |  Colombia: 35%")
    print("-" * 50)

    def _get_float(prompt, default=None):
        while True:
            suffix = f" [default: {default*100:.1f}%]" if default else ""
            raw = input(f"{prompt}{suffix}: ").strip()
            if raw == "" and default is not None:
                return default
            try:
                val = float(raw.replace("%", "").replace(",", "."))
                # aceptar tanto 4.5 como 0.045
                return val / 100 if val > 1 else val
            except ValueError:
                print("  ⚠️  Ingresa un número válido (ej: 4.5 o 0.045)")

    rf        = _get_float("Tasa libre de riesgo (Rf)")
    mkt_prem  = _get_float("Prima de mercado (Rm - Rf)", default=0.055)
    crp       = _get_float("Prima de riesgo país (0 si es USA)", default=0.0)
    tax       = _get_float("Tasa de impuestos")

    params = {
        "risk_free_rate": rf,
        "market_premium": mkt_prem,
        "country_risk_premium": crp,
        "tax_rate": tax
    }

    print("\n✅ Parámetros registrados:")
    for k, v in params.items():
        print(f"   {k}: {v*100:.2f}%")

    return params


def calculate_wacc(ticker: str, macro_params: dict) -> dict:
    """
    Calcula WACC a partir de datos de mercado y parámetros del usuario.

    Args:
        ticker:       Símbolo (ej: 'AAPL' o 'PFBCOLOM.CL')
        macro_params: dict retornado por get_wacc_inputs()

    Returns:
        dict con wacc, ke, kd, beta, pesos de capital
    """
    stock = yf.Ticker(ticker)
    info  = stock.info

    rf   = macro_params["risk_free_rate"]
    mp   = macro_params["market_premium"]
    crp  = macro_params["country_risk_premium"]
    tax  = macro_params["tax_rate"]

    # Beta
    beta = info.get("beta", 1.0)

    # Estructura de capital
    market_cap  = info.get("marketCap", 0)
    total_debt  = info.get("totalDebt", 0)
    total_value = market_cap + total_debt

    # Ke (CAPM + prima país)
    ke = rf + beta * mp + crp

    # Kd after-tax
    try:
        interest_expense = abs(stock.income_stmt.loc["Interest Expense"].iloc[0])
        kd_pretax = interest_expense / total_debt if total_debt > 0 else 0.05
    except Exception:
        kd_pretax = 0.05
    kd = kd_pretax * (1 - tax)

    # WACC
    weight_equity = market_cap / total_value
    weight_debt   = total_debt / total_value
    wacc          = weight_equity * ke + weight_debt * kd

    return {
        "wacc": wacc,
        "ke": ke,
        "kd": kd,
        "beta": beta,
        "weight_equity": weight_equity,
        "weight_debt": weight_debt
    }
```

**Uso típico:**
```python
# 1. El usuario ingresa los parámetros UNA sola vez
macro = get_wacc_inputs()

# 2. Reutilizar para N empresas sin volver a preguntar
for ticker in ["AAPL", "MSFT", "GOOGL"]:
    wacc_data = calculate_wacc(ticker, macro)
    print(f"{ticker}: WACC = {wacc_data['wacc']:.2%}")
```

### 2.3 Modelo DCF
```python
def dcf_valuation(
    fcf_history: list,          # FCF histórico (últimos 3-5 años)
    wacc: float,
    growth_rate_explicit: float, # Tasa crecimiento período explícito
    terminal_growth: float,      # g terminal (≤ GDP growth)
    explicit_years: int = 5,
    shares_outstanding: float = None,
    net_debt: float = 0
) -> dict:
    """
    Modelo DCF estándar con período explícito + valor terminal.
    """
    
    # Proyección FCF
    base_fcf = np.mean(fcf_history[-3:])  # promedio últimos 3 años
    projected_fcf = [
        base_fcf * (1 + growth_rate_explicit) ** t
        for t in range(1, explicit_years + 1)
    ]
    
    # Valor presente período explícito
    pv_explicit = sum(
        fcf / (1 + wacc) ** t
        for t, fcf in enumerate(projected_fcf, 1)
    )
    
    # Valor terminal (Gordon Growth)
    terminal_fcf = projected_fcf[-1] * (1 + terminal_growth)
    terminal_value = terminal_fcf / (wacc - terminal_growth)
    pv_terminal = terminal_value / (1 + wacc) ** explicit_years
    
    # Valor empresa y equity
    enterprise_value = pv_explicit + pv_terminal
    equity_value = enterprise_value - net_debt
    
    result = {
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "pv_explicit": pv_explicit,
        "pv_terminal": pv_terminal,
        "terminal_value_pct": pv_terminal / enterprise_value
    }
    
    if shares_outstanding:
        result["price_per_share"] = equity_value / shares_outstanding
    
    return result


def dcf_sensitivity(fcf_history, net_debt, shares_outstanding,
                     wacc_range, growth_range):
    """
    Tabla de sensibilidad WACC vs g terminal.
    Returns: DataFrame con precio por acción.
    """
    results = {}
    for g in growth_range:
        row = {}
        for w in wacc_range:
            val = dcf_valuation(
                fcf_history, w, 0.08, g,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt
            )
            row[f"WACC={w:.1%}"] = round(val["price_per_share"], 2)
        results[f"g={g:.1%}"] = row
    
    return pd.DataFrame(results).T
```

### 2.4 Valoración por Múltiplos
```python
def comparables_valuation(
    target_metrics: dict,   # {'ebitda': X, 'revenue': Y, 'eps': Z}
    peers: list,            # lista de tickers comparables
    metric: str = 'ebitda'  # 'ebitda', 'revenue', 'earnings'
) -> dict:
    """Valoración por múltiplos de empresas comparables."""
    
    multiples = []
    
    for peer in peers:
        try:
            stock = yf.Ticker(peer)
            info = stock.info
            
            ev = info.get('enterpriseValue', 0)
            
            if metric == 'ebitda':
                m = info.get('enterpriseToEbitda', None)
            elif metric == 'revenue':
                m = info.get('enterpriseToRevenue', None)
            elif metric == 'earnings':
                m = info.get('trailingPE', None)
            
            if m and m > 0:
                multiples.append(m)
        except:
            continue
    
    if not multiples:
        raise ValueError(f"No se pudieron obtener múltiplos para los peers")
    
    median_multiple = np.median(multiples)
    target_value = median_multiple * target_metrics.get(metric, 0)
    
    return {
        "median_multiple": median_multiple,
        "mean_multiple": np.mean(multiples),
        "implied_value": target_value,
        "peer_multiples": dict(zip(peers, multiples[:len(peers)]))
    }
```

---

## 3. Optimización de Portafolio (Markowitz)

```python
def portfolio_optimization(
    tickers: list,
    period: str = "3y",
    risk_free_rate: float = 0.045,
    n_portfolios: int = 10_000
) -> dict:
    """
    Optimización media-varianza. Retorna frontera eficiente y
    portafolio de máximo Sharpe.
    """
    
    # Descargar precios
    prices = yf.download(tickers, period=period)['Close']
    returns = prices.pct_change().dropna()
    
    mean_returns = returns.mean() * 252      # anualizar
    cov_matrix = returns.cov() * 252
    n_assets = len(tickers)
    
    # --- Simulación Monte Carlo para frontera eficiente ---
    results = np.zeros((3, n_portfolios))
    weights_record = []
    
    for i in range(n_portfolios):
        w = np.random.random(n_assets)
        w /= w.sum()
        weights_record.append(w)
        
        port_return = np.dot(w, mean_returns)
        port_vol = np.sqrt(w.T @ cov_matrix @ w)
        sharpe = (port_return - risk_free_rate) / port_vol
        
        results[0, i] = port_return
        results[1, i] = port_vol
        results[2, i] = sharpe
    
    # Portafolio máximo Sharpe
    max_sharpe_idx = results[2].argmax()
    max_sharpe_weights = weights_record[max_sharpe_idx]
    
    # Portafolio mínima varianza
    min_vol_idx = results[1].argmin()
    min_vol_weights = weights_record[min_vol_idx]
    
    return {
        "max_sharpe": {
            "weights": dict(zip(tickers, max_sharpe_weights)),
            "return": results[0, max_sharpe_idx],
            "volatility": results[1, max_sharpe_idx],
            "sharpe": results[2, max_sharpe_idx]
        },
        "min_volatility": {
            "weights": dict(zip(tickers, min_vol_weights)),
            "return": results[0, min_vol_idx],
            "volatility": results[1, min_vol_idx],
            "sharpe": results[2, min_vol_idx]
        },
        "frontier_data": pd.DataFrame({
            "return": results[0],
            "volatility": results[1],
            "sharpe": results[2]
        }),
        "returns": returns,
        "mean_returns": mean_returns,
        "cov_matrix": cov_matrix
    }


def plot_efficient_frontier(opt_results: dict, save_path: str = None):
    """Grafica la frontera eficiente con plotly."""
    
    df = opt_results["frontier_data"]
    
    fig = px.scatter(
        df, x="volatility", y="return",
        color="sharpe", color_continuous_scale="viridis",
        labels={"volatility": "Volatilidad anualizada",
                "return": "Retorno esperado anualizado",
                "sharpe": "Sharpe Ratio"},
        title="Frontera Eficiente — Optimización Markowitz"
    )
    
    # Marcar portafolios óptimos
    ms = opt_results["max_sharpe"]
    mv = opt_results["min_volatility"]
    
    fig.add_scatter(x=[ms["volatility"]], y=[ms["return"]],
                   mode="markers", marker=dict(size=15, color="red", symbol="star"),
                   name="Máximo Sharpe")
    fig.add_scatter(x=[mv["volatility"]], y=[mv["return"]],
                   mode="markers", marker=dict(size=15, color="blue", symbol="diamond"),
                   name="Mínima Varianza")
    
    if save_path:
        fig.write_html(save_path)
    
    return fig


def portfolio_metrics(weights: dict, returns_df: pd.DataFrame,
                      risk_free_rate: float = 0.045) -> dict:
    """Calcula métricas completas de un portafolio dado."""
    
    w = np.array(list(weights.values()))
    tickers = list(weights.keys())
    rets = returns_df[tickers]
    
    port_returns = rets @ w
    ann_return = port_returns.mean() * 252
    ann_vol = port_returns.std() * np.sqrt(252)
    sharpe = (ann_return - risk_free_rate) / ann_vol
    
    # Sortino
    downside = port_returns[port_returns < 0].std() * np.sqrt(252)
    sortino = (ann_return - risk_free_rate) / downside
    
    # Max Drawdown
    cumulative = (1 + port_returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    return {
        "annual_return": ann_return,
        "annual_volatility": ann_vol,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_drawdown,
        "calmar_ratio": ann_return / abs(max_drawdown)
    }
```

---

## 4. Utilidades de Datos

```python
def load_financials_from_excel(filepath: str, sheet_map: dict = None) -> dict:
    """
    Carga estados financieros desde Excel manual.
    
    sheet_map ejemplo:
    {'income': 'P&G', 'balance': 'Balance', 'cashflow': 'FCF'}
    """
    if sheet_map is None:
        sheet_map = {
            'income': 'income_statement',
            'balance': 'balance_sheet',
            'cashflow': 'cash_flow'
        }
    
    result = {}
    for key, sheet in sheet_map.items():
        try:
            result[key] = pd.read_excel(filepath, sheet_name=sheet, index_col=0)
        except Exception as e:
            print(f"⚠️ No se pudo cargar hoja '{sheet}': {e}")
    
    return result


def export_valuation_to_excel(valuation_results: dict,
                               output_path: str = "valoracion_output.xlsx"):
    """Exporta resultados de valoración a Excel formateado."""
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sheet_name, data in valuation_results.items():
            if isinstance(data, pd.DataFrame):
                data.to_excel(writer, sheet_name=sheet_name[:31])
            elif isinstance(data, dict):
                pd.DataFrame([data]).T.to_excel(
                    writer, sheet_name=sheet_name[:31], header=False
                )
    
    print(f"✅ Exportado a: {output_path}")
```

---

## 5. Estructura de Proyecto Recomendada

```
finanzas-proyecto/
├── data/
│   ├── raw/          # Datos descargados de yfinance o manuales
│   └── processed/    # Datos limpios listos para modelar
├── models/
│   ├── dcf.py        # Módulo DCF
│   ├── multiples.py  # Módulo múltiplos
│   └── portfolio.py  # Módulo portafolio
├── notebooks/
│   └── analysis.ipynb  # Exploración y presentación
├── outputs/
│   └── reports/      # Excel, HTML exportados
└── main.py           # Entry point / pipeline principal
```

---

## 6. Patrones de Automatización

**Pipeline completo de valoración:**
```python
# 1. Usuario ingresa parámetros macro UNA sola vez
macro = get_wacc_inputs()

# 2. Pipeline para N empresas
tickers = ['AAPL', 'MSFT', 'GOOGL']  # o BVC: ['PFBCOLOM.CL', 'ISA.CL']

results = {}
for ticker in tickers:
    data      = get_financial_data(ticker)
    wacc_data = calculate_wacc(ticker, macro)
    fcf       = data['cashflow'].loc['Free Cash Flow'].values.tolist()
    dcf       = dcf_valuation(
                    fcf, wacc_data['wacc'], 0.08, 0.025,
                    shares_outstanding=data['info'].get('sharesOutstanding')
                )
    results[ticker] = {**dcf, **wacc_data}

summary_df = pd.DataFrame(results).T
export_valuation_to_excel({"DCF Summary": summary_df})
```

---

## 7. Notas importantes

- **yfinance BVC:** Datos limitados para acciones colombianas. Para fundamentales BVC usar scraping de `simev.superfinanciera.gov.co` o PDFs de reportes trimestrales
- **Frecuencia datos:** Usar retornos mensuales para Markowitz con pocas acciones, diarios con >20
- **Matriz covarianzas:** Si n_activos > 15, considerar `sklearn.covariance.LedoitWolf()` para estabilidad
- **Moneda:** Siempre documentar si los modelos están en COP o USD; no mezclar sin ajuste de TRM
- Ver `references/snippets.md` para casos de uso adicionales y ejemplos de scraping BVC
