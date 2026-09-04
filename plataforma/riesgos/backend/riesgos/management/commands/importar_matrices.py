# -*- coding: utf-8 -*-
"""
importar_matrices — Sistematiza las matrices Excel de riesgos SUIIN/CRIC en la base de datos.

Uso:
    python manage.py importar_matrices \
        --matriz-riesgos /ruta/SUIIN_CRIC_Analisis_Matriz_DE_RIESGOS_v1.xlsx \
        --ptr /ruta/SUIIN_SGSI_CENSO_PlanTratamiento_de_Riesgos.xlsx

Ambos parámetros son opcionales de forma independiente: puede importar solo la matriz de
riesgos, solo un PTR, o ambos. El comando es idempotente (usa update_or_create) — se puede
volver a ejecutar tras corregir datos en el Excel sin duplicar registros.
"""
import re
import datetime as dt

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from riesgos.sincronizacion import ProtectorSincronizacion

from riesgos.models import (
    Activo, PuertoServicio, Vulnerabilidad, RiesgoActivo, RiesgoContextual,
    CampanaRedTeam, PlanTratamientoRiesgos, AccionTratamiento,
)

# ---------------------------------------------------------------------------
# Tablas de mapeo: texto libre del Excel -> choices del modelo
# ---------------------------------------------------------------------------

NIVEL_MAP = {
    "crítico": "CRITICO", "critico": "CRITICO",
    "alto": "ALTO", "medio": "MEDIO", "bajo": "BAJO",
    "—": "SIN_DATO", "-": "SIN_DATO", "": "SIN_DATO",
}

CLASIFICACION_MAP = {
    "altamente confidencial": "ALTAMENTE_CONFIDENCIAL",
    "confidencial": "CONFIDENCIAL",
    "público": "PUBLICO", "publico": "PUBLICO",
    "desconocida": "DESCONOCIDA",
}

COBERTURA_MAP = {
    "completa (nmap+ov)": "COMPLETA",
    "parcial (solo nmap)": "PARCIAL",
    "sin cobertura": "SIN_COBERTURA",
}

TRATAMIENTO_MAP = {
    "mitigar (inmediato)": "MITIGAR_INMEDIATO",
    "mitigar (urgente)": "MITIGAR_URGENTE",
    "mitigar (planificado)": "MITIGAR_PLANIFICADO",
    "aceptar": "ACEPTAR", "transferir": "TRANSFERIR", "eliminar": "ELIMINAR",
}

OPCION_TRATAMIENTO_MAP = {
    "mitigar": "MITIGAR",
    "mitigar / eliminar": "MITIGAR_ELIMINAR",
    "aceptar": "ACEPTAR", "transferir": "TRANSFERIR", "eliminar": "ELIMINAR",
}

ESTADO_MAP = {
    "pendiente": "PENDIENTE",
    "en progreso": "EN_PROGRESO",
    "cerrado": "CERRADO",
    "falso positivo": "FALSO_POSITIVO",
    "aceptado": "ACEPTADO",
}

# Sheet01 "Campaña RT" usa nombres distintos a los encabezados de sheet07; se normalizan aquí.
CAMPANA_ALIASES = {
    "suiin-censo": "SUIIN-CENSO",
    "minga-para-tejer": "MINGA-PARA-TEJER",
    "suiin-sion": "SION", "sion": "SION",
    "suiin-sia-uaiin": "SIA-UAIIN", "sia-uaiin": "SIA-UAIIN",
}

MESES = {
    "ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3, "marzo": 3,
    "abr": 4, "abril": 4, "may": 5, "mayo": 5, "jun": 6, "junio": 6,
    "jul": 7, "julio": 7, "ago": 8, "agosto": 8, "sep": 9, "septiembre": 9,
    "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11, "dic": 12, "diciembre": 12,
}


def norm(value) -> str:
    """Normaliza texto para usarlo como clave de mapeo (minúsculas, sin espacios extra)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip().lower()


def s(value) -> str:
    """Convierte a string limpio, tratando NaN/None/'—' como cadena vacía."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text in ("—", "-", "nan", "NaT") else text


def to_int(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def to_bool_si_no(value) -> bool:
    return norm(value) in ("sí", "si", "yes", "true", "1")


def parse_fecha_relativa(texto: str, anio_default=2026):
    """
    Convierte fechas en formato libre en español a un rango (inicio, fin).
    Soporta: '1-2 jun 2026', '24 jun 2026', '26 mayo – 5 junio 2026', '11 de junio de 2026'.
    Devuelve (None, None) si no puede interpretarlo — no es crítico para la sistematización.
    """
    if not texto:
        return None, None
    texto = texto.replace("–", "-").replace("—", "-")

    # 'DD de MES de AAAA'
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto, re.IGNORECASE)
    if m:
        dia, mes_txt, anio = m.groups()
        mes = MESES.get(mes_txt.lower())
        if mes:
            fecha = dt.date(int(anio), mes, int(dia))
            return fecha, fecha

    # 'DD-DD MES AAAA' o 'DD MES - DD MES AAAA'
    m = re.search(
        r"(\d{1,2})\s*-\s*(\d{1,2})\s+(\w+)\s+(\d{4})", texto, re.IGNORECASE)
    if m:
        d1, d2, mes_txt, anio = m.groups()
        mes = MESES.get(mes_txt.lower())
        if mes:
            return dt.date(int(anio), mes, int(d1)), dt.date(int(anio), mes, int(d2))

    m = re.search(
        r"(\d{1,2})\s+(\w+)\s*-\s*(\d{1,2})\s+(\w+)\s+(\d{4})", texto, re.IGNORECASE)
    if m:
        d1, mes1_txt, d2, mes2_txt, anio = m.groups()
        mes1, mes2 = MESES.get(mes1_txt.lower()), MESES.get(mes2_txt.lower())
        if mes1 and mes2:
            return dt.date(int(anio), mes1, int(d1)), dt.date(int(anio), mes2, int(d2))

    # 'DD MES AAAA' (fecha única)
    m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", texto, re.IGNORECASE)
    if m:
        dia, mes_txt, anio = m.groups()
        mes = MESES.get(mes_txt.lower())
        if mes:
            fecha = dt.date(int(anio), mes, int(dia))
            return fecha, fecha

    return None, None


def leer_hoja(path, sheet_name, header_row, filtro_col=None, filtro_regex=None):
    """Lee una hoja, descarta la columna vacía inicial y filas de leyenda/ruido."""
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row).dropna(how="all")
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
    if filtro_col and filtro_regex:
        df = df[df[filtro_col].astype(str).str.match(filtro_regex, na=False)]
    return df.reset_index(drop=True)


class Command(BaseCommand):
    help = "Sistematiza las matrices Excel de riesgos SUIIN/CRIC en la base de datos."

    def add_arguments(self, parser):
        parser.add_argument("--matriz-riesgos", type=str, default=None,
                             help="Ruta a SUIIN_CRIC_Analisis_Matriz_DE_RIESGOS_v1.xlsx")
        parser.add_argument("--ptr", action="append", default=None,
                             help="Ruta a un archivo PTR (SUIIN_SGSI_*_PlanTratamiento_de_Riesgos.xlsx). "
                                  "Puede repetirse para importar varios PTR.")
        parser.add_argument(
            "--forzar-sobrescritura", action="store_true",
            help="Sobrescribe también los registros editados manualmente desde la última "
                 "importación (por defecto se PROTEGEN y se omiten — ver README §4). "
                 "Úselo solo si está seguro de que el Excel debe ganar sobre las ediciones "
                 "hechas en la aplicación.")

    def handle(self, *args, **options):
        matriz_path = options.get("matriz_riesgos")
        ptr_paths = options.get("ptr") or []
        self.protector = ProtectorSincronizacion(forzar=options["forzar_sobrescritura"])

        if not matriz_path and not ptr_paths:
            self.stderr.write(self.style.ERROR(
                "Debe indicar --matriz-riesgos y/o --ptr <archivo>."))
            return

        if self.protector.forzar:
            self.stdout.write(self.style.WARNING(
                "⚠ --forzar-sobrescritura activo: se sobrescribirán también los registros "
                "editados manualmente desde la última importación."))

        if matriz_path:
            with transaction.atomic():
                self.importar_matriz_riesgos(matriz_path)

        for ptr_path in ptr_paths:
            with transaction.atomic():
                self.importar_ptr(ptr_path)

        self.protector.reportar(self.stdout, self.stderr, self.style)

    def _guardar_protegiendo(self, modelo, filtro, defaults, descripcion):
        """Delega en ProtectorSincronizacion (riesgos/sincronizacion.py), compartido
        con el comando sincronizar_activos_inventario. Se conserva este método como
        atajo fino para no reescribir las ~10 llamadas ya existentes más abajo."""
        return self.protector.guardar_protegiendo(modelo, filtro, defaults, descripcion)

    # ------------------------------------------------------------------
    # Matriz de riesgos (10 hojas)
    # ------------------------------------------------------------------
    def importar_matriz_riesgos(self, path):
        self.stdout.write("→ Sistematizando matriz de riesgos: %s" % path)

        campanas = self.importar_campanas(path)
        activos = self.importar_activos(path, campanas)
        self.importar_puertos(path, activos)
        self.importar_vulnerabilidades(path, activos)
        self.importar_riesgos_activo(path, activos)
        self.importar_riesgos_contextuales(path, activos)

    def importar_campanas(self, path):
        df = leer_hoja(path, "07_Red_Team_Detalle", header_row=3)
        # Hoja transpuesta: primera columna = campo, resto de columnas = una campaña cada una.
        df = df.set_index(df.columns[0])
        campanas = {}
        for col in df.columns:
            nombre_col = str(col)
            m = re.match(r"^([\w\-]+)\s*\(\.(\d+)\)", nombre_col)
            if not m:
                continue
            nombre, ultimo_octeto = m.groups()
            host_ip = f"192.168.1.{ultimo_octeto}"

            def campo(etiqueta):
                try:
                    return df.loc[etiqueta, col]
                except KeyError:
                    return None

            fecha_txt = s(campo("Fechas del engagement"))
            f_ini, f_fin = parse_fecha_relativa(fecha_txt)

            riesgos_nivel = s(campo("Riesgos por nivel (C/A/M/B)"))
            crit = alto = medio = bajo = 0
            m2 = re.search(r"Críticos:(\d+)\s*Altos:(\d+)\s*Medios:(\d+)\s*Bajos:(\d+)", riesgos_nivel)
            if m2:
                crit, alto, medio, bajo = (int(x) for x in m2.groups())

            tecnicas_txt = s(campo("Técnicas MITRE ATT&CK usadas"))
            m3 = re.match(r"(\d+)", tecnicas_txt)
            tecnicas_count = int(m3.group(1)) if m3 else None

            estado_compromiso = "COMPROMETIDO" if norm(campo("Estado de compromiso")) == "comprometido" \
                else "NO_EVALUADO"

            obj, _ = self._guardar_protegiendo(
                CampanaRedTeam, filtro={"nombre": nombre},
                defaults=dict(
                    host_ip=host_ip, fecha_inicio=f_ini, fecha_fin=f_fin,
                    estado_compromiso=estado_compromiso,
                    estado_ufw=s(campo("Estado UFW")),
                    uptime_sin_reinicio=s(campo("Uptime sin reinicio")),
                    agentes_implantados=s(campo("Agentes implantados")),
                    servidores_c2=s(campo("Servidor(es) C2")),
                    datos_exfiltrados=s(campo("Datos exfiltrados")),
                    riesgo_maximo_correlacionado=s(campo("Riesgo máximo correlacionado")),
                    riesgos_criticos=crit, riesgos_altos=alto,
                    riesgos_medios=medio, riesgos_bajos=bajo,
                    puertos_no_documentados=s(campo("Puertos no documentados")),
                    tecnicas_mitre_count=tecnicas_count,
                    tecnicas_mitre_detalle=tecnicas_txt,
                ),
                descripcion=nombre,
            )
            campanas[nombre] = obj
        self.stdout.write(f"  · Campañas Red Team: {len(campanas)}")
        return campanas

    def importar_activos(self, path, campanas):
        df01 = leer_hoja(path, "01_Resumen_Triple", header_row=4)
        df04 = leer_hoja(path, "04_Activos_Sin_Cobertura", header_row=4)
        df06 = leer_hoja(path, "06_SI_vs_Vulns_Servidor", header_row=4)

        enriquecido_04 = {row["ID"]: row for _, row in df04.iterrows()}
        estado_operativo_06 = {row["ID"]: s(row["Estado"]) for _, row in df06.iterrows()}

        activos = {}
        for _, row in df01.iterrows():
            id_activo = s(row["ID Activo"])
            if not id_activo:
                continue
            campana_nombre = CAMPANA_ALIASES.get(norm(row.get("Campaña RT")))
            campana_obj = campanas.get(campana_nombre) if campana_nombre else None

            extra04 = enriquecido_04.get(id_activo)
            vlan = s(extra04["VLAN"]) if extra04 is not None else ""
            mitre = s(extra04["MITRE ATT&CK"]) if extra04 is not None else ""
            accion_rec = s(extra04["Acción Recomendada"]) if extra04 is not None else ""

            obj, _ = self._guardar_protegiendo(
                Activo, filtro={"id_activo": id_activo},
                defaults=dict(
                    nombre=s(row["Nombre del Activo"]) or id_activo,
                    tipo=s(row.get("Tipo")),
                    ip_principal=s(row.get("IP(s)")),
                    valor=to_int(row.get("Valor")) or 0,
                    riesgo_matriz=NIVEL_MAP.get(norm(row.get("Riesgo Matriz")), "SIN_DATO"),
                    clasificacion_si="DESCONOCIDA",  # se refina con datos de otras hojas si aplica
                    vlan=vlan,
                    en_nmap=to_bool_si_no(row.get("En Nmap")),
                    puertos_abiertos_resumen=s(row.get("Puertos Abiertos")),
                    cobertura=COBERTURA_MAP.get(norm(row.get("Cobertura")), "SIN_COBERTURA"),
                    observacion_critica=s(row.get("Observación Crítica")),
                    afectado_red_team=to_bool_si_no(row.get("Red Team")),
                    campana_red_team=campana_obj,
                    estado_ufw_activo=s(row.get("UFW")),
                    exfiltracion_confirmada=s(row.get("Exfiltración Confirmada")),
                    accion_inmediata_red_team=s(row.get("Acción Inmediata RT")),
                    mitre_attck=mitre,
                    accion_recomendada=accion_rec,
                    estado_operativo=estado_operativo_06.get(id_activo, ""),
                ),
                descripcion=id_activo,
            )
            activos[id_activo] = obj
        self.stdout.write(f"  · Activos: {len(activos)}")
        return activos

    def importar_puertos(self, path, activos):
        df = leer_hoja(path, "03_Inventario_Nmap_por_Activo", header_row=3)
        df["ID Activo"] = df["ID Activo"].ffill()
        creados = 0
        # A diferencia de Vulnerabilidad/RiesgoActivo/etc., aquí SÍ se borra y recrea
        # sin protección: no hay CRUD manual de puertos en la app (son de solo
        # lectura, ver ActivoDetalle), y semánticamente un puerto es una foto del
        # último escaneo Nmap — tiene sentido que la reimportación lo reemplace por
        # completo, no que "proteja" una versión anterior.
        PuertoServicio.objects.filter(activo__id_activo__in=df["ID Activo"].dropna().unique()).delete()
        for _, row in df.iterrows():
            id_activo = s(row["ID Activo"])
            activo = activos.get(id_activo)
            puerto = to_int(row.get("Puerto"))
            if not activo or puerto is None:
                continue
            PuertoServicio.objects.create(
                activo=activo,
                ip=s(row.get("IP")),
                sistema_operativo=s(row.get("Sistema Operativo (Nmap)")),
                puerto=puerto,
                protocolo=s(row.get("Protocolo")),
                servicio=s(row.get("Servicio")),
                producto_version=s(row.get("Producto / Versión")),
                observacion=s(row.get("Observación")),
                hallazgo_red_team=s(row.get("Hallazgo Red Team en este Puerto")),
            )
            creados += 1
        self.stdout.write(f"  · Puertos/servicios: {creados}")

    def importar_vulnerabilidades(self, path, activos):
        df02 = leer_hoja(path, "02_Vulns_por_Activo", header_row=3).rename(
            columns={"Vulnerabilidad": "vuln_name"})
        df09 = leer_hoja(path, "09_Matriz_Riesgo_Detalle", header_row=4,
                          filtro_col="ID Activo", filtro_regex=r"^(RED|SI)-\d+$").rename(
            columns={"Vulnerabilidad / Hallazgo": "vuln_name"})

        df02["seq"] = df02.groupby(["ID Activo", "vuln_name"]).cumcount()
        df09["seq"] = df09.groupby(["ID Activo", "vuln_name"]).cumcount()

        merged = df02.merge(df09, on=["ID Activo", "vuln_name", "seq"], how="outer",
                             suffixes=("_02", "_09"))

        # Antes este método borraba TODAS las vulnerabilidades del activo y las
        # recreaba desde cero — lo que destruía sin aviso cualquier vulnerabilidad
        # creada manualmente desde la app, o el progreso de tratamiento registrado
        # en una ya existente. Ahora usa la misma protección que el resto del
        # importador: crea si no existe, actualiza si no fue editada manualmente
        # desde la última importación, y NUNCA borra (si una vulnerabilidad ya no
        # aparece en el Excel, simplemente se deja de tocar — no desaparece).
        # Clave natural: (activo, nombre, IP) — es lo más estable que identifica
        # "el mismo hallazgo" entre dos exportaciones del Excel.
        for _, row in merged.iterrows():
            id_activo = s(row["ID Activo"])
            activo = activos.get(id_activo)
            if not activo:
                continue
            nombre_vuln = s(row.get("vuln_name"))
            if not nombre_vuln:
                continue

            prob = to_int(row.get("Prob"))
            impacto = to_int(row.get("Impacto"))
            cvss_raw = row.get("CVSS")
            cvss = None
            if cvss_raw is not None and not pd.isna(cvss_raw):
                try:
                    cvss = round(float(cvss_raw), 1)
                except (ValueError, TypeError):
                    cvss = None

            cves = row.get("CVE(s)_02")
            if cves is None or (isinstance(cves, float) and pd.isna(cves)):
                cves = row.get("CVE(s)_09")

            ip = s(row.get("IP_02")) or s(row.get("IP_09"))

            self._guardar_protegiendo(
                Vulnerabilidad, filtro={"activo": activo, "nombre_vulnerabilidad": nombre_vuln, "ip": ip},
                defaults=dict(
                    id_riesgo=s(row.get("ID Riesgo")),
                    severidad_ov=norm(row.get("Severidad OV")).upper() if s(row.get("Severidad OV")) else "",
                    cvss=cvss,
                    cves=s(cves),
                    descripcion_tecnica=s(row.get("Descripción Técnica")),
                    solucion_recomendada=s(row.get("Solución Recomendada")) or s(row.get("Acción / Solución")),
                    probabilidad=prob,
                    impacto=impacto,
                    evidencia_red_team=s(row.get("Evidencia Red Team")) or "Sin evidencia directa de explotación",
                    explotado_confirmado_rt=s(row.get("Explotado/Confirmado por Red Team")) or "—",
                    tratamiento=TRATAMIENTO_MAP.get(norm(row.get("Tratamiento")), ""),
                    estado=ESTADO_MAP.get(norm(row.get("Estado")), "PENDIENTE"),
                ),
                descripcion=f"{id_activo} · {nombre_vuln[:50]}",
            )
        self.stdout.write(f"  · Vulnerabilidades (fusión hojas 02+09): {len(merged)} fila(s) del Excel leídas")

    def importar_riesgos_activo(self, path, activos):
        df = leer_hoja(path, "08_Matriz_Riesgo_por_Activo", header_row=4,
                        filtro_col="ID Riesgo", filtro_regex=r"^RA-\d+$")
        for _, row in df.iterrows():
            activo_txt = s(row["Activo"])
            id_activo = activo_txt.split(" — ")[0].strip() if " — " in activo_txt else activo_txt
            activo = activos.get(id_activo)
            if not activo:
                self.stderr.write(self.style.WARNING(
                    f"  ⚠ RiesgoActivo {row['ID Riesgo']}: activo '{id_activo}' no encontrado, se omite"))
                continue
            fecha_obj = row.get("Fecha Objetivo")
            fecha_obj = None if pd.isna(fecha_obj) else fecha_obj

            self._guardar_protegiendo(
                RiesgoActivo, filtro={"id_riesgo": s(row["ID Riesgo"])},
                defaults=dict(
                    activo=activo,
                    clasificacion=NIVEL_MAP.get(norm(row.get("Clasificación")), "SIN_DATO"),
                    probabilidad=to_int(row.get("Prob")) or 1,
                    impacto=to_int(row.get("Impacto")) or 1,
                    tratamiento=TRATAMIENTO_MAP.get(norm(row.get("Tratamiento")), ""),
                    responsable_sugerido=s(row.get("Responsable Sugerido")),
                    estado=ESTADO_MAP.get(norm(row.get("Estado")), "PENDIENTE"),
                    fecha_objetivo=fecha_obj,
                    justificacion=s(row.get("Justificación")),
                    controles_accion=s(row.get("Controles / Acción")),
                ),
                descripcion=s(row["ID Riesgo"]),
            )
        self.stdout.write(f"  · Riesgos por activo: {len(df)} fila(s) del Excel leídas")

    def importar_riesgos_contextuales(self, path, activos):
        df = leer_hoja(path, "10_Matriz de riesgos de segurid", header_row=2)
        for _, row in df.iterrows():
            id_rc = s(row.get("ID Riesgo\nContextual"))
            if not re.match(r"^RC-\d+$", id_rc or ""):
                continue

            activos_texto = s(row.get("Activos SUIIN\nAfectados"))
            codigos = set(re.findall(r"\b(RED-\d+|SI-\d+)\b", activos_texto))

            obj, protegido = self._guardar_protegiendo(
                RiesgoContextual, filtro={"id_riesgo_contextual": id_rc},
                defaults=dict(
                    escenario_amenaza=s(row.get("Escenario de Amenaza\n(descripción)")),
                    actor_amenaza=s(row.get("Actor de Amenaza\n(threat actor)")),
                    activos_afectados_texto=activos_texto,
                    clasificacion_si=CLASIFICACION_MAP.get(
                        norm(row.get("Clasificación SI\nDatos en riesgo")), "DESCONOCIDA"),
                    datos_especificos_riesgo=s(row.get("Datos específicos\nen riesgo")),
                    probabilidad=to_int(row.get("Prob.\n(1–5)")) or 1,
                    impacto=to_int(row.get("Impacto\n(1–5)")) or 1,
                    marco_referencia=s(row.get("Marco de referencia\n(no CVE)")),
                    descripcion_escenario=s(row.get("Descripción del escenario\ny vector de ataque")),
                    impacto_cia_misional=s(row.get("Impacto CIA\n+ impacto misional")),
                    controles_iso=s(row.get("Controles ISO 27001\n+ marcos adicionales")),
                    accion_mitigacion=s(row.get("Acción de mitigación\nespecífica CRIC")),
                    plazo=s(row.get("Plazo")),
                    responsable=s(row.get("Responsable\n(org. CRIC)")),
                    ley_marco_legal=s(row.get("Ley / Marco legal\naplicable Colombia")),
                    estado_actual=s(row.get("Estado\nactual")) or "SIN_CONTROL",
                    observaciones_correlacion=s(row.get("Observaciones / Correlación\ncon riesgos técnicos")),
                ),
                descripcion=id_rc,
            )
            if not protegido:
                # La relación M2M no la maneja `defaults` (no es un campo simple) —
                # solo se toca si el registro no está protegido, por la misma razón.
                activos_rel = [activos[c] for c in codigos if c in activos]
                obj.activos_relacionados.set(activos_rel)
        self.stdout.write(f"  · Riesgos contextuales: {len(df)} fila(s) del Excel leídas")

    # ------------------------------------------------------------------
    # Plan de Tratamiento de Riesgos (PTR)
    # ------------------------------------------------------------------
    def importar_ptr(self, path):
        self.stdout.write("→ Sistematizando PTR: %s" % path)
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True)
        portada = wb["Portada"]

        def celda(r, c):
            return portada.cell(row=r, column=c).value

        referencia = s(celda(8, 4))
        titulo = s(celda(5, 2))
        subtitulo = s(celda(6, 2))  # ej. "SUIIN-CENSO - 192.168.1.203"
        clasificacion_doc = s(celda(9, 4)) or "CONFIDENCIAL — Uso Interno Restringido"
        fecha_emision_txt = s(celda(10, 4))
        periodo_txt = s(celda(11, 4))
        herramientas = s(celda(12, 4))
        host_objetivo_txt = s(celda(13, 4))

        f_emision, _ = parse_fecha_relativa(fecha_emision_txt)
        p_ini, p_fin = parse_fecha_relativa(periodo_txt)

        # El título/subtítulo de portada identifican la campaña de forma más confiable que el
        # campo "Host objetivo", que en algunos documentos fuente arrastra la IP de otra campaña
        # (plantilla reutilizada de un PTR previo). Se prioriza título/subtítulo; la IP es respaldo.
        campana = None
        for c in CampanaRedTeam.objects.all():
            alias = c.nombre.replace("-", " ").lower()
            if alias in titulo.lower() or alias in subtitulo.lower() or c.host_ip in subtitulo:
                campana = c
                break
        if not campana:
            host_ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", host_objetivo_txt)
            if host_ip_match:
                campana = CampanaRedTeam.objects.filter(host_ip=host_ip_match.group(1)).first()
        if not campana:
            self.stderr.write(self.style.ERROR(
                "  ⚠ No se encontró una CampanaRedTeam para este PTR. "
                "Importe primero la matriz de riesgos con --matriz-riesgos, o cree la campaña "
                "manualmente en el admin. Se omite este PTR."))
            return

        plan, _ = self._guardar_protegiendo(
            PlanTratamientoRiesgos, filtro={"referencia": referencia or f"PTR-{campana.nombre}"},
            defaults=dict(
                titulo=titulo or f"Plan de Tratamiento de Riesgos — {campana.nombre}",
                campana_red_team=campana,
                clasificacion_documento=clasificacion_doc,
                fecha_emision=f_emision or dt.date.today(),
                periodo_campana_inicio=p_ini,
                periodo_campana_fin=p_fin,
                herramientas=herramientas,
            ),
            descripcion=referencia or campana.nombre,
        )

        # --- Matriz PTR: definición del riesgo (R-XX, P, I, score, tratamiento base) ---
        df_matriz = leer_hoja(path, "Matriz PTR", header_row=1,
                               filtro_col="ID", filtro_regex=r"^R-\d+$")

        # --- Plan de Acción: plazo/herramienta/estado operativo, agrupado por fase ---
        df_accion_raw = pd.read_excel(path, sheet_name="Plan de Acción", header=1).dropna(how="all")
        fase_actual = "FASE_1"
        filas_accion = []
        for _, row in df_accion_raw.iterrows():
            id_val = s(row.get("ID"))
            m = re.match(r"^FASE\s+(\d+)", id_val, re.IGNORECASE)
            if m:
                fase_actual = f"FASE_{m.group(1)}"
                continue
            if re.match(r"^R-\d+$", id_val or ""):
                row = row.copy()
                row["_fase"] = fase_actual
                filas_accion.append(row)
        df_accion = pd.DataFrame(filas_accion)

        # --- Seguimiento: fecha límite / cierre / % avance ---
        df_seguimiento = leer_hoja(path, "Seguimiento", header_row=1,
                                    filtro_col="ID", filtro_regex=r"^R-\d+$")

        accion_por_id = {s(r["ID"]): r for _, r in df_accion.iterrows()} if not df_accion.empty else {}
        seguimiento_por_id = {s(r["ID"]): r for _, r in df_seguimiento.iterrows()}

        creados, omitidos = 0, []
        for _, row in df_matriz.iterrows():
            id_riesgo = s(row["ID"])
            prob, impacto = to_int(row.get("P")), to_int(row.get("I"))
            if prob is None or impacto is None:
                omitidos.append(id_riesgo)
                continue

            fila_accion = accion_por_id.get(id_riesgo)
            fila_seg = seguimiento_por_id.get(id_riesgo)

            fase_txt = s(row.get("Fase"))
            m = re.search(r"Fase\s*(\d+)", fase_txt, re.IGNORECASE)
            fase = f"FASE_{m.group(1)}" if m else (
                fila_accion["_fase"] if fila_accion is not None else "FASE_1")

            estado_txt = ""
            if fila_accion is not None:
                estado_txt = s(fila_accion.get("Estado"))
            if not estado_txt and fila_seg is not None:
                estado_txt = s(fila_seg.get("Estado"))

            porcentaje = 0
            if fila_seg is not None:
                porcentaje = to_int(fila_seg.get("% Avance")) or 0

            fecha_cierre = None
            if fila_seg is not None:
                fc = fila_seg.get("Fecha cierre real")
                if fc is not None and not pd.isna(fc):
                    try:
                        fecha_cierre = pd.to_datetime(fc).date()
                    except Exception:
                        fecha_cierre = None

            self._guardar_protegiendo(
                AccionTratamiento, filtro={"plan": plan, "id_riesgo": id_riesgo},
                defaults=dict(
                    descripcion_riesgo=s(row.get("Descripción del Riesgo")),
                    probabilidad=prob, impacto=impacto,
                    fuente=s(row.get("Fuente")),
                    tecnica_mitre_cwe=s(row.get("Técnica MITRE / CWE")),
                    acciones_tratamiento=s(row.get("Acciones de Tratamiento")),
                    kpi_criterio_cierre=s(row.get("KPI / Criterio de Cierre")) or (
                        s(fila_accion.get("KPI / Criterio de Cierre")) if fila_accion is not None else ""),
                    opcion_tratamiento=OPCION_TRATAMIENTO_MAP.get(norm(row.get("Opción")), "MITIGAR"),
                    responsable=s(row.get("Responsable")) or "Administrador",
                    fase=fase,
                    plazo=s(fila_accion.get("Plazo")) if fila_accion is not None else "",
                    herramienta_comando=s(fila_accion.get("Herramienta / Comando clave"))
                        if fila_accion is not None else "",
                    control_iso27001=s(row.get("Control ISO 27001")),
                    estado=ESTADO_MAP.get(norm(estado_txt), "PENDIENTE"),
                    fecha_limite_texto=s(fila_seg.get("Fecha límite")) if fila_seg is not None else "",
                    fecha_cierre_real=fecha_cierre,
                    porcentaje_avance=porcentaje,
                ),
                descripcion=f"{plan.referencia} · {id_riesgo}",
            )
            creados += 1

        self.stdout.write(f"  · Acciones de tratamiento: {creados} fila(s) del Excel leídas")
        if omitidos:
            self.stderr.write(self.style.WARNING(
                "  ⚠ Se omitieron por no tener P/I definido en 'Matriz PTR' (referenciados solo en "
                f"'Plan de Acción', probablemente de otro registro de riesgos): {', '.join(omitidos)}"))
