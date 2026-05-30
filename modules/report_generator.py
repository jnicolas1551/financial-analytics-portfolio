"""
Generacion de reportes: PDF investing memo (fpdf2 + matplotlib) y Excel (xlsxwriter).
"""
import io
import math
import tempfile
import os
import numpy as np
import pandas as pd
from datetime import datetime
from fpdf import FPDF

from components.charts import (
    mpl_price_history, mpl_fcf_projection,
    mpl_sensitivity, mpl_efficiency, mpl_portfolio_bar,
)
from components.styles import COLORS


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

# Mapa de caracteres Unicode a equivalentes Latin-1 / ASCII para fpdf2
_UNICODE_MAP = {
    '—': '-',    # em dash —
    '–': '-',    # en dash –
    '‒': '-',    # figure dash
    '’': "'",    # right single quotation '
    '‘': "'",    # left single quotation '
    '“': '"',    # left double quotation "
    '”': '"',    # right double quotation "
    '…': '...',  # ellipsis …
    'é': 'e',    # é
    'á': 'a',    # a
    'í': 'i',    # i
    'ó': 'o',    # o
    'ú': 'u',    # u
    'ñ': 'n',    # n~
    'ü': 'u',    # u umlaut
    'à': 'a',    'è': 'e',
    'ì': 'i',    'ò': 'o',  'ù': 'u',
    'â': 'a',    'ê': 'e',  'î': 'i',
    'ô': 'o',    'û': 'u',
    'ä': 'a',    'ë': 'e',  'ï': 'i',
    'ö': 'o',    'ÿ': 'y',
    'É': 'E',    'Á': 'A',  'Í': 'I',
    'Ó': 'O',    'Ú': 'U',  'Ñ': 'N',
    '®': '(R)',  '©': '(C)', '™': '(TM)',
    '€': 'EUR',  '£': 'GBP', '¥': 'JPY',
}

def _s(text) -> str:
    """Sanitiza texto a Latin-1 para fuentes built-in de fpdf2.
    Reemplaza caracteres Unicode problemáticos con equivalentes ASCII."""
    if text is None:
        return ""
    text = str(text)
    for char, repl in _UNICODE_MAP.items():
        text = text.replace(char, repl)
    # Eliminar cualquier caracter restante fuera de Latin-1
    return text.encode('latin-1', errors='ignore').decode('latin-1')


def _fmt(v, mode="", default="N/A") -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return default
    if mode == "usd":   return f"USD {v:,.2f}"
    if mode == "pct":   return f"{v:.2%}"
    if mode == "mult":  return f"{v:.1f}x"
    if mode == "bn":    return f"USD {v/1e9:.2f}B" if abs(v) >= 1e9 else f"USD {v/1e6:.0f}M"
    if mode == "int":   return f"{v:,.0f}"
    return f"{v:.2f}"


def _signal(current: float, target: float | None) -> tuple[str, float]:
    if not target or not current or current == 0:
        return "SIN DATOS", 0.0
    pot = target / current - 1
    if pot > 0.15:   return "COMPRA",  pot
    if pot < -0.10:  return "VENTA",   pot
    return "NEUTRAL", pot


# ══════════════════════════════════════════════════════════════════════════════
# PDF INVESTING MEMO
# ══════════════════════════════════════════════════════════════════════════════

class _Memo(FPDF):
    """FPDF2 subclass con header/footer corporativo.
    Sobreescribe cell y multi_cell para sanitizar strings a Latin-1 automaticamente."""

    def __init__(self, portfolio_name: str = "Portafolio"):
        super().__init__()
        self.portfolio_name = portfolio_name
        self.set_margins(18, 28, 18)
        self.set_auto_page_break(auto=True, margin=22)

    def cell(self, w=0, h=0, txt="", border=0, ln=False, align="", fill=False, link=""):
        # Sanitiza automaticamente todos los strings a Latin-1 (fpdf2 built-in fonts)
        super().cell(w, h, _s(txt), border=border, ln=ln, align=align, fill=fill, link=link)

    def header(self):
        r, g, b = COLORS["pdf_primary"]
        self.set_fill_color(r, g, b)
        self.rect(0, 0, 210, 22, "F")
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 6)
        self.cell(0, 10, _s(f"ANALISIS INSTITUCIONAL - {self.portfolio_name.upper()}"), align="L")
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-18)
        self.set_draw_color(*COLORS["pdf_primary"])
        self.set_line_width(0.4)
        self.line(18, self.get_y(), 192, self.get_y())
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(120, 120, 120)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cell(0, 8, _s(
                  f"Generado: {fecha}  |  Pagina {self.page_no()}  |  "
                  "Modelo cuantitativo con datos Yahoo Finance. No constituye asesoria de inversion."),
                  align="C")
        self.set_text_color(0, 0, 0)


def _section(pdf: _Memo, title: str):
    pdf.ln(5)
    r, g, b = COLORS["pdf_primary"]
    pdf.set_fill_color(r, g, b)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, _s(f"  {title}"), fill=True, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)


def _kv(pdf: _Memo, label: str, value: str, alt: bool = False, highlight: str | None = None):
    if alt:
        pdf.set_fill_color(*COLORS["pdf_row_alt"])
    else:
        pdf.set_fill_color(255, 255, 255)

    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(72, 6.5, _s(f"  {label}"), border="LTB", fill=True)

    pdf.set_font("Helvetica", "", 8)
    if highlight == "pos":
        pdf.set_text_color(*COLORS["pdf_positive"])
    elif highlight == "neg":
        pdf.set_text_color(*COLORS["pdf_negative"])
    pdf.cell(100, 6.5, _s(f"  {value}"), border="RTB", fill=True, ln=True)
    pdf.set_text_color(0, 0, 0)


def _embed_image(pdf: _Memo, buf: io.BytesIO, w: float = 174, h: float = 0):
    """Guarda buffer en temp file y lo inserta en el PDF."""
    if buf is None:
        return
    buf.seek(0)
    suffix = ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(buf.read())
        tmp_path = tmp.name
    try:
        pdf.image(tmp_path, x=18, w=w, h=h if h else 0)
    finally:
        os.unlink(tmp_path)


def _peer_table_pdf(pdf: _Memo, peer_df: pd.DataFrame):
    if peer_df is None or peer_df.empty:
        return
    cols    = ["Ticker", "EV/EBITDA", "P/E", "Mg. EBITDA", "ROE", "Div. Yield"]
    widths  = [22, 25, 20, 28, 22, 25]

    r, g, b = COLORS["pdf_primary"]
    pdf.set_fill_color(r, g, b)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(255, 255, 255)
    for col, w in zip(cols, widths):
        pdf.cell(w, 7, col, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    for i, row in peer_df.iterrows():
        alt = (int(str(i)) % 2 == 0) if str(i).isdigit() else (i % 2 == 0)
        pdf.set_fill_color(*(COLORS["pdf_row_alt"] if alt else (255, 255, 255)))
        pdf.set_font("Helvetica", "", 7.5)

        def _c(key, mode=""):
            v = row.get(key)
            return _fmt(v, mode)

        pdf.cell(22, 6.5, str(row.get("Ticker", ""))[:8],       border=1, fill=True, align="C")
        pdf.cell(25, 6.5, _c("EV/EBITDA", "mult"),              border=1, fill=True, align="C")
        pdf.cell(20, 6.5, _c("P/E",       "mult"),              border=1, fill=True, align="C")
        pdf.cell(28, 6.5, _c("Mg. EBITDA","pct"),               border=1, fill=True, align="C")
        pdf.cell(22, 6.5, _c("ROE",       "pct"),               border=1, fill=True, align="C")
        pdf.cell(25, 6.5, _c("Div. Yield","pct"),               border=1, fill=True, align="C")
        pdf.ln()


def generate_pdf(portfolio: dict, portfolio_name: str = "Portafolio") -> bytes:
    """
    Genera un investing memo PDF con todas las empresas del portafolio.
    """
    pdf = _Memo(portfolio_name)

    # ── Portada ────────────────────────────────────────────────────────────
    pdf.add_page()
    r, g, b = COLORS["pdf_primary"]
    pdf.set_fill_color(r, g, b)
    pdf.rect(0, 55, 210, 90, "F")
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(18, 70)
    pdf.cell(0, 14, "INVESTING MEMO", ln=True, align="L")
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_x(18)
    pdf.cell(0, 10, f"Analisis de Portafolio — {portfolio_name}", ln=True, align="L")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_x(18)
    pdf.cell(0, 8, f"Generado el {datetime.now().strftime('%d de %B de %Y')}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(18)
    tickers_str = "  |  ".join(portfolio.keys())
    pdf.cell(0, 8, f"Activos: {tickers_str}", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(18, 155)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Resumen Ejecutivo del Portafolio", ln=True)
    pdf.ln(2)

    # Tabla resumen portafolio
    r, g, b = COLORS["pdf_primary"]
    pdf.set_fill_color(r, g, b)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(255, 255, 255)
    hdrs = ["Ticker", "Empresa", "Precio", "PO Mult.", "PO DCF", "Potencial", "Senal"]
    wths = [18,  46, 18, 20, 20, 22, 22]
    for h, w in zip(hdrs, wths):
        pdf.cell(w, 7, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    for i, (tk, data) in enumerate(portfolio.items()):
        m    = data.get("metrics", {})
        dcf  = data.get("dcf", {})
        mult = data.get("multiples", {})
        cp   = m.get("current_price", 0) or 0
        po_m = mult.get("combined_price")
        po_d = dcf.get("price_per_share") if dcf and not dcf.get("error") else None
        sig, pot = _signal(cp, po_m or po_d)

        pdf.set_fill_color(*(COLORS["pdf_row_alt"] if i % 2 == 0 else (255, 255, 255)))
        pdf.set_font("Helvetica", "", 7.5)

        if sig == "COMPRA":
            sig_color = COLORS["pdf_positive"]
        elif sig == "VENTA":
            sig_color = COLORS["pdf_negative"]
        else:
            sig_color = (180, 130, 0)

        pdf.cell(18, 6.5, tk[:8],                       border=1, fill=True, align="C")
        pdf.cell(46, 6.5, (m.get("name","") or "")[:28],border=1, fill=True)
        pdf.cell(18, 6.5, _fmt(cp, "usd"),              border=1, fill=True, align="C")
        pdf.cell(20, 6.5, _fmt(po_m, "usd"),            border=1, fill=True, align="C")
        pdf.cell(20, 6.5, _fmt(po_d, "usd"),            border=1, fill=True, align="C")
        pdf.cell(22, 6.5, _fmt(pot, "pct"),             border=1, fill=True, align="C")
        pdf.set_text_color(*sig_color)
        pdf.cell(22, 6.5, sig,                           border=1, fill=True, align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.ln()

    # Grafica portafolio
    pdf.ln(4)
    try:
        buf = mpl_portfolio_bar(portfolio)
        _embed_image(pdf, buf, w=170, h=70)
    except Exception:
        pass

    # ── Seccion por empresa ────────────────────────────────────────────────
    for ticker, data in portfolio.items():
        pdf.add_page()
        m       = data.get("metrics", {})
        dcf     = data.get("dcf", {})
        mult    = data.get("multiples", {})
        wacc_d  = data.get("wacc_data", {})
        history = data.get("history", pd.DataFrame())
        sens    = data.get("sensitivity")
        country = data.get("country", {})
        cp      = m.get("current_price", 0) or 0
        po_m    = mult.get("combined_price")
        po_d    = dcf.get("price_per_share") if dcf and not dcf.get("error") else None
        sig, pot = _signal(cp, po_m or po_d)
        ccy     = m.get("currency", "USD")
        fx      = m.get("fx_to_usd", 1.0) or 1.0

        # Titulo empresa
        r, g, b = COLORS["pdf_primary"]
        pdf.set_fill_color(r, g, b)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 11, f"  {ticker} — {(m.get('name','') or '')[:55]}", fill=True, ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 6, f"  {m.get('sector','')} | {m.get('industry','')} | "
                       f"{m.get('country','')} | Moneda: {ccy}", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        # Signal badge
        sc = COLORS["pdf_positive"] if sig=="COMPRA" else (COLORS["pdf_negative"] if sig=="VENTA" else (200,150,0))
        pdf.set_fill_color(*sc)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(40, 8, f"  {sig}  {_fmt(pot,'pct')}", fill=True, ln=False)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(0, 8,
                 f"   Precio actual: {_fmt(cp,'usd')} {ccy}  |  "
                 f"PO Multiplos: {_fmt(po_m,'usd')} {ccy}  |  "
                 f"PO DCF: {_fmt(po_d,'usd')} {ccy}", ln=True)

        # ── Grafica precio historico ──
        try:
            buf_h = mpl_price_history(history, ticker, po_d, po_m)
            _embed_image(pdf, buf_h, w=174, h=62)
        except Exception:
            pass

        # ── Metricas clave (2 columnas) ──
        _section(pdf, "1. METRICAS CLAVE")
        col_pairs = [
            ("Market Cap",      _fmt(m.get("market_cap"),      "bn")),
            ("Enterprise Value",_fmt(m.get("enterprise_value"),"bn")),
            ("EBITDA",          _fmt(m.get("ebitda"),          "bn")),
            ("Ingresos TTM",    _fmt(m.get("total_revenue"),   "bn")),
            ("P/E trailing",    _fmt(m.get("trailing_pe"),     "mult")),
            ("EV/EBITDA",       _fmt(m.get("ev_ebitda"),       "mult")),
            ("Margen EBITDA",   _fmt(m.get("ebitda_margin"),   "pct")),
            ("Margen Operativo",_fmt(m.get("operating_margin"),"pct")),
            ("ROE",             _fmt(m.get("return_on_equity"),"pct")),
            ("ROA",             _fmt(m.get("return_on_assets"),"pct")),
            ("Deuda Total",     _fmt(m.get("total_debt"),      "bn")),
            ("Caja",            _fmt(m.get("total_cash"),      "bn")),
            ("Beta",            _fmt(m.get("beta"))),
            ("Div. Yield",      _fmt(m.get("dividend_yield"),  "pct")),
        ]
        mid = len(col_pairs) // 2
        left, right = col_pairs[:mid], col_pairs[mid:]
        for i, ((lbl1, val1), (lbl2, val2)) in enumerate(zip(left, right)):
            alt = (i % 2 == 0)
            bg = COLORS["pdf_row_alt"] if alt else (255, 255, 255)
            pdf.set_fill_color(*bg)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.cell(37, 6.2, f"  {lbl1}", border="LTB", fill=True)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.cell(48, 6.2, f"  {val1}", border="RTB", fill=True)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.cell(37, 6.2, f"  {lbl2}", border="LTB", fill=True)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.cell(48, 6.2, f"  {val2}", border="RTB", fill=True, ln=True)

        if ccy != "USD":
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(100, 100, 100)
            price_usd = cp * fx
            pdf.cell(0, 5, f"  Equivalente USD: precio actual = USD {price_usd:.2f}  (TRM: {fx:.4f})", ln=True)
            pdf.set_text_color(0, 0, 0)

        # ── DCF ──────────────────────────────────────────────────────────────
        _section(pdf, "2. VALORACION DCF — FLUJOS DE CAJA DESCONTADOS")

        if dcf and not dcf.get("error"):
            # WACC components
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 6, "  Componentes WACC", ln=True)
            wacc_items = [
                ("WACC",              _fmt(wacc_d.get("wacc"),          "pct")),
                ("Ke (costo equity)", _fmt(wacc_d.get("ke"),            "pct")),
                ("Kd after-tax",      _fmt(wacc_d.get("kd"),            "pct")),
                ("Beta",              _fmt(wacc_d.get("beta"))),
                ("Rf",                _fmt(wacc_d.get("rf"),            "pct")),
                ("Prima mercado",     _fmt(wacc_d.get("mkt_premium"),   "pct")),
                ("Prima pais (CRP)",  _fmt(wacc_d.get("crp"),           "pct")),
                ("Tasa impuestos",    _fmt(wacc_d.get("tax_rate"),      "pct")),
                ("Peso equity",       _fmt(wacc_d.get("weight_equity"), "pct")),
                ("Peso deuda",        _fmt(wacc_d.get("weight_debt"),   "pct")),
            ]
            for i, (l, v) in enumerate(wacc_items):
                _kv(pdf, l, v, alt=(i % 2 == 0))

            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 6, "  Resultados DCF", ln=True)
            dcf_items = [
                ("FCF base",              _fmt(dcf.get("base_fcf"),        "bn")),
                ("Tasa crec. explicito",  _fmt(dcf.get("growth_explicit"), "pct")),
                ("Tasa crec. terminal g", _fmt(dcf.get("terminal_growth"), "pct")),
                ("Anios proyeccion",      str(dcf.get("explicit_years",""))),
                ("VP periodo explicito",  _fmt(dcf.get("pv_explicit"),     "bn")),
                ("Valor terminal",        _fmt(dcf.get("terminal_value"),  "bn")),
                ("VP valor terminal",     _fmt(dcf.get("pv_terminal"),     "bn")),
                ("% valor terminal",      _fmt(dcf.get("terminal_pct"),    "pct")),
                ("EV (DCF)",              _fmt(dcf.get("ev_dcf"),          "bn")),
                ("Equity value",          _fmt(dcf.get("equity_dcf"),      "bn")),
                ("Precio por accion",     f"{_fmt(dcf.get('price_per_share'),'usd')} {ccy}"),
            ]
            for i, (l, v) in enumerate(dcf_items):
                hl = "pos" if "precio" in l.lower() else None
                _kv(pdf, l, v, alt=(i % 2 == 0), highlight=hl)

            # Grafica FCF
            try:
                buf_f = mpl_fcf_projection(dcf, ticker)
                _embed_image(pdf, buf_f, w=160, h=58)
            except Exception:
                pass

            # Sensibilidad (nueva pagina si necesario)
            if sens is not None and not sens.empty:
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 8)
                pdf.cell(0, 6, "  Tabla de Sensibilidad (precio accion)", ln=True)
                try:
                    buf_s = mpl_sensitivity(sens, ticker, cp)
                    _embed_image(pdf, buf_s, w=170, h=68)
                except Exception:
                    pass
        else:
            pdf.set_font("Helvetica", "I", 8)
            msg = dcf.get("error", "DCF no disponible.") if dcf else "Sin datos."
            pdf.cell(0, 7, f"  {msg}", ln=True)

        # ── Multiplos ─────────────────────────────────────────────────────────
        pdf.add_page()
        _section(pdf, "3. ANALISIS DE COMPARABLES — MULTIPLOS DE MERCADO")

        if mult and not mult.get("error"):
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 6, "  Precios objetivo por multiplo directo", ln=True)
            dp = mult.get("direct_prices", {})
            mult_items = [
                ("PO via EV/EBITDA",   _fmt(dp.get("ev_ebitda"),  "usd") + f" {ccy}" if dp.get("ev_ebitda") else "N/A"),
                ("PO via P/E",         _fmt(dp.get("pe"),         "usd") + f" {ccy}" if dp.get("pe")        else "N/A"),
                ("PO via EV/Revenue",  _fmt(dp.get("ev_revenue"), "usd") + f" {ccy}" if dp.get("ev_revenue") else "N/A"),
                ("PO combinado multiplos", f"{_fmt(mult.get('combined_price'),'usd')} {ccy}"),
                ("Eficiencia ponderada",   _fmt(mult.get("weighted_eff"), "pct")),
            ]
            for i, (l, v) in enumerate(mult_items):
                hl = "pos" if "combinado" in l.lower() else None
                _kv(pdf, l, v, alt=(i % 2 == 0), highlight=hl)

            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 6, "  Tabla de peers comparables", ln=True)
            peer_df = mult.get("peer_table", pd.DataFrame())
            _peer_table_pdf(pdf, peer_df)

            # Grafica eficiencia
            pdf.ln(3)
            try:
                buf_e = mpl_efficiency(mult.get("efficiency", {}), ticker)
                _embed_image(pdf, buf_e, w=155, h=60)
            except Exception:
                pass
        else:
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 7, "  Analisis de multiplos no disponible.", ln=True)

        # ── Recomendacion final empresa ──────────────────────────────────────
        _section(pdf, "4. RECOMENDACION FINAL")
        sc = COLORS["pdf_positive"] if sig=="COMPRA" else (COLORS["pdf_negative"] if sig=="VENTA" else (200,150,0))
        pdf.set_fill_color(*sc)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, f"   SENAL: {sig}  |  Potencial: {_fmt(pot,'pct')}", fill=True, ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        final_items = [
            ("Precio actual de mercado", f"{_fmt(cp,'usd')} {ccy}"),
            ("Precio objetivo DCF",      f"{_fmt(po_d,'usd')} {ccy}"),
            ("Precio objetivo Multiplos",f"{_fmt(po_m,'usd')} {ccy}"),
            ("Potencial de valoracion",  _fmt(pot,"pct")),
        ]
        for i, (l, v) in enumerate(final_items):
            _kv(pdf, l, v, alt=(i % 2 == 0))

    # ── Disclaimer ────────────────────────────────────────────────────────
    pdf.add_page()
    _section(pdf, "DISCLAIMER Y METODOLOGIA")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(80, 80, 80)
    disclaimer = _s(
        "Este documento ha sido generado de forma automatica mediante modelos cuantitativos "
        "de valoracion (DCF y analisis de comparables) con datos obtenidos de Yahoo Finance "
        "(yfinance). Los resultados son de caracter informativo y educativo UNICAMENTE.\n\n"
        "No constituye asesoria financiera, recomendacion de inversion ni oferta de valores. "
        "Los modelos de valoracion implican supuestos sobre tasas de descuento, tasas de "
        "crecimiento y datos de mercado que pueden no reflejar condiciones futuras. "
        "Consulte siempre con un asesor financiero certificado antes de tomar decisiones "
        "de inversion.\n\n"
        "Metodologia DCF: FCF = UODI + D&A - delta KTNO - CAPEX. "
        "WACC con pesos por valor de mercado. Ke via CAPM + prima de riesgo pais (Damodaran 2024). "
        "Kd implicita sobre deuda financiera.\n\n"
        "Metodologia Multiplos: precio implicito por EV/EBITDA, P/E y EV/Revenue aplicando "
        "la mediana del grupo de peers del mismo sector. "
        "Precio combinado ponderado por los pesos definidos por el usuario."
    )
    pdf.multi_cell(0, 5, disclaimer)

    return bytes(pdf.output())


# ══════════════════════════════════════════════════════════════════════════════
# EXCEL
# ══════════════════════════════════════════════════════════════════════════════

def generate_excel(portfolio: dict) -> bytes:
    buf = io.BytesIO()

    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        wb = writer.book

        # Formatos
        fmt_title  = wb.add_format({"bold":True, "font_size":13, "font_color":"#FFFFFF",
                                    "bg_color":"#1e3a5f", "border":0})
        fmt_hdr    = wb.add_format({"bold":True, "font_color":"#FFFFFF",
                                    "bg_color":"#1e3a5f", "border":1, "align":"center"})
        fmt_label  = wb.add_format({"bold":True, "bg_color":"#F0F4FA", "border":1})
        fmt_val    = wb.add_format({"border":1, "num_format":"#,##0.00"})
        fmt_pct    = wb.add_format({"border":1, "num_format":"0.00%"})
        fmt_usd    = wb.add_format({"border":1, "num_format":"$#,##0.00"})
        fmt_bn     = wb.add_format({"border":1, "num_format":"$#,##0,,\"B\""})
        fmt_pos    = wb.add_format({"border":1, "font_color":"#007A33", "bold":True, "num_format":"0.00%"})
        fmt_neg    = wb.add_format({"border":1, "font_color":"#CC0000", "bold":True, "num_format":"0.00%"})
        fmt_sub    = wb.add_format({"bold":True, "font_size":10, "font_color":"#1e3a5f"})
        fmt_it     = wb.add_format({"italic":True, "font_color":"#888888", "font_size":8})

        def write_kv(ws, row, label, value, fmt_v=None, col_off=0):
            ws.write(row, col_off,     label, fmt_label)
            ws.write(row, col_off + 1, value, fmt_v or fmt_val)
            return row + 1

        # ── Hoja 1: Resumen portafolio ──────────────────────────────────
        ws0 = wb.add_worksheet("Resumen Portafolio")
        ws0.set_column("A:A", 28)
        ws0.set_column("B:I", 16)
        ws0.merge_range("A1:I1", "ANALISIS INSTITUCIONAL — RESUMEN DE PORTAFOLIO", fmt_title)
        ws0.write(1, 0, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fmt_it)
        row = 3
        hdrs0 = ["Ticker","Empresa","Precio","PO Mult.","PO DCF","Potencial","WACC","Senal"]
        for c, h in enumerate(hdrs0):
            ws0.write(row, c, h, fmt_hdr)
        row += 1
        for tk, data in portfolio.items():
            m    = data.get("metrics", {})
            dcf  = data.get("dcf", {})
            mult = data.get("multiples", {})
            wac  = data.get("wacc_data", {})
            cp   = m.get("current_price", 0) or 0
            po_m = mult.get("combined_price")
            po_d = dcf.get("price_per_share") if dcf and not dcf.get("error") else None
            sig, pot = _signal(cp, po_m or po_d)
            pf = fmt_pos if pot > 0 else fmt_neg
            ws0.write(row, 0, tk)
            ws0.write(row, 1, (m.get("name","") or "")[:40])
            ws0.write(row, 2, cp,  fmt_usd)
            ws0.write(row, 3, po_m if po_m else "", fmt_usd)
            ws0.write(row, 4, po_d if po_d else "", fmt_usd)
            ws0.write(row, 5, pot, pf)
            ws0.write(row, 6, wac.get("wacc", ""), fmt_pct)
            ws0.write(row, 7, sig)
            row += 1

        # ── Hoja por empresa ──────────────────────────────────────────
        for ticker, data in portfolio.items():
            m      = data.get("metrics", {})
            dcf    = data.get("dcf", {})
            mult   = data.get("multiples", {})
            wacc_d = data.get("wacc_data", {})
            sens   = data.get("sensitivity")

            sname  = ticker[:28]
            ws     = wb.add_worksheet(sname)
            ws.set_column("A:A", 30)
            ws.set_column("B:B", 20)
            ws.set_column("C:C", 30)
            ws.set_column("D:D", 20)

            ws.merge_range(f"A1:D1",
                           f"{ticker} — {(m.get('name','') or '')[:50]}", fmt_title)
            ws.write(1, 0, f"Sector: {m.get('sector','')} | Pais: {m.get('country','')} | Moneda: {m.get('currency','')}", fmt_it)

            r = 3
            ws.write(r, 0, "METRICAS CLAVE", fmt_sub)
            r += 1
            kv_left = [
                ("Precio actual",       m.get("current_price"), fmt_usd),
                ("Market Cap",          m.get("market_cap"),    fmt_bn),
                ("Enterprise Value",    m.get("enterprise_value"), fmt_bn),
                ("EBITDA",              m.get("ebitda"),        fmt_bn),
                ("Ingresos TTM",        m.get("total_revenue"), fmt_bn),
                ("P/E trailing",        m.get("trailing_pe"),   fmt_val),
                ("EV/EBITDA",           m.get("ev_ebitda"),     fmt_val),
            ]
            kv_right = [
                ("Margen EBITDA",       m.get("ebitda_margin"),      fmt_pct),
                ("ROE",                 m.get("return_on_equity"),   fmt_pct),
                ("Deuda total",         m.get("total_debt"),         fmt_bn),
                ("Caja",                m.get("total_cash"),         fmt_bn),
                ("Beta",                m.get("beta"),               fmt_val),
                ("Dividend Yield",      m.get("dividend_yield"),     fmt_pct),
                ("FCF (libre)",         m.get("free_cashflow"),      fmt_bn),
            ]
            for (ll, lv, lf), (rl, rv, rf_) in zip(kv_left, kv_right):
                ws.write(r, 0, ll, fmt_label)
                ws.write(r, 1, lv if lv is not None else "", lf)
                ws.write(r, 2, rl, fmt_label)
                ws.write(r, 3, rv if rv is not None else "", rf_)
                r += 1

            r += 1
            ws.write(r, 0, "WACC — COMPONENTES", fmt_sub)
            r += 1
            wacc_rows = [
                ("WACC",              wacc_d.get("wacc"),          fmt_pct),
                ("Ke (costo equity)", wacc_d.get("ke"),            fmt_pct),
                ("Kd after-tax",      wacc_d.get("kd"),            fmt_pct),
                ("Beta",              wacc_d.get("beta"),          fmt_val),
                ("Rf",                wacc_d.get("rf"),            fmt_pct),
                ("Prima mercado",     wacc_d.get("mkt_premium"),   fmt_pct),
                ("Prima pais (CRP)",  wacc_d.get("crp"),           fmt_pct),
                ("Tasa impuestos",    wacc_d.get("tax_rate"),      fmt_pct),
                ("Peso equity",       wacc_d.get("weight_equity"), fmt_pct),
                ("Peso deuda",        wacc_d.get("weight_debt"),   fmt_pct),
            ]
            for ll, lv, lf in wacc_rows:
                ws.write(r, 0, ll, fmt_label)
                ws.write(r, 1, lv if lv is not None else "", lf)
                r += 1

            r += 1
            ws.write(r, 0, "DCF — RESULTADOS", fmt_sub)
            r += 1
            if dcf and not dcf.get("error"):
                dcf_rows = [
                    ("FCF base",             dcf.get("base_fcf"),        fmt_bn),
                    ("Tasa crec. explicito", dcf.get("growth_explicit"), fmt_pct),
                    ("Tasa crec. terminal",  dcf.get("terminal_growth"), fmt_pct),
                    ("VP periodo explicito", dcf.get("pv_explicit"),     fmt_bn),
                    ("Valor terminal",       dcf.get("terminal_value"),  fmt_bn),
                    ("VP valor terminal",    dcf.get("pv_terminal"),     fmt_bn),
                    ("% valor terminal",     dcf.get("terminal_pct"),    fmt_pct),
                    ("EV (DCF)",             dcf.get("ev_dcf"),          fmt_bn),
                    ("Equity value",         dcf.get("equity_dcf"),      fmt_bn),
                    ("Precio por accion",    dcf.get("price_per_share"), fmt_usd),
                ]
                for ll, lv, lf in dcf_rows:
                    ws.write(r, 0, ll, fmt_label)
                    ws.write(r, 1, lv if lv is not None else "", lf)
                    r += 1

                r += 1
                ws.write(r, 0, "Proyeccion FCF", fmt_sub)
                r += 1
                yrs = [f"Ano {i+1}" for i in range(dcf.get("explicit_years", 5))]
                for c, y in enumerate(yrs):
                    ws.write(r, c+1, y, fmt_hdr)
                ws.write(r, 0, "FCF Proy (USD)", fmt_label)
                r += 1
                for c, v in enumerate(dcf.get("fcfs_proj", [])):
                    ws.write(r-1, c+1, v, fmt_bn)
                ws.write(r, 0, "VP FCF (USD)", fmt_label)
                for c, v in enumerate(dcf.get("pv_fcfs", [])):
                    ws.write(r, c+1, v, fmt_bn)
                r += 2

            r += 1
            ws.write(r, 0, "MULTIPLOS — RESULTADOS", fmt_sub)
            r += 1
            if mult and not mult.get("error"):
                dp = mult.get("direct_prices", {})
                mult_rows = [
                    ("PO via EV/EBITDA",    dp.get("ev_ebitda"),  fmt_usd),
                    ("PO via P/E",          dp.get("pe"),         fmt_usd),
                    ("PO via EV/Revenue",   dp.get("ev_revenue"), fmt_usd),
                    ("PO combinado",        mult.get("combined_price"), fmt_usd),
                    ("Eficiencia ponderada",mult.get("weighted_eff"),   fmt_pct),
                ]
                for ll, lv, lf in mult_rows:
                    ws.write(r, 0, ll, fmt_label)
                    ws.write(r, 1, lv if lv is not None else "", lf)
                    r += 1

                peer_df = mult.get("peer_table", pd.DataFrame())
                if not peer_df.empty:
                    r += 1
                    ws.write(r, 0, "Tabla de Peers", fmt_sub)
                    r += 1
                    for c2, col in enumerate(peer_df.columns):
                        ws.write(r, c2, col, fmt_hdr)
                    r += 1
                    for _, row_data in peer_df.iterrows():
                        for c2, v in enumerate(row_data):
                            ws.write(r, c2, v if v is not None else "")
                        r += 1

            # Sensibilidad
            if sens is not None and not sens.empty:
                r += 2
                ws.write(r, 0, "Sensibilidad DCF (precio/accion)", fmt_sub)
                r += 1
                ws.write(r, 0, "", fmt_label)
                for c2, col in enumerate(sens.columns):
                    ws.write(r, c2+1, col, fmt_hdr)
                r += 1
                for idx, row_data in sens.iterrows():
                    ws.write(r, 0, str(idx), fmt_label)
                    for c2, v in enumerate(row_data):
                        if v is not None and not (isinstance(v, float) and np.isnan(v)):
                            f = fmt_pos if v > (m.get("current_price",0) or 0) else fmt_neg
                            ws.write(r, c2+1, v, f)
                    r += 1

    buf.seek(0)
    return buf.getvalue()
