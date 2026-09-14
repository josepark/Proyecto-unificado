"""Validación de detalle_extra contra detalle_schema de ClaseActivo (Ola 2)."""

TIPOS = ("texto", "entero", "decimal", "booleano", "fecha", "opciones")


def _error(campo, mensaje):
    return f"{campo}: {mensaje}"


def validar_detalle_extra(schema, datos):
    """Devuelve (datos_normalizados, lista_errores)."""
    if not schema or not schema.get("campos"):
        return dict(datos or {}), []

    datos = dict(datos or {})
    errores = []
    campos = schema.get("campos") or []
    permitidos = set()

    for spec in campos:
        if not isinstance(spec, dict):
            continue
        nombre = (spec.get("nombre") or "").strip()
        if not nombre:
            continue
        permitidos.add(nombre)
        valor = datos.get(nombre)
        requerido = bool(spec.get("requerido"))
        if valor in (None, "") and requerido:
            errores.append(_error(nombre, "es obligatorio"))
            continue
        if valor in (None, ""):
            continue

        tipo = (spec.get("tipo") or "texto").lower()
        try:
            if tipo == "texto":
                datos[nombre] = str(valor).strip()
            elif tipo == "entero":
                n = int(valor)
                if "min" in spec and n < spec["min"]:
                    errores.append(_error(nombre, f"debe ser ≥ {spec['min']}"))
                elif "max" in spec and n > spec["max"]:
                    errores.append(_error(nombre, f"debe ser ≤ {spec['max']}"))
                else:
                    datos[nombre] = n
            elif tipo == "decimal":
                datos[nombre] = float(valor)
            elif tipo == "booleano":
                if isinstance(valor, bool):
                    datos[nombre] = valor
                else:
                    datos[nombre] = str(valor).strip().lower() in ("1", "true", "si", "sí", "yes")
            elif tipo == "fecha":
                datos[nombre] = str(valor).strip()
            elif tipo == "opciones":
                opciones = [str(o) for o in (spec.get("opciones") or [])]
                s = str(valor).strip()
                if opciones and s not in opciones:
                    errores.append(_error(nombre, f"valor no válido ({', '.join(opciones)})"))
                else:
                    datos[nombre] = s
            else:
                datos[nombre] = valor
        except (TypeError, ValueError):
            errores.append(_error(nombre, f"no es un {tipo} válido"))

    for clave in datos:
        if clave not in permitidos:
            errores.append(_error(clave, "no está definido en el esquema de la clase"))

    return datos, errores
