"""
Paleta de colores y CSS para el dashboard financiero.
Basado en la guia UI/UX de la skill ui-ux-finanzas.
"""

COLORS = {
    "background":    "#0E1117",
    "card":          "#1E2130",
    "border":        "#2D3147",
    "text_primary":  "#FAFAFA",
    "text_secondary":"#8B92A5",
    "positive":      "#00C853",
    "negative":      "#FF1744",
    "neutral":       "#FFD600",
    "accent":        "#4C8BF5",
    "accent_light":  "#7AB3FF",
    "chart_palette": ["#4C8BF5","#00C853","#FFD600","#FF6D00","#E040FB","#00BCD4","#FF4081","#69F0AE"],
    # PDF (fondo blanco)
    "pdf_primary":   (30, 58, 95),     # RGB dark blue
    "pdf_accent":    (76, 139, 245),   # RGB blue
    "pdf_positive":  (0, 200, 83),
    "pdf_negative":  (255, 23, 68),
    "pdf_neutral":   (255, 214, 0),
    "pdf_row_alt":   (240, 244, 250),
    "pdf_text":      (13, 13, 13),
}

PLOTLY_LAYOUT = dict(
    template        = "plotly_dark",
    paper_bgcolor   = "#0E1117",
    plot_bgcolor    = "#0E1117",
    font            = dict(family="Inter, sans-serif", color="#FAFAFA"),
    legend          = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin          = dict(t=60, b=40, l=20, r=20),
    xaxis           = dict(gridcolor="#2D3147", zerolinecolor="#2D3147"),
    yaxis           = dict(gridcolor="#2D3147", zerolinecolor="#2D3147"),
)

CSS = """
<style>
/* ── Reset y base ───────────────────────────────────────────── */
.stApp { background-color: #0E1117; }
div[data-testid="stSidebar"] { background-color: #1E2130; }

/* ── Metric cards ───────────────────────────────────────────── */
.metric-card {
    background: #1E2130;
    border: 1px solid #2D3147;
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
    height: 110px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.metric-label {
    font-size: 0.72rem;
    color: #8B92A5;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 6px;
}
.metric-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #FAFAFA;
    line-height: 1.1;
}
.metric-delta {
    font-size: 0.82rem;
    margin-top: 4px;
}
.positive { color: #00C853; }
.negative { color: #FF1744; }
.neutral  { color: #FFD600; }

/* ── Section titles ─────────────────────────────────────────── */
.section-title {
    font-size: 0.78rem;
    font-weight: 600;
    color: #8B92A5;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    border-bottom: 1px solid #2D3147;
    padding-bottom: 6px;
    margin: 22px 0 14px 0;
}

/* ── Signal badge ───────────────────────────────────────────── */
.signal-badge {
    display: inline-block;
    padding: 6px 20px;
    border-radius: 20px;
    font-size: 1.0rem;
    font-weight: 700;
    letter-spacing: 0.05em;
}
.signal-compra  { background: rgba(0,200,83,0.18);  color: #00C853; border: 1px solid #00C853; }
.signal-venta   { background: rgba(255,23,68,0.18); color: #FF1744; border: 1px solid #FF1744; }
.signal-neutral { background: rgba(255,214,0,0.18); color: #FFD600; border: 1px solid #FFD600; }

/* ── Tabs ───────────────────────────────────────────────────── */
div[data-testid="stTabs"] button {
    font-size: 0.85rem;
    font-weight: 600;
    color: #8B92A5;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #4C8BF5;
    border-bottom: 2px solid #4C8BF5;
}

/* ── Sliders ────────────────────────────────────────────────── */
div[data-testid="stSlider"] > div > div > div {
    background: #4C8BF5 !important;
}

/* ── Download button ────────────────────────────────────────── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #1e3a5f, #4C8BF5);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 10px 24px;
    transition: opacity 0.2s;
}
.stDownloadButton > button:hover { opacity: 0.88; }

/* ── Info boxes ─────────────────────────────────────────────── */
.info-box {
    background: rgba(76,139,245,0.08);
    border-left: 3px solid #4C8BF5;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    font-size: 0.85rem;
    color: #8B92A5;
    margin: 8px 0;
}

/* ── Peer table highlight ───────────────────────────────────── */
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
"""


def kpi_card(label: str, value: str, delta: str = "", delta_sign: int = 0) -> str:
    """
    Genera HTML para una tarjeta KPI.
    delta_sign: 1=positivo (verde), -1=negativo (rojo), 0=neutro (amarillo)
    """
    cls = {1: "positive", -1: "negative", 0: "neutral"}.get(delta_sign, "neutral")
    delta_html = f'<div class="metric-delta {cls}">{delta}</div>' if delta else ""
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """


def signal_badge(signal: str) -> str:
    cls = {"COMPRA": "signal-compra", "VENTA": "signal-venta"}.get(signal, "signal-neutral")
    return f'<span class="signal-badge {cls}">{signal}</span>'


def section_title(text: str) -> str:
    return f'<div class="section-title">{text}</div>'
