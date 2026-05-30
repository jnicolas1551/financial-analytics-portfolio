---
name: finanzas-valoracion
description: >
  Skill especializada en valoración de empresas y análisis de portafolio para mercados
  S&P 500 y BVC (Colombia). Úsala siempre que el usuario mencione: DCF, flujos de caja
  descontados, WACC, múltiplos comparables, EV/EBITDA, P/E, DDM, NAV, valoración por
  activos, análisis fundamental, optimización de portafolio, Markowitz, Sharpe ratio,
  frontera eficiente, estados financieros, o cualquier tarea de valuación o construcción
  de portafolio. También aplica cuando el usuario pida interpretar métricas financieras,
  comparar empresas, o estructurar un modelo de inversión. Si hay duda, úsala.
---

# Skill: Valoración de Empresas y Análisis de Portafolio

## Contexto del usuario
- Ingeniero civil con MAF en EAFIT
- Mercados foco: **S&P 500** y **BVC (Colombia)**
- Fuentes de datos: `yfinance`, Excel/CSV manuales
- Idioma: explicaciones en español, código/fórmulas en inglés

---

## 1. Métodos de Valoración

### 1.1 DCF — Flujos de Caja Descontados
**Cuándo usar:** Empresas con flujos predecibles, estables o en crecimiento moderado.

**Estructura del modelo:**
```
FCF = EBIT(1-t) + D&A - CAPEX - ΔWWC
Valor Terminal = FCF_n × (1+g) / (WACC - g)
Valor Empresa = Σ FCF_t/(1+WACC)^t + VT/(1+WACC)^n
Valor Equity = Valor Empresa - Deuda Neta
Precio por acción = Valor Equity / Shares Outstanding
```

**WACC:**
```
WACC = (E/V)×Ke + (D/V)×Kd×(1-t)
Ke = Rf + β×(Rm - Rf) + Prima país (si aplica BVC)
```

**Consideraciones BVC:**
- Agregar prima de riesgo país Colombia (EMBI+): ~200-350 bps histórico
- Usar TRM para convertir si los flujos son en COP y comparas con USD
- Beta: usar betas de comparables del S&P si no hay liquidez suficiente en BVC

**Consideraciones S&P 500:**
- Rf: Treasury 10Y (buscar en FRED: `DGS10`)
- Prima de mercado: 4.5%–6% histórico Damodaran
- Beta: regresión vs SPY a 5 años, frecuencia mensual

---

### 1.2 Múltiplos Comparables
**Cuándo usar:** Valoración rápida, benchmarking sectorial, sanity check del DCF.

**Múltiplos principales:**

| Múltiplo | Fórmula | Uso |
|----------|---------|-----|
| EV/EBITDA | Enterprise Value / EBITDA | Universal, ajusta deuda |
| P/E | Precio / EPS | Empresas maduras con utilidades |
| P/S | Precio / Ventas | Growth companies sin utilidades |
| P/BV | Precio / Book Value | Financieras, bancos |
| EV/EBIT | EV / EBIT | Cuando D&A distorsiona |

**Proceso:**
1. Definir peer group (mismo sector, tamaño similar, mercado comparable)
2. Calcular múltiplos del peer group → mediana (no promedio, evitar outliers)
3. Aplicar múltiplo mediana a métricas de la empresa objetivo
4. Aplicar descuento por iliquidez si es BVC (~15-25%)

---

### 1.3 DDM — Dividend Discount Model
**Cuándo usar:** Empresas con política de dividendos estable y predecible (utilities, bancos maduros).

```
Gordon Growth: P = D1 / (Ke - g)
Multi-stage:   P = Σ Dt/(1+Ke)^t + Pn/(1+Ke)^n
```

**Advertencia:** Inapropiado para empresas sin dividendos o con payout inconsistente.

---

### 1.4 NAV — Net Asset Value
**Cuándo usar:** Holdings, REITs, empresas de recursos naturales, conglomerados.

```
NAV = Valor de Mercado de Activos - Deuda Total
Descuento/Premio NAV = (Precio Mercado - NAV) / NAV
```

---

## 2. Análisis de Portafolio

### 2.1 Optimización Markowitz (Mean-Variance)
**Framework:**
```
Maximizar:  Sharpe = (Rp - Rf) / σp
Sujeto a:   Σ wi = 1,  wi ≥ 0 (long-only)

Rp = Σ wi × Ri
σp² = w' × Σ × w   (Σ = matriz de covarianzas)
```

**Proceso estándar:**
1. Definir universo de activos
2. Calcular retornos históricos (mínimo 3 años, frecuencia diaria o mensual)
3. Estimar matriz de covarianzas (usar Ledoit-Wolf si n_activos > 20)
4. Correr optimización → frontera eficiente
5. Seleccionar portafolio de máximo Sharpe o mínima varianza

**Métricas de evaluación del portafolio:**

| Métrica | Fórmula | Referencia |
|---------|---------|------------|
| Sharpe Ratio | (Rp-Rf)/σp | >1 aceptable, >2 excelente |
| Sortino Ratio | (Rp-Rf)/σ_downside | Mejor que Sharpe para asimétricas |
| Max Drawdown | (Peak-Trough)/Peak | Riesgo de caída máxima |
| Beta portafolio | Cov(Rp,Rm)/Var(Rm) | Sensibilidad al mercado |
| Alpha (Jensen) | Rp - [Rf + β(Rm-Rf)] | Retorno ajustado por riesgo |

### 2.2 Consideraciones BVC vs S&P
- **Liquidez BVC:** Filtrar acciones con volumen diario > COP 500M para evitar iliquidez
- **Correlación:** BVC y S&P tienen correlación moderada (~0.4-0.6), útil para diversificación
- **Divisa:** Definir si portafolio mixto se denomina en USD o COP; modelar riesgo cambiario

---

## 3. Análisis Fundamental — Checklist

### Estados Financieros (orden de lectura)
1. **Balance General:** Estructura de capital, liquidez (current ratio, quick ratio)
2. **P&G:** Márgenes (bruto, EBITDA, neto), crecimiento de ingresos
3. **Flujo de Caja:** FCF yield, calidad de utilidades (FCF/Net Income > 0.8 es buena señal)

### Red Flags
- Deuda Neta/EBITDA > 4x (apalancamiento alto)
- FCF negativo recurrente con utilidades positivas (accruals)
- Goodwill > 30% de activos totales
- Deterioro de márgenes en tendencia de 3+ años

---

## 4. Estructura de Entregables

Cuando el usuario pida una valoración, siempre entregar:
1. **Resumen ejecutivo** (precio objetivo, upside/downside, recomendación)
2. **Supuestos clave** (WACC, g, múltiplos usados)
3. **Análisis de sensibilidad** (tabla WACC vs g mínimo)
4. **Riesgos principales** (3-5 bullets)

Para portafolio:
1. **Pesos óptimos** por activo
2. **Métricas del portafolio** (Sharpe, volatilidad, retorno esperado)
3. **Frontera eficiente** (si hay código disponible, graficar)
4. **Comparación vs benchmark** (SPY para S&P, COLCAP para BVC)

---

## 5. Referencias rápidas

- Damodaran data (betas, primas): `pages.stern.nyu.edu/~adamodar/`
- FRED (tasas USA): `fred.stlouisfed.org`
- BVC datos: `bvc.com.co` / `simev.superfinanciera.gov.co`
- SEC EDGAR (10-K, 10-Q): `sec.gov/edgar`
- Documentación extendida: ver `references/formulas.md` y `references/bvc-guide.md`
