"""
Motor de calculo de riesgos del SGSI SUIIN.

Metodologia (probabilidad x impacto), alineada a ISO/IEC 27005:

  IMPACTO (1-5): derivado de la valoracion C-I-D (valor = C+I+D, rango 0-12).
      0-2 -> 1 | 3-5 -> 2 | 6-8 -> 3 | 9-10 -> 4 | 11-12 -> 5

  PROBABILIDAD (1-5): base 1, incrementada por exposicion a amenazas y
      hallazgos de vulnerabilidad, reducida por controles aplicados.
      amenazas:   0->0 | 1-2->+1 | 3-4->+2 | 5+->+3
      hallazgos:  0->0 | 1-3->+1 | 4+->+2
      controles:  >=3 aplicados -> -1
      (resultado acotado a 1-5)

  RIESGO = probabilidad x impacto (1-25), clasificado:
      >=17 Critico | 10-16 Alto | 5-9 Medio | 1-4 Bajo
"""

NIVELES = ["BAJO", "MED", "ALTO", "CRIT"]


def impacto_de_valor(valor):
    if valor is None:
        return None
    if valor <= 2:
        return 1
    if valor <= 5:
        return 2
    if valor <= 8:
        return 3
    if valor <= 10:
        return 4
    return 5


def _factor_amenazas(n):
    if n >= 5:
        return 3
    if n >= 3:
        return 2
    if n >= 1:
        return 1
    return 0


def _factor_hallazgos(n):
    if not n:
        return 0
    if n >= 4:
        return 2
    return 1


def clasificar(score):
    if score >= 17:
        return "CRIT"
    if score >= 10:
        return "ALTO"
    if score >= 5:
        return "MED"
    return "BAJO"


def calcular_activo(activo):
    """
    Devuelve un dict con probabilidad, impacto, score y nivel calculado
    para un activo. Requiere que el activo tenga sus relaciones cargadas.
    """
    valor = activo.valor
    impacto = impacto_de_valor(valor)

    n_amenazas = activo.amenazas.count()
    n_controles = activo.controles.count()
    hallazgos = 0
    if hasattr(activo, "infraestructura") and activo.infraestructura:
        hallazgos = activo.infraestructura.hallazgos_abiertos or 0

    prob = 1 + _factor_amenazas(n_amenazas) + _factor_hallazgos(hallazgos)
    if n_controles >= 3:
        prob -= 1
    prob = max(1, min(5, prob))

    if impacto is None:
        return {"probabilidad": prob, "impacto": None, "score": None,
                "nivel": "SIN", "n_amenazas": n_amenazas,
                "n_controles": n_controles, "hallazgos": hallazgos}

    score = prob * impacto
    return {"probabilidad": prob, "impacto": impacto, "score": score,
            "nivel": clasificar(score), "n_amenazas": n_amenazas,
            "n_controles": n_controles, "hallazgos": hallazgos}
