"""Detección automática de activos relacionados a partir de un diagrama SVG.

Los diagramas de topología/arquitectura suben como SVG (o PDF/imagen, para
los que esta detección no aplica) y ya traen texto legible dentro de sus
elementos <text> — normalmente el nombre visible del equipo/sistema
("pfSense FW", "Proxmox R740"), no siempre el código formal del activo
("RED-003"). Esta función cruza esos textos contra el nombre y el ID de
cada activo del inventario para SUGERIR relaciones — nunca las aplica sin
que la persona las confirme en el formulario, porque una relación
incorrecta en un diagrama de red es justamente el tipo de error que un
SGSI no debería introducir en silencio.

Solo cubre SVG: es el único formato de los que acepta el formulario
(imagen, PDF, SVG) donde el texto queda accesible sin OCR.
"""
import difflib
import re
import xml.etree.ElementTree as ET

UMBRAL_CONFIANZA = 0.55

# Palabras demasiado genéricas en este dominio como para servir de pista por
# sí solas (aparecerían en decenas de activos distintos).
PALABRAS_GENERICAS = {
    "servidor", "sistema", "version", "activo", "equipo", "dispositivo",
    "modulo", "modelo", "para", "con", "los", "las", "del", "the", "and",
    # Boilerplate institucional: aparece en casi cualquier diagrama (título,
    # marca de agua) sin identificar ningún equipo en particular.
    "suiin", "cric", "topologia", "topología", "arquitectura", "diagrama",
    "ejemplo", "plano", "flujo",
}


def es_svg(nombre_archivo, contenido=None):
    if nombre_archivo and nombre_archivo.lower().endswith(".svg"):
        return True
    if contenido:
        cabecera = contenido[:200].lstrip().lower()
        return cabecera.startswith(b"<?xml") or cabecera.startswith(b"<svg")
    return False


def extraer_textos_svg(contenido_bytes):
    """Devuelve la lista de fragmentos de texto legibles del SVG (vacía si
    el archivo no es un SVG válido — nunca lanza excepción, para que un
    archivo mal formado no rompa la subida del diagrama)."""
    try:
        root = ET.fromstring(contenido_bytes)
    except ET.ParseError:
        return []
    textos = []
    for el in root.iter():
        etiqueta = el.tag.split("}")[-1]
        if etiqueta in ("text", "title", "desc"):
            texto = "".join(el.itertext()).strip()
            if texto:
                textos.append(texto)
    return textos


def _normalizar(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _tokens_significativos(s):
    return {t for t in _normalizar(s).split()
            if len(t) >= 4 and t not in PALABRAS_GENERICAS}


def _peso_token(t):
    # Un token con dígitos suele ser un modelo/código ("r740", "x8-2s") y
    # discrimina mucho mejor que una marca genérica compartida por varios
    # equipos ("proxmox", "dell") — se pondera más alto a propósito.
    return len(t) + (4 if any(c.isdigit() for c in t) else 0)


def sugerir_activos(contenido_bytes, activos):
    """`activos` es un iterable de objetos con .id, .id_activo, .nombre.
    Devuelve una lista de sugerencias ordenada por confianza descendente,
    cada una con el texto del diagrama que motivó la coincidencia (para
    que la persona pueda verificarla de un vistazo, no solo confiar a
    ciegas).

    La señal principal es la superposición de palabras "significativas"
    (marca, modelo, sigla) entre el texto del diagrama y el nombre del
    activo — comparar las cadenas completas con difflib subestima
    coincidencias como "pfSense FW" contra "Firewall — Netgate pfSense NG
    Firewall", porque son de longitud muy distinta aunque compartan la
    palabra que realmente identifica el equipo. difflib queda como
    respaldo para variantes de escritura sin una palabra en común exacta.
    """
    textos = extraer_textos_svg(contenido_bytes)
    if not textos:
        return []
    textos_analizados = [
        (t, _normalizar(t), _tokens_significativos(t)) for t in textos]

    sugerencias = []
    for activo in activos:
        nombre_norm = _normalizar(activo.nombre)
        id_norm = _normalizar(activo.id_activo)
        tokens_nombre = _tokens_significativos(activo.nombre) | _tokens_significativos(activo.id_activo)
        mejor_ratio, mejor_texto = 0.0, None

        for texto_original, texto_norm, tokens_texto in textos_analizados:
            if not texto_norm:
                continue
            if id_norm and len(id_norm) >= 3 and id_norm in texto_norm:
                mejor_ratio, mejor_texto = 1.0, texto_original
                break

            comunes = tokens_nombre & tokens_texto
            if comunes:
                palabra_clave = max(comunes, key=_peso_token)
                peso = _peso_token(palabra_clave)
                ratio = min(0.97, 0.55 + 0.05 * (peso - 4) + 0.03 * (len(comunes) - 1))
            else:
                ratio = difflib.SequenceMatcher(None, nombre_norm, texto_norm).ratio()

            if ratio > mejor_ratio:
                mejor_ratio, mejor_texto = ratio, texto_original

        if mejor_ratio >= UMBRAL_CONFIANZA:
            sugerencias.append({
                "activo_id": activo.id,
                "id_activo": activo.id_activo,
                "nombre": activo.nombre,
                "texto_coincidente": mejor_texto,
                "confianza": round(mejor_ratio, 2),
            })

    sugerencias.sort(key=lambda s: -s["confianza"])
    return sugerencias
