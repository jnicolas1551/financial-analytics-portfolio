"""
Analisis de Comparables (CCA) con scoring ponderado por el usuario.
Metodo estandar: precio implicito directo por cada multiplo.
Metodo eficiencia: ajuste ponderado sobre mediana de peers.
"""
import numpy as np
import pandas as pd


# Configuracion de cada multiplo: etiqueta, direccion y columna de datos
METRIC_CONFIG: dict = {
    "ev_ebitda": {
        "label":     "EV/EBITDA",
        "direction": "lower_better",   # menor = empresa mas barata
        "default_w": 40,
    },
    "trailing_pe": {
        "label":     "P/E",
        "direction": "lower_better",
        "default_w": 10,
    },
    "ebitda_margin": {
        "label":     "Margen EBITDA",
        "direction": "higher_better",  # mayor = empresa mas eficiente
        "default_w": 30,
    },
    "return_on_equity": {
        "label":     "ROE",
        "direction": "higher_better",
        "default_w": 15,
    },
    "dividend_yield": {
        "label":     "Dividend Yield",
        "direction": "higher_better",
        "default_w": 5,
    },
}


def _median(values: list) -> float | None:
    clean = [v for v in values if v is not None and not np.isnan(v) and v > 0]
    return float(np.median(clean)) if clean else None


def _peer_value(peer: dict, key: str) -> float | None:
    v = peer.get(key)
    if v is None or (isinstance(v, float) and np.isnan(v)) or v <= 0:
        return None
    return float(v)


def run_multiples_analysis(
    target:  dict,
    peers:   list[dict],
    weights: dict,
) -> dict:
    """
    Calcula precios objetivo via multiplos directos y via scoring ponderado.

    Args:
        target:  metricas de la empresa objetivo (metrics dict)
        peers:   lista de dicts de metricas de peers
        weights: {metric_key: peso (0-100)} — el usuario los ajusta

    Returns:
        dict con precios directos, scoring, tabla de peers y precio final.
    """
    if not peers:
        return {"error": "Sin peers disponibles para comparacion."}

    debt   = target.get("total_debt",  0) or 0
    cash   = target.get("total_cash",  0) or 0
    shares = target.get("shares",      1) or 1
    ebitda = target.get("ebitda",      0) or 0
    rev    = target.get("total_revenue", 0) or 0
    eps    = target.get("trailing_eps",  0) or 0

    # ------------------------------------------------------------------ #
    # 1. PRECIOS DIRECTOS (metodo estandar)
    # ------------------------------------------------------------------ #
    direct: dict = {}

    med_ev_ebitda = _median([_peer_value(p, "ev_ebitda")  for p in peers])
    med_pe        = _median([_peer_value(p, "trailing_pe") for p in peers if
                             (p.get("trailing_pe") or 0) < 150])  # excluir outliers
    med_ev_rev    = _median([_peer_value(p, "ev_revenue")  for p in peers])

    if med_ev_ebitda and ebitda > 0:
        implied_ev = med_ev_ebitda * ebitda
        direct["ev_ebitda"] = max((implied_ev - debt + cash) / shares, 0)
        direct["_med_ev_ebitda"] = med_ev_ebitda

    if med_pe and eps > 0:
        direct["pe"] = med_pe * eps
        direct["_med_pe"] = med_pe

    if med_ev_rev and rev > 0:
        implied_ev = med_ev_rev * rev
        direct["ev_revenue"] = max((implied_ev - debt + cash) / shares, 0)
        direct["_med_ev_rev"] = med_ev_rev

    # ------------------------------------------------------------------ #
    # 2. SCORING PONDERADO DE EFICIENCIA
    # ------------------------------------------------------------------ #
    total_w = sum(weights.values()) or 1
    norm_w  = {k: v / total_w for k, v in weights.items()}

    peer_medians: dict  = {}
    target_vals:  dict  = {}
    efficiency:   dict  = {}

    for key, cfg in METRIC_CONFIG.items():
        peer_vals = [_peer_value(p, key) for p in peers]
        med       = _median(peer_vals)
        tgt       = _peer_value(target, key)

        if med is None or tgt is None:
            continue

        peer_medians[key] = med
        target_vals[key]  = tgt

        if cfg["direction"] == "higher_better":
            eff = tgt / med - 1
        else:  # lower_better
            eff = med / tgt - 1

        efficiency[key] = eff

    # Eficiencia ponderada total
    weighted_eff = sum(
        efficiency[k] * norm_w.get(k, 0)
        for k in efficiency
    )

    # Precio via scoring: ajustar mediana EV/EBITDA por eficiencia
    efficiency_price = None
    if "ev_ebitda" in peer_medians and ebitda > 0:
        adj_multiple    = max(peer_medians["ev_ebitda"] * (1 + weighted_eff), 1.0)
        implied_ev_adj  = adj_multiple * ebitda
        efficiency_price = max((implied_ev_adj - debt + cash) / shares, 0)

    # ------------------------------------------------------------------ #
    # 3. PRECIO COMBINADO (media ponderada de multiplos directos)
    # ------------------------------------------------------------------ #
    price_contributions = []
    weight_sum = 0.0

    if "ev_ebitda" in direct:
        w = norm_w.get("ev_ebitda", 0.4)
        price_contributions.append(direct["ev_ebitda"] * w)
        weight_sum += w
    if "pe" in direct:
        w = norm_w.get("trailing_pe", 0.1)
        price_contributions.append(direct["pe"] * w)
        weight_sum += w
    if "ev_revenue" in direct:
        w = 0.1
        price_contributions.append(direct["ev_revenue"] * w)
        weight_sum += w

    combined_price = (sum(price_contributions) / weight_sum) if weight_sum > 0 else None

    # ------------------------------------------------------------------ #
    # 4. TABLA DE PEERS
    # ------------------------------------------------------------------ #
    rows = []
    for p in peers:
        rows.append({
            "Ticker":        p.get("ticker", ""),
            "Empresa":       p.get("name", "")[:30],
            "EV/EBITDA":     _peer_value(p, "ev_ebitda"),
            "P/E":           _peer_value(p, "trailing_pe"),
            "Mg. EBITDA":    _peer_value(p, "ebitda_margin"),
            "ROE":           _peer_value(p, "return_on_equity"),
            "Div. Yield":    _peer_value(p, "dividend_yield"),
            "Q Tobin":       _peer_value(p, "q_tobin"),
            "Beta":          _peer_value(p, "beta"),
        })
    peer_df = pd.DataFrame(rows)

    return {
        "direct_prices":    direct,
        "combined_price":   combined_price,
        "efficiency_price": efficiency_price,
        "peer_medians":     peer_medians,
        "target_vals":      target_vals,
        "efficiency":       efficiency,
        "weighted_eff":     weighted_eff,
        "peer_table":       peer_df,
        "norm_weights":     norm_w,
        "error":            None,
    }
