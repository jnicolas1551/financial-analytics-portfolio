"""
Dashboard de Analisis Fundamental — Portafolio Institucional
Valoracion por DCF + Multiplos de Pares | Yahoo Finance | Streamlit
Repositorio: financial-analytics-portfolio
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ── Configuracion de pagina (DEBE ir primero) ──────────────────────────────
st.set_page_config(
    page_title="Analisis Fundamental | Portafolio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports locales ────────────────────────────────────────────────────────
from components.styles      import CSS, COLORS, kpi_card, signal_badge, section_title
from components.charts      import (
    chart_price_history, chart_fcf_projection, chart_wacc_waterfall,
    chart_sensitivity_heatmap, chart_peer_comparison,
    chart_efficiency_bars, chart_portfolio_summary,
)
from modules.data_fetcher   import fetch_company_data, fetch_peers_data
from modules.dcf_model      import calculate_wacc, get_fcf_base, run_dcf, dcf_sensitivity
from modules.multiples_model import run_multiples_analysis, METRIC_CONFIG
from modules.report_generator import generate_pdf, generate_excel

st.markdown(CSS, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CACHE
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch(ticker: str) -> dict:
    return fetch_company_data(ticker)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_peers(peer_tickers: tuple) -> list:
    return fetch_peers_data(list(peer_tickers))


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown("## 📊 Analisis Fundamental")
        st.markdown("---")

        # Tickers
        st.markdown("### 📈 Portafolio")
        tickers_raw = st.text_area(
            "Tickers (uno por linea o separados por coma)",
            value="AAPL\nMSFT\nGOOGL",
            height=100,
            help="Ej: AAPL, DPZ, ECOPETROL.CL — soporta cualquier mercado de Yahoo Finance",
        )
        tickers = [t.strip().upper() for t in tickers_raw.replace(",", "\n").splitlines() if t.strip()]

        # Peers personalizados
        with st.expander("🔧 Peers manuales (opcional)", expanded=False):
            peers_raw = st.text_area(
                "Peers adicionales (reemplaza los automaticos)",
                value="",
                height=80,
                help="Deja vacio para usar peers automaticos por sector",
            )
            custom_peers = [t.strip().upper() for t in peers_raw.replace(",","\n").splitlines() if t.strip()]

        st.markdown("---")

        # DCF
        st.markdown("### 💹 Parametros DCF")
        growth_explicit = st.slider(
            "Tasa crecimiento explicito (%)", 0.0, 25.0, 8.0, 0.5,
            help="Tasa anual de crecimiento del FCF en el periodo de proyeccion. "
                 "Se mostrara la tasa historica calculada como referencia.",
        ) / 100
        terminal_growth = st.slider(
            "Crecimiento terminal g (%)", 0.0, 5.0, 2.5, 0.1,
            help="Tasa de crecimiento a perpetuidad. Debe ser < WACC.",
        ) / 100
        explicit_years = st.slider("Anos de proyeccion", 3, 10, 5, 1)

        st.markdown("---")

        # Pesos multiplos
        st.markdown("### ⚖️ Pesos Multiplos")
        st.caption("Ajusta la importancia de cada metrica. La suma debe ser 100%.")

        w_ev_ebitda   = st.slider("EV/EBITDA",     0, 100, 40, 5)
        w_ebitda_mg   = st.slider("Margen EBITDA", 0, 100, 30, 5)
        w_roe         = st.slider("ROE",           0, 100, 15, 5)
        w_pe          = st.slider("P/E",           0, 100, 10, 5)
        w_yield       = st.slider("Div. Yield",    0, 100,  5, 5)

        total_w = w_ev_ebitda + w_ebitda_mg + w_roe + w_pe + w_yield
        delta_w = total_w - 100
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            st.metric("Suma pesos", f"{total_w}%")
        with col_w2:
            if total_w != 100:
                st.warning(f"Ajusta {delta_w:+d}%")
            else:
                st.success("✓ 100%")

        weights = {
            "ev_ebitda":        w_ev_ebitda,
            "ebitda_margin":    w_ebitda_mg,
            "return_on_equity": w_roe,
            "trailing_pe":      w_pe,
            "dividend_yield":   w_yield,
        }

        st.markdown("---")

        # Overrides WACC por pais
        with st.expander("🌍 Override WACC por pais", expanded=False):
            st.caption("Deja en 0 para usar los valores Damodaran auto-detectados.")
            override_rf    = st.number_input("Rf override (%)", 0.0, 30.0, 0.0, 0.1) / 100
            override_crp   = st.number_input("CRP override (%)", 0.0, 30.0, 0.0, 0.1) / 100
            override_tax   = st.number_input("Tasa impuestos override (%)", 0.0, 50.0, 0.0, 0.5) / 100
            override_mp    = st.number_input("Prima mercado override (%)", 0.0, 15.0, 0.0, 0.1) / 100

        wacc_override: dict = {}
        if override_rf  > 0: wacc_override["rf"]          = override_rf
        if override_crp > 0: wacc_override["crp"]         = override_crp
        if override_tax > 0: wacc_override["tax_rate"]    = override_tax
        if override_mp  > 0: wacc_override["mkt_premium"] = override_mp

        st.markdown("---")
        run_btn = st.button("🚀 Analizar Portafolio", type="primary", use_container_width=True)

    return {
        "tickers":         tickers,
        "custom_peers":    custom_peers,
        "growth_explicit": growth_explicit,
        "terminal_growth": terminal_growth,
        "explicit_years":  explicit_years,
        "weights":         weights,
        "wacc_override":   wacc_override,
        "run":             run_btn,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE DE ANALISIS
# ══════════════════════════════════════════════════════════════════════════════

def run_analysis(params: dict) -> dict:
    """
    Descarga datos y corre DCF + Multiplos para cada ticker.
    Retorna dict {ticker: {metrics, dcf, multiples, wacc_data, ...}}
    """
    portfolio = {}
    errors    = {}
    tickers   = params["tickers"]

    progress = st.progress(0, text="Iniciando analisis...")

    for i, ticker in enumerate(tickers):
        progress.progress((i) / len(tickers), text=f"Descargando {ticker}...")
        try:
            raw = cached_fetch(ticker)
        except Exception as e:
            errors[ticker] = f"Error descargando datos: {e}"
            continue

        metrics    = raw["metrics"]
        history    = raw["history"]
        fcf_hist   = raw["fcf_history"]
        country    = raw["country"]
        auto_peers = raw["auto_peers"]

        # Peers
        peer_list = params["custom_peers"] if params["custom_peers"] else auto_peers
        peer_list = [p for p in peer_list if p != ticker][:6]

        progress.progress((i + 0.4) / len(tickers), text=f"Descargando peers de {ticker}...")
        try:
            peers_data = cached_peers(tuple(peer_list)) if peer_list else []
        except Exception:
            peers_data = []

        # WACC
        override = params["wacc_override"] or {}
        try:
            wacc_data = calculate_wacc(metrics, country, override)
        except Exception as e:
            wacc_data = {"wacc": 0.10, "error": str(e)}

        # FCF base
        fcf_data = get_fcf_base(metrics, fcf_hist)

        # DCF
        try:
            dcf_result = run_dcf(
                metrics, fcf_data, wacc_data,
                params["growth_explicit"],
                params["terminal_growth"],
                params["explicit_years"],
            )
        except Exception as e:
            dcf_result = {"error": str(e)}

        # Sensibilidad
        sens_df = None
        if dcf_result and not dcf_result.get("error"):
            try:
                sens_df = dcf_sensitivity(
                    metrics, fcf_data, wacc_data,
                    params["growth_explicit"],
                    params["explicit_years"],
                )
            except Exception:
                pass

        # Multiplos
        progress.progress((i + 0.75) / len(tickers), text=f"Analizando multiplos {ticker}...")
        try:
            mult_result = run_multiples_analysis(metrics, peers_data, params["weights"])
        except Exception as e:
            mult_result = {"error": str(e)}

        portfolio[ticker] = {
            "metrics":     metrics,
            "history":     history,
            "fcf_data":    fcf_data,
            "dcf":         dcf_result,
            "multiples":   mult_result,
            "wacc_data":   wacc_data,
            "country":     country,
            "sensitivity": sens_df,
            "peers":       peers_data,
            "peer_list":   peer_list,
        }

    progress.progress(1.0, text="Analisis completado.")
    return portfolio, errors


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS DE VISUALIZACION
# ══════════════════════════════════════════════════════════════════════════════

def _safe(v, default="N/A"):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return default
    return v

def _fmt_price(v, ccy="USD"):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    return f"{v:,.2f} {ccy}"

def _fmt_pct(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    return f"{v:.2%}"

def _fmt_mult(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    return f"{v:.1f}x"

def _get_signal(current, target):
    if not current or not target:
        return "SIN DATOS", 0, 0
    pot = target / current - 1
    if pot > 0.15:   return "COMPRA",  pot,  1
    if pot < -0.10:  return "VENTA",   pot, -1
    return "NEUTRAL", pot, 0

def _best_po(dcf, mult):
    po_m = (mult or {}).get("combined_price")
    po_d = None
    if dcf and not dcf.get("error"):
        po_d = dcf.get("price_per_share")
    return po_m, po_d


# ══════════════════════════════════════════════════════════════════════════════
# TABS DE VISUALIZACION
# ══════════════════════════════════════════════════════════════════════════════

def render_overview(portfolio: dict):
    """Tab de resumen del portafolio completo."""
    st.markdown(section_title("Vista general del portafolio"), unsafe_allow_html=True)

    # KPI cards del portafolio
    n_compra = sum(
        1 for d in portfolio.values()
        if _get_signal(
            d["metrics"].get("current_price"),
            d["multiples"].get("combined_price") or
            (d["dcf"].get("price_per_share") if d["dcf"] and not d["dcf"].get("error") else None)
        )[0] == "COMPRA"
    )
    n_venta = sum(
        1 for d in portfolio.values()
        if _get_signal(
            d["metrics"].get("current_price"),
            d["multiples"].get("combined_price") or
            (d["dcf"].get("price_per_share") if d["dcf"] and not d["dcf"].get("error") else None)
        )[0] == "VENTA"
    )
    n_neutral = len(portfolio) - n_compra - n_venta

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(kpi_card("Activos Analizados", str(len(portfolio))), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("Senales COMPRA", str(n_compra), delta_sign=1), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("Senales NEUTRAL", str(n_neutral), delta_sign=0), unsafe_allow_html=True)
    with c4: st.markdown(kpi_card("Senales VENTA",  str(n_venta),  delta_sign=-1), unsafe_allow_html=True)

    st.plotly_chart(chart_portfolio_summary(portfolio), use_container_width=True)
    st.markdown("---")

    # Tabla resumen
    rows = []
    for tk, data in portfolio.items():
        m    = data["metrics"]
        dcf  = data["dcf"]
        mult = data["multiples"]
        cp   = m.get("current_price", 0) or 0
        ccy  = m.get("currency", "USD")
        fx   = m.get("fx_to_usd", 1.0) or 1.0
        po_m, po_d = _best_po(dcf, mult)
        sig, pot, _ = _get_signal(cp, po_m or po_d)
        wacc = data.get("wacc_data", {}).get("wacc")

        rows.append({
            "Ticker":           tk,
            "Empresa":          (m.get("name","") or "")[:35],
            "Pais":             m.get("country",""),
            "Moneda":           ccy,
            "Precio Actual":    f"{cp:,.2f}",
            "PO Multiplos":     f"{po_m:,.2f}" if po_m else "N/A",
            "PO DCF":           f"{po_d:,.2f}" if po_d else "N/A",
            "Potencial":        f"{pot:.1%}" if pot else "N/A",
            "WACC":             f"{wacc:.2%}" if wacc else "N/A",
            "EV/EBITDA":        _fmt_mult(m.get("ev_ebitda")),
            "Margen EBITDA":    _fmt_pct(m.get("ebitda_margin")),
            "Senal":            sig,
        })

    df = pd.DataFrame(rows)

    def _color_signal(v):
        if v == "COMPRA":  return "color: #00C853; font-weight: bold"
        if v == "VENTA":   return "color: #FF1744; font-weight: bold"
        return "color: #FFD600; font-weight: bold"

    styled = df.style.applymap(_color_signal, subset=["Senal"])
    st.dataframe(styled, use_container_width=True, hide_index=True)


def render_company_tab(ticker: str, data: dict, params: dict):
    """Contenido de la tab de una empresa individual."""
    m       = data["metrics"]
    dcf     = data["dcf"]
    mult    = data["multiples"]
    wacc_d  = data["wacc_data"]
    history = data["history"]
    sens    = data["sensitivity"]
    country = data["country"]
    cp      = m.get("current_price", 0) or 0
    ccy     = m.get("currency", "USD")
    fx      = m.get("fx_to_usd", 1.0) or 1.0
    po_m, po_d = _best_po(dcf, mult)
    sig, pot, sign = _get_signal(cp, po_m or po_d)

    # ── Header ──────────────────────────────────────────────────────────────
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"### {ticker} — {m.get('name','')}")
        st.caption(f"{m.get('sector','')} | {m.get('industry','')} | {m.get('country','')} | {ccy}")
        if not country.get("detected"):
            st.info("⚠️ Pais no encontrado en tabla Damodaran — usando parametros globales por defecto.")
    with col_h2:
        st.markdown(signal_badge(sig), unsafe_allow_html=True)
        st.markdown(f"**Potencial:** {_fmt_pct(pot)}")
        if ccy != "USD":
            st.caption(f"Precio USD equiv: {cp * fx:,.2f}")

    # ── KPIs ────────────────────────────────────────────────────────────────
    st.markdown(section_title("Metricas Clave"), unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    mc  = m.get("market_cap", 0) or 0
    ev  = m.get("enterprise_value", 0) or 0
    ebd = m.get("ebitda", 0) or 0

    kpis = [
        (c1, "Precio Actual",  f"{cp:,.2f} {ccy}",        "", 0),
        (c2, "Market Cap",     f"USD {mc/1e9:.2f}B",       "", 0),
        (c3, "EV",             f"USD {ev/1e9:.2f}B",       "", 0),
        (c4, "EBITDA",         f"USD {ebd/1e9:.2f}B",      "", 0),
        (c5, "Margen EBITDA",  _fmt_pct(m.get("ebitda_margin")), "", 0),
        (c6, "Beta",           f"{m.get('beta', 0):.2f}",  "", 0),
    ]
    for col, lbl, val, delta, ds in kpis:
        with col:
            st.markdown(kpi_card(lbl, val, delta, ds), unsafe_allow_html=True)

    st.markdown("")
    c7, c8, c9, c10, c11, c12 = st.columns(6)
    kpis2 = [
        (c7,  "P/E",           _fmt_mult(m.get("trailing_pe")),      "", 0),
        (c8,  "EV/EBITDA",     _fmt_mult(m.get("ev_ebitda")),        "", 0),
        (c9,  "ROE",           _fmt_pct(m.get("return_on_equity")),  "", 0),
        (c10, "Div. Yield",    _fmt_pct(m.get("dividend_yield")),    "", 0),
        (c11, "WACC",          _fmt_pct(wacc_d.get("wacc")),         "", 0),
        (c12, "Deuda/EBITDA",  f"{(m.get('total_debt',0) or 0) / max(ebd,1):.1f}x", "", 0),
    ]
    for col, lbl, val, delta, ds in kpis2:
        with col:
            st.markdown(kpi_card(lbl, val, delta, ds), unsafe_allow_html=True)

    # ── Grafica precio historico ─────────────────────────────────────────────
    st.markdown("")
    st.plotly_chart(
        chart_price_history(history, ticker, po_d, po_m),
        use_container_width=True,
    )

    # ── DCF ─────────────────────────────────────────────────────────────────
    st.markdown(section_title("Valoracion DCF — Flujos de Caja Descontados"), unsafe_allow_html=True)

    if dcf and not dcf.get("error"):
        col_w, col_r = st.columns([1, 1])

        with col_w:
            st.markdown("**Componentes WACC**")
            # FCF historico como referencia
            fcf_data = data.get("fcf_data", {})
            if fcf_data.get("fcf_growth_hist") or m.get("fcf_growth_hist"):
                gh = m.get("fcf_growth_hist") or fcf_data.get("fcf_growth_hist")
                st.info(f"📌 Tasa historica FCF (CAGR): **{gh:.1%}**  "
                        f"(comparar con tasa explicita usada: {params['growth_explicit']:.1%})")

            wacc_table = pd.DataFrame([
                {"Componente": "WACC",             "Valor": _fmt_pct(wacc_d.get("wacc"))},
                {"Componente": "Ke (costo equity)","Valor": _fmt_pct(wacc_d.get("ke"))},
                {"Componente": "Kd after-tax",     "Valor": _fmt_pct(wacc_d.get("kd"))},
                {"Componente": "Beta",              "Valor": f"{wacc_d.get('beta',0):.2f}"},
                {"Componente": "Rf",                "Valor": _fmt_pct(wacc_d.get("rf"))},
                {"Componente": "Prima mercado",     "Valor": _fmt_pct(wacc_d.get("mkt_premium"))},
                {"Componente": "Prima pais (CRP)",  "Valor": _fmt_pct(wacc_d.get("crp"))},
                {"Componente": "Tasa impuestos",    "Valor": _fmt_pct(wacc_d.get("tax_rate"))},
                {"Componente": "Peso equity",       "Valor": _fmt_pct(wacc_d.get("weight_equity"))},
                {"Componente": "Peso deuda",        "Valor": _fmt_pct(wacc_d.get("weight_debt"))},
            ])
            st.dataframe(wacc_table, hide_index=True, use_container_width=True)
            st.plotly_chart(chart_wacc_waterfall(wacc_d, ticker), use_container_width=True)

        with col_r:
            st.markdown("**Resultados DCF**")
            dcf_table = pd.DataFrame([
                {"Item": "FCF base",              "Valor": f"USD {dcf.get('base_fcf',0)/1e6:.1f}M"},
                {"Item": "Tasa crec. explicito",  "Valor": _fmt_pct(dcf.get("growth_explicit"))},
                {"Item": "Tasa crec. terminal g", "Valor": _fmt_pct(dcf.get("terminal_growth"))},
                {"Item": "VP periodo explicito",  "Valor": f"USD {(dcf.get('pv_explicit',0) or 0)/1e9:.2f}B"},
                {"Item": "Valor terminal",        "Valor": f"USD {(dcf.get('terminal_value',0) or 0)/1e9:.2f}B"},
                {"Item": "VP valor terminal",     "Valor": f"USD {(dcf.get('pv_terminal',0) or 0)/1e9:.2f}B"},
                {"Item": "% valor terminal",      "Valor": _fmt_pct(dcf.get("terminal_pct"))},
                {"Item": "EV (DCF)",              "Valor": f"USD {(dcf.get('ev_dcf',0) or 0)/1e9:.2f}B"},
                {"Item": "Equity value",          "Valor": f"USD {(dcf.get('equity_dcf',0) or 0)/1e9:.2f}B"},
                {"Item": f"🎯 Precio objetivo {ccy}", "Valor": _fmt_price(dcf.get("price_per_share"), ccy)},
            ])
            st.dataframe(dcf_table, hide_index=True, use_container_width=True)

        # Proyeccion FCF
        st.plotly_chart(chart_fcf_projection(dcf, ticker), use_container_width=True)

        # Sensibilidad
        if sens is not None and not sens.empty:
            st.markdown(section_title("Tabla de Sensibilidad — WACC × g terminal"), unsafe_allow_html=True)
            st.caption(f"Precio actual: **{_fmt_price(cp, ccy)}** | Verde = por encima del precio actual, Rojo = por debajo")
            st.plotly_chart(
                chart_sensitivity_heatmap(sens, ticker, cp),
                use_container_width=True,
            )
    else:
        err = (dcf or {}).get("error", "Sin datos de FCF disponibles.")
        st.warning(f"⚠️ DCF no calculado: {err}")
        st.markdown(
            '<div class="info-box">💡 Tip: El DCF requiere FCF positivo y WACC > g terminal. '
            "Si la empresa tiene FCF negativo (startup, reestructuracion), el modelo de multiplos "
            "es mas adecuado.</div>",
            unsafe_allow_html=True,
        )

    # ── Multiplos ────────────────────────────────────────────────────────────
    st.markdown(section_title("Analisis de Comparables — Multiplos de Pares"), unsafe_allow_html=True)

    if mult and not mult.get("error"):
        peer_df = mult.get("peer_table", pd.DataFrame())
        direct  = mult.get("direct_prices", {})
        eff     = mult.get("efficiency", {})
        w_eff   = mult.get("weighted_eff", 0)

        # Precios objetivo directos
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        cols_po = [col_p1, col_p2, col_p3, col_p4]
        po_items = [
            ("PO EV/EBITDA", direct.get("ev_ebitda"), 0),
            ("PO P/E",       direct.get("pe"),         0),
            ("PO EV/Rev.",   direct.get("ev_revenue"), 0),
            ("PO Combinado", mult.get("combined_price"), sign),
        ]
        for col, (lbl, val, ds) in zip(cols_po, po_items):
            pot_str = f"vs actual: {(val/cp-1):.1%}" if val and cp else ""
            with col:
                st.markdown(kpi_card(lbl, _fmt_price(val, ccy), pot_str, ds), unsafe_allow_html=True)

        st.markdown(f"**Eficiencia ponderada total:** {w_eff:+.1%}")
        col_info = st.columns([1])[0]
        st.markdown(
            '<div class="info-box">La eficiencia mide cuanto mejor o peor es la empresa '
            "vs la mediana de sus peers en las metricas ponderadas. "
            "Positivo = empresa es 'mejor' que peers → merece prima. "
            "Negativo = empresa es 'peor' → merece descuento.</div>",
            unsafe_allow_html=True,
        )

        # Graficas comparables
        col_g1, col_g2 = st.columns([3, 2])
        with col_g1:
            if not peer_df.empty:
                st.plotly_chart(
                    chart_peer_comparison(peer_df, mult.get("target_vals", {}), ticker),
                    use_container_width=True,
                )
        with col_g2:
            if eff:
                st.plotly_chart(chart_efficiency_bars(eff, ticker), use_container_width=True)

        # Tabla peers detallada
        if not peer_df.empty:
            st.markdown("**Tabla de peers**")

            def _style_peer(df):
                return df.style.format({
                    "EV/EBITDA":  lambda x: f"{x:.1f}x" if pd.notna(x) and x else "N/A",
                    "P/E":        lambda x: f"{x:.1f}x" if pd.notna(x) and x else "N/A",
                    "Mg. EBITDA": lambda x: f"{x:.1%}"  if pd.notna(x) and x else "N/A",
                    "ROE":        lambda x: f"{x:.1%}"  if pd.notna(x) and x else "N/A",
                    "Div. Yield": lambda x: f"{x:.2%}"  if pd.notna(x) and x else "N/A",
                    "Q Tobin":    lambda x: f"{x:.2f}x" if pd.notna(x) and x else "N/A",
                    "Beta":       lambda x: f"{x:.2f}"  if pd.notna(x) and x else "N/A",
                }, na_rep="N/A")

            st.dataframe(_style_peer(peer_df), use_container_width=True, hide_index=True)
    else:
        err = (mult or {}).get("error", "Sin peers disponibles.")
        st.warning(f"⚠️ Multiplos no calculados: {err}")

    # ── Resumen final ────────────────────────────────────────────────────────
    st.markdown(section_title("Resumen y Recomendacion"), unsafe_allow_html=True)
    col_r1, col_r2 = st.columns([2, 1])
    with col_r1:
        resumen = pd.DataFrame([
            {"Metrica":           "Precio actual de mercado",
             "Valor":             _fmt_price(cp, ccy)},
            {"Metrica":           "Precio objetivo DCF",
             "Valor":             _fmt_price(po_d, ccy) if po_d else "N/A"},
            {"Metrica":           "Precio objetivo Multiplos",
             "Valor":             _fmt_price(po_m, ccy) if po_m else "N/A"},
            {"Metrica":           "Potencial de valoracion",
             "Valor":             _fmt_pct(pot)},
            {"Metrica":           "WACC",
             "Valor":             _fmt_pct(wacc_d.get("wacc"))},
            {"Metrica":           "Pais detectado",
             "Valor":             country.get("country_name", "N/A")},
        ])
        st.dataframe(resumen, hide_index=True, use_container_width=True)
    with col_r2:
        st.markdown(signal_badge(sig), unsafe_allow_html=True)
        st.markdown(f"**{_fmt_pct(pot)}** de potencial")
        st.caption("Basado en PO Multiplos como metrica principal.")
        if ccy != "USD":
            price_usd = cp * fx
            po_usd    = (po_m or 0) * fx if po_m else None
            st.caption(f"En USD: actual = {price_usd:,.2f} | PO = {po_usd:,.2f}" if po_usd else "")


# ══════════════════════════════════════════════════════════════════════════════
# APP PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def main():
    params = render_sidebar()

    # Disparar analisis
    if params["run"] and params["tickers"]:
        with st.spinner("⏳ Descargando datos y calculando valoraciones..."):
            portfolio, errors = run_analysis(params)
        st.session_state["portfolio"] = portfolio
        st.session_state["errors"]    = errors
        st.session_state["params"]    = params
        if errors:
            for tk, err in errors.items():
                st.error(f"❌ {tk}: {err}")
        st.success(f"✅ Analisis completado — {len(portfolio)} activos procesados.")

    elif params["run"] and not params["tickers"]:
        st.warning("⚠️ Ingresa al menos un ticker en el sidebar.")

    # Mostrar resultados si existen
    portfolio = st.session_state.get("portfolio", {})
    saved_params = st.session_state.get("params", params)

    if not portfolio:
        # Landing page
        st.markdown("# 📊 Analisis Fundamental Institucional")
        st.markdown("### Valoracion por DCF y Multiplos de Pares — Multi-mercado")
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**📈 Valoracion DCF**")
            st.markdown("- WACC auto-detectado por pais (Damodaran)\n- FCF proyectado a 5-10 anos\n- Valor terminal Gordon Growth\n- Tabla de sensibilidad WACC × g")
        with col2:
            st.markdown("**🔄 Multiplos de Pares**")
            st.markdown("- Peers automaticos por sector\n- EV/EBITDA, P/E, Margen EBITDA, ROE, Yield\n- Pesos ajustables por el usuario\n- Scoring de eficiencia relativa")
        with col3:
            st.markdown("**📄 Reportes**")
            st.markdown("- PDF investing memo profesional\n- Excel multi-hoja con todos los datos\n- Tipo de cambio automatico\n- Soporte USD, COP, EUR, MXN y mas")
        st.markdown("---")
        st.info("👈 Ingresa los tickers en el panel izquierdo y haz clic en **Analizar Portafolio**")
        return

    # Tabs
    tab_labels = ["🌐 Portafolio"] + [f"📈 {tk}" for tk in portfolio] + ["📥 Descargas"]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        render_overview(portfolio)

    for i, (ticker, data) in enumerate(portfolio.items()):
        with tabs[i + 1]:
            render_company_tab(ticker, data, saved_params)

    with tabs[-1]:
        st.markdown(section_title("Descargar Reportes"), unsafe_allow_html=True)
        st.markdown("Genera el investing memo en PDF y el modelo completo en Excel con todos los datos del analisis.")

        col_d1, col_d2 = st.columns(2)

        with col_d1:
            st.markdown("#### 📄 PDF — Investing Memo")
            st.markdown("Documento profesional con:\n- Portada y resumen del portafolio\n- Seccion completa por empresa\n- Graficas de precio, FCF, sensibilidad y eficiencia\n- Tablas WACC y comparables\n- Disclaimer metodologico")
            if st.button("⚙️ Generar PDF", use_container_width=True):
                with st.spinner("Generando PDF..."):
                    try:
                        pdf_bytes = generate_pdf(portfolio)
                        fecha = datetime.now().strftime("%Y%m%d_%H%M")
                        st.download_button(
                            label="📥 Descargar Investing Memo PDF",
                            data=pdf_bytes,
                            file_name=f"investing_memo_{fecha}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"Error generando PDF: {e}")

        with col_d2:
            st.markdown("#### 📊 Excel — Modelo Completo")
            st.markdown("Archivo Excel con:\n- Hoja resumen del portafolio\n- Una hoja por empresa con:\n  - Metricas y WACC\n  - Proyeccion FCF\n  - Tabla de peers\n  - Sensibilidad DCF\n- Formato profesional con colores")
            if st.button("⚙️ Generar Excel", use_container_width=True):
                with st.spinner("Generando Excel..."):
                    try:
                        xl_bytes = generate_excel(portfolio)
                        fecha = datetime.now().strftime("%Y%m%d_%H%M")
                        st.download_button(
                            label="📥 Descargar Modelo Excel",
                            data=xl_bytes,
                            file_name=f"analisis_fundamental_{fecha}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"Error generando Excel: {e}")

        # Metadata del analisis
        st.markdown("---")
        st.markdown("**Datos del analisis**")
        meta = pd.DataFrame([
            {"Campo": "Tickers analizados",    "Valor": ", ".join(portfolio.keys())},
            {"Campo": "Fecha/hora",             "Valor": datetime.now().strftime("%Y-%m-%d %H:%M")},
            {"Campo": "Tasa crec. explicito",   "Valor": _fmt_pct(saved_params.get("growth_explicit"))},
            {"Campo": "Tasa crec. terminal g",  "Valor": _fmt_pct(saved_params.get("terminal_growth"))},
            {"Campo": "Anos de proyeccion",     "Valor": str(saved_params.get("explicit_years"))},
            {"Campo": "Fuente de datos",        "Valor": "Yahoo Finance (yfinance)"},
            {"Campo": "Datos WACC pais",        "Valor": "Damodaran Country Risk Premium 2024"},
        ])
        st.dataframe(meta, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
