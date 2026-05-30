---
name: ui-ux-finanzas
description: >
  Skill de diseño UI/UX especializada en dashboards financieros con Streamlit.
  Úsala siempre que el usuario pida construir, mejorar o diseñar: dashboards de
  valoración, portafolios, análisis financiero, reportes de inversión, o cualquier
  interfaz visual con datos financieros. Aplica para Streamlit, HTML estático con
  Plotly, o cualquier frontend con propósito financiero. Si hay diseño + finanzas,
  úsala. Incluye patrones de layout, paleta de colores, tipografía, componentes
  reutilizables y estructura de proyecto lista para GitHub + Streamlit Cloud.
---

# Skill: UI/UX para Dashboards Financieros (Streamlit)

## Contexto del usuario
- Stack: Python + Streamlit + Plotly
- Destino: GitHub + Streamlit Cloud (portafolio público)
- Mercados: S&P 500 y BVC Colombia
- Audiencia: profesores, clientes, reclutadores

---

## 1. Principios de Diseño Financiero

- **Claridad sobre decoración:** los números son el protagonista, el diseño los sirve
- **Jerarquía visual clara:** métrica principal → contexto → detalle
- **Semáforo consistente:** verde = positivo/upside, rojo = negativo/downside, gris = neutro
- **Densidad de información:** mostrar máximo 4-6 KPIs en el fold inicial
- **Mobile-friendly:** Streamlit Cloud se ve en móvil — evitar tablas muy anchas

---

## 2. Paleta de Colores

```python
COLORS = {
    # Fondo y estructura
    "background":   "#0E1117",   # fondo oscuro Streamlit default
    "card":         "#1E2130",   # cards/contenedores
    "border":       "#2D3147",   # bordes sutiles

    # Tipografía
    "text_primary": "#FAFAFA",   # texto principal
    "text_secondary": "#8B92A5", # texto secundario / labels

    # Semáforo financiero
    "positive":     "#00C853",   # upside, ganancia
    "negative":     "#FF1744",   # downside, pérdida
    "neutral":      "#FFD600",   # neutral / advertencia

    # Acento de marca
    "accent":       "#4C8BF5",   # azul principal (gráficas, botones)
    "accent_light": "#7AB3FF",   # hover / secundario

    # Gráficas (secuencial para múltiples series)
    "chart_palette": [
        "#4C8BF5", "#00C853", "#FFD600",
        "#FF6D00", "#E040FB", "#00BCD4"
    ]
}
```

---

## 3. Estructura de App Streamlit

### Layout estándar para dashboard financiero
```python
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# --- Configuración de página (SIEMPRE primero) ---
st.set_page_config(
    page_title="Financial Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS personalizado ---
st.markdown("""
<style>
    /* Fondo general */
    .stApp { background-color: #0E1117; }

    /* Cards de métricas */
    .metric-card {
        background-color: #1E2130;
        border: 1px solid #2D3147;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #FAFAFA;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #8B92A5;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .positive { color: #00C853; }
    .negative { color: #FF1744; }
    .neutral  { color: #FFD600; }

    /* Sidebar */
    .css-1d391kg { background-color: #1E2130; }

    /* Títulos de sección */
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #8B92A5;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        border-bottom: 1px solid #2D3147;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)
```

### Sidebar — inputs del usuario
```python
def render_sidebar() -> dict:
    """Sidebar con todos los inputs del usuario."""
    with st.sidebar:
        st.image("assets/logo.png", width=120)  # opcional
        st.title("⚙️ Parámetros")

        st.markdown("### 📈 Empresas")
        tickers_input = st.text_input(
            "Tickers (separados por coma)",
            value="AAPL, MSFT, GOOGL",
            help="Ej: AAPL, MSFT — Para BVC: PFBCOLOM.CL, ISA.CL"
        )
        tickers = [t.strip().upper() for t in tickers_input.split(",")]

        st.markdown("### 🌍 Parámetros Macro")
        market = st.selectbox("Mercado", ["S&P 500 (USA)", "BVC (Colombia)"])

        if market == "S&P 500 (USA)":
            rf_default, tax_default, crp_default = 4.5, 21.0, 0.0
        else:
            rf_default, tax_default, crp_default = 11.5, 35.0, 2.5

        rf   = st.slider("Tasa libre de riesgo Rf (%)", 0.0, 20.0, rf_default, 0.1)
        mp   = st.slider("Prima de mercado (%)", 3.0, 9.0, 5.5, 0.1)
        crp  = st.slider("Prima de riesgo país (%)", 0.0, 8.0, crp_default, 0.1)
        tax  = st.slider("Tasa de impuestos (%)", 0.0, 40.0, tax_default, 0.5)
        g    = st.slider("Crecimiento terminal g (%)", 1.0, 5.0, 2.5, 0.1)

        run = st.button("🚀 Ejecutar Valoración", use_container_width=True, type="primary")

    return {
        "tickers": tickers,
        "rf": rf / 100,
        "market_premium": mp / 100,
        "country_risk_premium": crp / 100,
        "tax_rate": tax / 100,
        "terminal_growth": g / 100,
        "run": run
    }
```

---

## 4. Componentes Reutilizables

### KPI Card
```python
def kpi_card(label: str, value: str, delta: str = None, delta_positive: bool = None):
    """
    Tarjeta de métrica individual.
    delta_positive: True=verde, False=rojo, None=amarillo
    """
    delta_class = ""
    if delta:
        if delta_positive is True:
            delta_class = "positive"
        elif delta_positive is False:
            delta_class = "negative"
        else:
            delta_class = "neutral"

    delta_html = f'<div class="{delta_class}" style="font-size:0.9rem">{delta}</div>' if delta else ""

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)
```

### Tabla comparativa de valoración
```python
def render_valuation_table(results: dict):
    """
    Tabla resumen con semáforo de upside/downside.
    results: {ticker: {price_target, current_price, upside, wacc, ...}}
    """
    st.markdown('<div class="section-title">📋 Resumen de Valoración</div>',
                unsafe_allow_html=True)

    rows = []
    for ticker, data in results.items():
        upside = data.get("upside", 0)
        rows.append({
            "Empresa":         ticker,
            "Precio Objetivo": f"${data['price_target']:.2f}",
            "Precio Actual":   f"${data['current_price']:.2f}",
            "Upside/Downside": f"{upside:+.1f}%",
            "WACC":            f"{data['wacc']:.2%}",
            "EV ($B)":         f"${data['enterprise_value']/1e9:.1f}B",
            "Recomendación":   "🟢 COMPRA" if upside > 15 else ("🔴 VENTA" if upside < -10 else "🟡 NEUTRAL")
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
```

### Gráfica precio objetivo vs actual
```python
def plot_price_comparison(results: dict):
    """Bar chart comparando precio objetivo vs precio de mercado."""
    tickers = list(results.keys())
    targets  = [results[t]["price_target"]  for t in tickers]
    currents = [results[t]["current_price"] for t in tickers]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Precio Objetivo (DCF)",
        x=tickers, y=targets,
        marker_color="#4C8BF5",
        text=[f"${v:.0f}" for v in targets],
        textposition="outside"
    ))
    fig.add_trace(go.Bar(
        name="Precio Actual",
        x=tickers, y=currents,
        marker_color="#8B92A5",
        text=[f"${v:.0f}" for v in currents],
        textposition="outside"
    ))
    fig.update_layout(
        barmode="group",
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        title="Precio Objetivo DCF vs Precio de Mercado",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=60, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)
```

### Heatmap tabla de sensibilidad
```python
def plot_sensitivity_heatmap(sensitivity_df: pd.DataFrame, ticker: str):
    """Heatmap de sensibilidad WACC vs g terminal."""
    fig = px.imshow(
        sensitivity_df,
        color_continuous_scale=["#FF1744", "#FFD600", "#00C853"],
        title=f"Sensibilidad DCF — {ticker} (Precio por acción USD)",
        text_auto=True,
        aspect="auto"
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        coloraxis_showscale=True
    )
    st.plotly_chart(fig, use_container_width=True)
```

---

## 5. Estructura de Proyecto para GitHub

```
finanzas-dashboard/
├── app.py                  # Entry point principal (streamlit run app.py)
├── requirements.txt        # Dependencias
├── README.md               # Documentación + badge Streamlit
├── .gitignore
├── modules/
│   ├── valuation.py        # DCF, WACC, múltiplos
│   ├── portfolio.py        # Markowitz, métricas
│   └── data.py             # Descarga y limpieza yfinance
├── components/
│   ├── charts.py           # Todas las gráficas Plotly
│   ├── tables.py           # Tablas y KPI cards
│   └── styles.py           # CSS y colores (COLORS dict)
└── assets/
    └── logo.png            # Opcional
```

### requirements.txt estándar
```
streamlit>=1.32.0
yfinance>=0.2.36
plotly>=5.19.0
pandas>=2.0.0
numpy>=1.26.0
scipy>=1.12.0
openpyxl>=3.1.0
```

### README.md con badge
```markdown
# 📊 Financial Valuation Dashboard

Dashboard de valoración de empresas (DCF + Múltiplos) y optimización
de portafolios. Mercados: S&P 500 y BVC Colombia.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://tuapp.streamlit.app)

## Uso local
pip install -r requirements.txt
streamlit run app.py
```

---

## 6. Patrones de UX Financiero

**Flujo recomendado de la app:**
```
Sidebar (inputs) → Loading spinner → KPIs resumen (fold 1)
→ Tabla comparativa → Gráfica precios → Tabs por empresa
→ [Tab empresa] Sensibilidad + Waterfall EV → Portafolio (opcional)
```

**Loading states:**
```python
with st.spinner("⏳ Descargando datos y calculando valoraciones..."):
    results = run_valuation_pipeline(params)
st.success("✅ Valoración completada")
```

**Tabs por empresa:**
```python
if results:
    tabs = st.tabs([f"📈 {t}" for t in tickers])
    for i, ticker in enumerate(tickers):
        with tabs[i]:
            col1, col2 = st.columns(2)
            with col1:
                plot_sensitivity_heatmap(results[ticker]["sensitivity"], ticker)
            with col2:
                # métricas detalladas
                pass
```

**Manejo de errores visible:**
```python
try:
    data = get_financial_data(ticker)
except Exception as e:
    st.error(f"❌ No se pudo obtener datos para {ticker}: {e}")
    st.info("💡 Para BVC usa sufijo .CL — Ej: PFBCOLOM.CL")
```

---

## 7. Despliegue en Streamlit Cloud

```bash
# 1. Subir a GitHub
git init
git add .
git commit -m "feat: financial valuation dashboard"
git remote add origin https://github.com/tuuser/finanzas-dashboard.git
git push -u origin main

# 2. En share.streamlit.io
# - New app → seleccionar repo → main → app.py → Deploy
```

**Checklist antes de subir:**
- [ ] No hay API keys hardcodeadas en el código
- [ ] `requirements.txt` tiene todas las dependencias
- [ ] App corre sin errores con `streamlit run app.py`
- [ ] Datos sensibles en `st.secrets` si aplica
