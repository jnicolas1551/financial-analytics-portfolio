# 📊 Analisis Fundamental Institucional

Dashboard interactivo de valoracion de empresas por **DCF** (Flujos de Caja Descontados) y **Multiplos de Pares (CCA)**, con soporte multi-mercado y multi-moneda.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://financial-analytics-portfolio.streamlit.app)

---

## Funcionalidades

| Modulo | Descripcion |
|---|---|
| **DCF** | WACC auto-detectado por pais (Damodaran 2024), FCF proyectado, valor terminal Gordon Growth, sensibilidad WACC × g |
| **Multiplos** | Peers automaticos por sector, EV/EBITDA / P/E / Margen EBITDA / ROE / Yield con pesos ajustables |
| **Multi-mercado** | S&P 500, BVC Colombia, LSE, TSX, ASX y cualquier mercado disponible en Yahoo Finance |
| **Reportes** | PDF investing memo profesional + Excel multi-hoja descargables desde el dashboard |
| **Moneda** | Tipo de cambio automatico — muestra precio objetivo en moneda local y equivalente USD |

---

## Instalacion local

```bash
git clone https://github.com/jnicolas1551/financial-analytics-portfolio.git
cd financial-analytics-portfolio
pip install -r requirements.txt
streamlit run app.py
```

---

## Estructura del proyecto

```
financial-analytics-portfolio/
├── app.py                     # Entrada principal Streamlit
├── requirements.txt
├── .streamlit/config.toml     # Tema oscuro
├── modules/
│   ├── country_data.py        # Tabla Damodaran ~26 paises + peers por sector
│   ├── data_fetcher.py        # Descarga yfinance + peers automaticos + FX
│   ├── dcf_model.py           # WACC, FCF, DCF, sensibilidad
│   ├── multiples_model.py     # CCA estandar + scoring ponderado
│   └── report_generator.py   # PDF investing memo + Excel
└── components/
    ├── styles.py              # Paleta de colores + CSS
    └── charts.py             # Graficos Plotly (UI) + Matplotlib (PDF)
```

---

## Metodologia

### WACC
- **Ke** = Rf + β × Prima_mercado + Prima_pais (CAPM + Damodaran CRP)
- **Kd** = Gastos_financieros / Deuda_total × (1 − t)
- Pesos por valor de mercado (no valor libro)
- Parametros de pais auto-detectados desde Yahoo Finance (`info['country']`)

### DCF
- **FCF** = UODI + D&A − ΔCapital_Trabajo − CAPEX
- Proyeccion explicita de 3-10 anos a tasa definida por el usuario
- Valor terminal: Gordon Growth Model (FCF_n × (1+g) / (WACC − g))
- Tabla de sensibilidad WACC ± 2% × g 0.5%-4%

### Multiplos
- Precio implicito por EV/EBITDA, P/E y EV/Revenue usando **mediana** de peers (mas robusta que promedio)
- Precio combinado ponderado por pesos definidos por el usuario
- Scoring de eficiencia relativa por metrica

---

## Mercados soportados

| Region | Ejemplo tickers |
|---|---|
| USA (S&P 500) | AAPL, MSFT, GOOGL, DPZ |
| Colombia (BVC) | ECOPETROL.CL, PFBCOLOM.CL, ISA.CL |
| Mexico | AMXL.MX, FEMSAUBD.MX |
| Europa | SAP.DE, NESN.SW, MC.PA |
| Otros | Cualquier ticker disponible en Yahoo Finance |

---

## Disclaimer

Este dashboard es de caracter **educativo e informativo**. No constituye asesoria financiera ni recomendacion de inversion. Los modelos de valoracion implican supuestos que pueden no reflejar condiciones futuras. Consulte con un asesor financiero certificado antes de tomar decisiones de inversion.

---

*Desarrollado con Python + Streamlit + yfinance + fpdf2 + xlsxwriter*
