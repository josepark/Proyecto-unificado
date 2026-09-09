"""Utilidades para racks físicos — parsing legacy y emparejamiento (Ola 4)."""
import re


def normalizar_codigo_rack(texto):
    """Limpia texto legacy («Rack 2», «RACK-NORTE-03») para comparar con catálogo."""
    if not texto:
        return ""
    t = str(texto).strip()
    t = re.sub(r"^(rack\s*[-:]?\s*)", "", t, flags=re.I)
    return t.strip().upper()


def parse_unidad_rack(texto):
    """Convierte «U12-U14», «U40» o «12-14» en (inicio, fin) o (None, None)."""
    if not texto:
        return None, None
    t = str(texto).strip().upper().replace(" ", "")
    m = re.match(r"^U?(\d+)(?:-U?(\d+))?$", t)
    if not m:
        return None, None
    ini = int(m.group(1))
    fin = int(m.group(2)) if m.group(2) else ini
    if fin < ini:
        ini, fin = fin, ini
    return ini, fin


def emparejar_rack_en_datacenter(racks_qs, texto_legacy):
    """Busca un Rack del queryset cuyo código coincida con texto legacy."""
    codigo = normalizar_codigo_rack(texto_legacy)
    if not codigo:
        return None
    for rack in racks_qs:
        if rack.codigo.upper() == codigo:
            return rack
    for rack in racks_qs:
        rc = rack.codigo.upper()
        if codigo in rc or rc in codigo:
            return rack
    return None


def texto_ubicacion_rack(inf):
    """Texto legible de rack/U para etiquetas PDF y reportes."""
    if not inf:
        return None
    if inf.rack_fk_id:
        u = ""
        if inf.unidad_inicio and inf.unidad_fin:
            u = f" U{inf.unidad_inicio}-U{inf.unidad_fin}"
        elif inf.unidad_inicio:
            u = f" U{inf.unidad_inicio}"
        return f"Rack {inf.rack_fk.codigo}{u}"
    if inf.rack:
        return f"Rack {inf.rack}" + (f" U{inf.unidad_rack}" if inf.unidad_rack else "")
    return None
