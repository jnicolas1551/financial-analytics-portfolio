"""
Graficos Plotly (dashboard interactivo) y Matplotlib (exportacion PDF).
"""
import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from components.styles import COLORS, PLOTLY_LAYOUT


def _layout(**kw) -> dict:
    base = dict(PLOTLY_LAYOUT)
    base.update(kw)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# GRAFICOS PLOTLY (Streamlit)
# ══════════════════════════════════════════════════════════════════════════════

def chart_price_history(history: pd.DataFrame, ticker: str,
                         po_dcf: float | None = None,
                         po_mult: float | None = None) -> go.Figure:
    """Precio historico + lineas de precio objetivo."""
    if history.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history.index, y=history["Close"],
        name="Precio cierre",
        line=dict(color=COLORS["accent"], width=1.8),
        fill="tozeroy",
        fillcolor="rgba(76,139,245,0.08)",
    ))

    current = float(history["Close"].iloc[-1])
    fig.add_hline(y=current, line_dash="dot", line_color=COLORS["text_secondary"],
                  annotation_text=f"Actual {current:.1f}", annotation_position="bottom right")

    if po_dcf:
        color = COLORS["positive"] if po_dcf > current else COLORS["negative"]
        fig.add_hline(y=po_dcf, line_dash="dash", line_color=color,
                      annotation_text=f"PO DCF {po_dcf:.1f}", annotation_position="top right")
    if po_mult:
        color = COLORS["positive"] if po_mult > current else COLORS["negative"]
        fig.add_hline(y=po_mult, line_dash="longdash", line_color=color,
                      annotation_text=f"PO Mult {po_mult:.1f}", annotation_position="top left")

    fig.update_layout(**_layout(title=f"{ticker} — Precio Historico (5 anos)"))
    return fig


def chart_fcf_projection(dcf: dict, ticker: str) -> go.Figure:
    """Barras de FCF proyectado + VP en el periodo explicito."""
    if not dcf or dcf.get("error"):
        return go.Figure()

    years  = [f"Ano {i+1}" for i in range(dcf["explicit_years"])]
    fcfs   = [v / 1e6 for v in dcf["fcfs_proj"]]
    pvs    = [v / 1e6 for v in dcf["pv_fcfs"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="FCF Proyectado (M)",  x=years, y=fcfs,
                         marker_color=COLORS["accent"]))
    fig.add_trace(go.Bar(name="VP FCF (M)",          x=years, y=pvs,
                         marker_color=COLORS["accent_light"]))
    fig.add_trace(go.Scatter(name="FCF Proyectado",  x=years, y=fcfs,
                             mode="lines+markers", line=dict(color=COLORS["neutral"], width=2)))

    fig.update_layout(**_layout(
        title=f"{ticker} — Proyeccion FCF ({dcf['explicit_years']} anos)",
        barmode="group",
        yaxis_title=f"Millones {ticker}",
    ))
    return fig


def chart_wacc_waterfall(wacc: dict, ticker: str) -> go.Figure:
    """Waterfall del WACC mostrando componentes."""
    rf       = wacc.get("rf", 0.045)
    beta     = wacc.get("beta", 1.0)
    mp       = wacc.get("mkt_premium", 0.055)
    crp      = wacc.get("crp", 0.0)
    ke       = wacc.get("ke", 0.0)
    kd       = wacc.get("kd", 0.0)
    we       = wacc.get("weight_equity", 0.7)
    wd       = wacc.get("weight_debt", 0.3)
    wacc_val = wacc.get("wacc", 0.0)
    if not wacc_val:
        return go.Figure()

    labels = ["Rf", "β × Prima", "Prima Pais", "Ke", "Kd×Wd×(1-t)", "WACC"]
    values = [rf, beta * mp, crp, -(rf + beta*mp + crp), kd * wd, 0]
    measures = ["relative", "relative", "relative", "total", "relative", "total"]

    fig = go.Figure(go.Waterfall(
        name="WACC",
        orientation="v",
        measure=measures,
        x=labels,
        y=[rf*100, beta*mp*100, crp*100, -(rf+beta*mp+crp)*100, kd*wd*100, wacc_val*100],
        text=[f"{v*100:.2f}%" for v in [rf, beta*mp, crp, ke, kd*wd, wacc_val]],
        textposition="outside",
        decreasing=dict(marker_color=COLORS["negative"]),
        increasing=dict(marker_color=COLORS["positive"]),
        totals=dict(marker_color=COLORS["accent"]),
        connector=dict(line=dict(color=COLORS["border"])),
    ))

    fig.update_layout(**_layout(
        title=f"{ticker} — Composicion WACC ({wacc_val:.2%})",
        yaxis_title="% anual",
    ))
    return fig


def chart_sensitivity_heatmap(sens_df: pd.DataFrame, ticker: str,
                               current_price: float) -> go.Figure:
    """Heatmap de sensibilidad WACC × g terminal con color por upside/downside."""
    if sens_df is None or sens_df.empty:
        return go.Figure()

    z = sens_df.values.astype(float)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=list(sens_df.columns),
        y=list(sens_df.index),
        colorscale=[
            [0.0,  COLORS["negative"]],
            [0.45, "#4D4D4D"],
            [0.55, "#4D4D4D"],
            [1.0,  COLORS["positive"]],
        ],
        zmid=current_price,
        text=z,
        texttemplate="%{text:.0f}",
        textfont=dict(size=10, color="white"),
        showscale=True,
        colorbar=dict(title="Precio USD"),
    ))

    fig.add_shape(
        type="rect", x0=-0.5, x1=len(sens_df.columns)-0.5,
        y0=-0.5, y1=len(sens_df.index)-0.5,
        line=dict(color=COLORS["neutral"], width=1.5),
    )

    fig.update_layout(**_layout(
        title=f"{ticker} — Sensibilidad DCF (precio/accion vs WACC y g)",
        xaxis_title="WACC",
        yaxis_title="g terminal",
        margin=dict(t=70, b=50, l=80, r=20),
    ))
    return fig


def chart_peer_comparison(peer_table: pd.DataFrame,
                           target_vals: dict,
                           ticker: str) -> go.Figure:
    """Grafico de barras horizontales comparando multiplos vs peers."""
    if peer_table is None or peer_table.empty:
        return go.Figure()

    metrics_to_plot = {
        "EV/EBITDA": ("EV/EBITDA", target_vals.get("ev_ebitda")),
        "P/E":       ("P/E",       target_vals.get("trailing_pe")),
        "Mg. EBITDA":("Mg. EBITDA",target_vals.get("ebitda_margin")),
    }

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=list(metrics_to_plot.keys()),
        horizontal_spacing=0.1,
    )

    for col_i, (title, (col_name, tgt_val)) in enumerate(metrics_to_plot.items(), 1):
        if col_name not in peer_table.columns:
            continue
        data     = peer_table.dropna(subset=[col_name])
        names    = list(data["Ticker"])
        values   = list(data[col_name])
        colors   = [COLORS["accent"]] * len(values)

        if tgt_val is not None:
            names.append(ticker)
            values.append(tgt_val)
            colors.append(COLORS["neutral"])

        fig.add_trace(
            go.Bar(
                name=col_name,
                x=values, y=names,
                orientation="h",
                marker_color=colors,
                showlegend=False,
                text=[f"{v:.1f}x" if col_name in ["EV/EBITDA","P/E"] else f"{v:.1%}"
                      for v in values],
                textposition="outside",
            ),
            row=1, col=col_i,
        )

    fig.update_layout(**_layout(
        title=f"{ticker} — Multiplos vs Peers",
        height=max(300, len(peer_table) * 35 + 120),
    ))
    return fig


def chart_efficiency_bars(efficiency: dict, ticker: str) -> go.Figure:
    """Barras de eficiencia relativa por multiplo."""
    if not efficiency:
        return go.Figure()

    from modules.multiples_model import METRIC_CONFIG
    labels = [METRIC_CONFIG[k]["label"] for k in efficiency]
    values = [v * 100 for v in efficiency.values()]
    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in values]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in values],
        textposition="outside",
    ))
    fig.add_hline(y=0, line_color=COLORS["text_secondary"], line_dash="dot")
    fig.update_layout(**_layout(
        title=f"{ticker} — Eficiencia vs Peers (%, +positivo = empresa es mejor)",
        yaxis_title="% diferencia vs mediana peers",
    ))
    return fig


def chart_portfolio_summary(portfolio: dict) -> go.Figure:
    """Scatter: potencial vs riesgo (WACC) para el portafolio completo."""
    tickers, potentials, waccs, prices = [], [], [], []
    for tk, data in portfolio.items():
        dcf  = data.get("dcf", {})
        mult = data.get("multiples", {})
        m    = data.get("metrics", {})
        cp   = m.get("current_price", 0)
        po   = mult.get("combined_price") or dcf.get("price_per_share")
        if cp and po:
            pot = (po / cp - 1) * 100
            tickers.append(tk)
            potentials.append(round(pot, 1))
            waccs.append(round((data.get("wacc_data", {}).get("wacc", 0)) * 100, 2))
            prices.append(cp)

    if not tickers:
        return go.Figure()

    fig = go.Figure()
    for i, (tk, pot, w, cp) in enumerate(zip(tickers, potentials, waccs, prices)):
        color = COLORS["positive"] if pot > 15 else (COLORS["negative"] if pot < -10 else COLORS["neutral"])
        fig.add_trace(go.Scatter(
            x=[w], y=[pot],
            mode="markers+text",
            name=tk,
            text=[tk],
            textposition="top center",
            marker=dict(size=14, color=color, line=dict(width=1.5, color="white")),
            hovertemplate=f"<b>{tk}</b><br>WACC: {w:.1f}%<br>Potencial: {pot:+.1f}%<br>Precio: {cp:.1f}<extra></extra>",
        ))

    fig.add_hline(y=15, line_dash="dash", line_color=COLORS["positive"],
                  annotation_text="Umbral COMPRA +15%")
    fig.add_hline(y=-10, line_dash="dash", line_color=COLORS["negative"],
                  annotation_text="Umbral VENTA -10%")
    fig.update_layout(**_layout(
        title="Portafolio — Potencial de Valoracion vs Costo de Capital",
        xaxis_title="WACC (%)",
        yaxis_title="Potencial (% vs precio actual)",
        showlegend=False,
    ))
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# GRAFICOS MATPLOTLIB (para PDF — fondo blanco, estilo profesional)
# ══════════════════════════════════════════════════════════════════════════════

def _mpl_style():
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor":   "white",
        "axes.edgecolor":   "#CCCCCC",
        "axes.grid":        True,
        "grid.color":       "#EEEEEE",
        "grid.linewidth":   0.6,
        "font.family":      "sans-serif",
        "font.size":        9,
        "text.color":       "#1A1A1A",
        "axes.labelcolor":  "#1A1A1A",
        "xtick.color":      "#555555",
        "ytick.color":      "#555555",
    })


def mpl_price_history(history: pd.DataFrame, ticker: str,
                       po_dcf=None, po_mult=None) -> io.BytesIO:
    _mpl_style()
    fig, ax = plt.subplots(figsize=(7, 3))
    if not history.empty:
        ax.plot(history.index, history["Close"], color="#1e3a5f", linewidth=1.4, label="Precio")
        ax.fill_between(history.index, history["Close"], alpha=0.08, color="#1e3a5f")
        current = float(history["Close"].iloc[-1])
        ax.axhline(current, linestyle=":", color="#888888", linewidth=0.9,
                   label=f"Actual {current:.1f}")
        if po_dcf:
            c = "#00A855" if po_dcf > current else "#D32F2F"
            ax.axhline(po_dcf, linestyle="--", color=c, linewidth=1.2,
                       label=f"PO DCF {po_dcf:.1f}")
        if po_mult:
            c = "#00A855" if po_mult > current else "#D32F2F"
            ax.axhline(po_mult, linestyle="-.", color=c, linewidth=1.2,
                       label=f"PO Mult {po_mult:.1f}")
    ax.set_title(f"{ticker} — Precio Historico (5 anos)", fontsize=10, fontweight="bold", pad=8)
    ax.set_ylabel("Precio")
    ax.legend(fontsize=7, loc="upper left")
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def mpl_fcf_projection(dcf: dict, ticker: str) -> io.BytesIO:
    _mpl_style()
    fig, ax = plt.subplots(figsize=(7, 3))
    if dcf and not dcf.get("error"):
        years = [f"A{i+1}" for i in range(dcf["explicit_years"])]
        fcfs  = [v / 1e6 for v in dcf["fcfs_proj"]]
        pvs   = [v / 1e6 for v in dcf["pv_fcfs"]]
        x     = np.arange(len(years))
        w     = 0.38
        ax.bar(x - w/2, fcfs, w, label="FCF Proy (M)", color="#1e3a5f", alpha=0.85)
        ax.bar(x + w/2, pvs,  w, label="VP FCF (M)",   color="#4C8BF5", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(years)
        ax.set_ylabel("Millones")
        ax.legend(fontsize=7)
    ax.set_title(f"{ticker} — Proyeccion FCF", fontsize=10, fontweight="bold", pad=8)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def mpl_sensitivity(sens_df: pd.DataFrame, ticker: str, current_price: float) -> io.BytesIO:
    _mpl_style()
    if sens_df is None or sens_df.empty:
        buf = io.BytesIO()
        return buf

    fig, ax = plt.subplots(figsize=(7, 3.5))
    data    = sens_df.values.astype(float)
    vmin    = min(data[~np.isnan(data)]) if not np.all(np.isnan(data)) else 0
    vmax    = max(data[~np.isnan(data)]) if not np.all(np.isnan(data)) else 1
    im      = ax.imshow(data, cmap="RdYlGn", aspect="auto",
                        vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(sens_df.columns)))
    ax.set_xticklabels(sens_df.columns, rotation=30, ha="right", fontsize=7)
    ax.set_yticks(range(len(sens_df.index)))
    ax.set_yticklabels(sens_df.index, fontsize=7)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.5,
                        color="white" if abs(v - current_price) > (vmax-vmin)*0.3 else "black")
    plt.colorbar(im, ax=ax, label="Precio accion")
    ax.set_title(f"{ticker} — Sensibilidad DCF", fontsize=10, fontweight="bold", pad=8)
    ax.set_xlabel("WACC")
    ax.set_ylabel("g terminal")
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def mpl_efficiency(efficiency: dict, ticker: str) -> io.BytesIO:
    _mpl_style()
    from modules.multiples_model import METRIC_CONFIG
    fig, ax = plt.subplots(figsize=(6, 2.8))
    if efficiency:
        labels = [METRIC_CONFIG[k]["label"] for k in efficiency]
        values = [v * 100 for v in efficiency.values()]
        colors = ["#00A855" if v >= 0 else "#D32F2F" for v in values]
        ax.barh(labels, values, color=colors, edgecolor="white", linewidth=0.4)
        ax.axvline(0, color="#555555", linewidth=0.8)
        for i, v in enumerate(values):
            ax.text(v + (0.5 if v >= 0 else -0.5), i, f"{v:+.1f}%",
                    va="center", ha="left" if v >= 0 else "right", fontsize=7.5)
    ax.set_title(f"{ticker} — Eficiencia vs Peers", fontsize=10, fontweight="bold", pad=8)
    ax.set_xlabel("% diferencia vs mediana")
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def mpl_portfolio_bar(portfolio: dict) -> io.BytesIO:
    """Barra horizontal del potencial de valoracion de todo el portafolio."""
    _mpl_style()
    tickers, potentials = [], []
    for tk, data in portfolio.items():
        dcf  = data.get("dcf", {})
        mult = data.get("multiples", {})
        m    = data.get("metrics", {})
        cp   = m.get("current_price", 0)
        po   = mult.get("combined_price") or (dcf.get("price_per_share") if dcf else None)
        if cp and po:
            tickers.append(tk)
            potentials.append((po / cp - 1) * 100)

    fig, ax = plt.subplots(figsize=(7, max(2.5, len(tickers) * 0.55)))
    if tickers:
        colors = ["#00A855" if v > 15 else ("#D32F2F" if v < -10 else "#F9A825")
                  for v in potentials]
        ax.barh(tickers, potentials, color=colors, edgecolor="white", linewidth=0.4)
        ax.axvline(0,   color="#555555", linewidth=0.8)
        ax.axvline(15,  color="#00A855", linewidth=0.7, linestyle="--", label="Umbral COMPRA")
        ax.axvline(-10, color="#D32F2F", linewidth=0.7, linestyle="--", label="Umbral VENTA")
        for i, v in enumerate(potentials):
            ax.text(v + 0.5, i, f"{v:+.1f}%", va="center", fontsize=7.5)
        ax.legend(fontsize=7, loc="lower right")
    ax.set_title("Portafolio — Potencial de Valoracion", fontsize=10, fontweight="bold", pad=8)
    ax.set_xlabel("Potencial (%)")
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf
