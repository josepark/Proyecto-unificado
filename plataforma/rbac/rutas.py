#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUIIN-RBAC — rutas de negocio (matriz, roles, sistemas, usuarios,
auditoría y exportaciones). Se registran sobre la aplicación para conservar
los nombres de endpoint que usan las plantillas."""
import csv
import io
import sqlite3
from datetime import datetime

from flask import (abort, flash, jsonify, redirect, render_template, request,
                   Response, url_for)

from db import audit, db, verificar_cadena

ESTADOS_USUARIO = ("Activo", "Temporal", "Suspendido", "Revocado")
RIESGOS_ATTACK = ("Alto", "Medio", "Bajo")
CLASIFICACIONES = ("Altamente Confidencial", "Confidencial", "Interna", "Pública")
DIAS_ALERTA_VENCIMIENTO = 7

# Certificación periódica de accesos (control 5.18 / POL-SI-002): cuántos
# días equivale cada periodicidad declarada en rol.revision_periodica.
DIAS_REVISION = {"Mensual": 30, "Trimestral": 90, "Semestral": 180, "Anual": 365}
_CASE_DIAS_REVISION = " ".join(
    f"WHEN '{k}' THEN {v}" for k, v in DIAS_REVISION.items())
SQL_REVISION_VENCIDA = f"""CASE
    WHEN r.ultima_revision IS NULL THEN 1
    WHEN date(r.ultima_revision, '+' ||
         (CASE r.revision_periodica {_CASE_DIAS_REVISION} ELSE 90 END) ||
         ' days') < date('now') THEN 1
    ELSE 0 END"""


# ---------------------------------------------------------------- utilidades
def _entero(valor, nombre):
    """Convierte a int con mensaje claro; None si el valor es inválido."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        flash(f"Valor inválido para «{nombre}».", "warn")
        return None


def _fecha_valida(txt):
    if not txt:
        return True
    try:
        datetime.strptime(txt, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validar_datos_rol(f, c):
    """Valida el formulario de alta/edición de rol. Devuelve (datos, error)."""
    codigo = f.get("codigo", "").strip()
    abreviatura = f.get("abreviatura", "").strip().upper()
    denominacion = f.get("denominacion", "").strip()
    if not codigo or not abreviatura or not denominacion:
        return None, "El código, la abreviatura y la denominación son obligatorios."
    try:
        grupo_id = int(f.get("grupo_id"))
    except (TypeError, ValueError):
        return None, "Seleccione un grupo de rol válido."
    if not c.execute("SELECT 1 FROM grupo_rol WHERE id=?", (grupo_id,)).fetchone():
        return None, "Seleccione un grupo de rol válido."
    riesgo = f.get("riesgo_attack", "")
    if riesgo not in RIESGOS_ATTACK:
        return None, "Seleccione un nivel de riesgo ATT&CK válido (Alto/Medio/Bajo)."
    mfa = f.get("mfa_requerido", "").strip()
    revision = f.get("revision_periodica", "").strip()
    if not mfa or not revision:
        return None, "El requisito de MFA y la periodicidad de revisión son obligatorios."
    return {
        "codigo": codigo, "abreviatura": abreviatura, "denominacion": denominacion,
        "grupo_id": grupo_id, "cosecha": f.get("cosecha", "").strip(),
        "en_det7": 1 if f.get("en_det7") == "1" else 0,
        "funcion": f.get("funcion", "").strip(), "mfa_requerido": mfa,
        "riesgo_attack": riesgo, "revision_periodica": revision,
        "observaciones": f.get("observaciones", "").strip(),
    }, None


def _validar_datos_sistema(f, c):
    """Valida el formulario de alta/edición de sistema. Devuelve (datos, error)."""
    nombre = f.get("nombre", "").strip()
    if not nombre:
        return None, "El nombre del sistema o recurso es obligatorio."
    clasificacion = f.get("clasificacion", "")
    if clasificacion not in CLASIFICACIONES:
        return None, "Seleccione una clasificación válida."
    cat_nueva = f.get("categoria_nueva", "").strip()
    if cat_nueva:
        fila = c.execute("SELECT id FROM categoria_sistema WHERE nombre=?",
                         (cat_nueva,)).fetchone()
        cat_id = fila["id"] if fila else c.execute(
            "INSERT INTO categoria_sistema (nombre) VALUES (?)",
            (cat_nueva,)).lastrowid
    else:
        try:
            cat_id = int(f.get("categoria_id"))
        except (TypeError, ValueError):
            return None, "Seleccione una categoría válida o indique una nueva."
        if not c.execute("SELECT 1 FROM categoria_sistema WHERE id=?",
                         (cat_id,)).fetchone():
            return None, "Seleccione una categoría válida o indique una nueva."

    tecnicas_raw = f.get("tecnicas_attack", "").strip()
    codigos = [t.strip().upper() for t in tecnicas_raw.split("/") if t.strip()]
    if codigos:
        reconocidos = {r["id"] for r in c.execute(
            "SELECT id FROM attack_tecnica WHERE id IN (%s)"
            % ",".join("?" * len(codigos)), codigos)}
        desconocidos = [cod for cod in codigos if cod not in reconocidos]
        if desconocidos:
            return None, (f"Técnica(s) ATT&CK no reconocida(s) del catálogo: "
                          f"{', '.join(desconocidos)}.")
    tecnicas_attack = "/".join(codigos)

    return {
        "nombre": nombre, "categoria_id": cat_id, "clasificacion": clasificacion,
        "tecnicas_attack": tecnicas_attack,
    }, None


def registrar(app):

    # ---------------------------------------------------------------- inicio
    @app.route("/")
    def inicio():
        c = db()
        stats = {
            "roles": c.execute("SELECT COUNT(*) n FROM rol").fetchone()["n"],
            "sistemas": c.execute("SELECT COUNT(*) n FROM sistema").fetchone()["n"],
            "usuarios": c.execute(
                "SELECT COUNT(*) n FROM usuario WHERE estado IN ('Activo','Temporal')"
            ).fetchone()["n"],
            "accesos": c.execute(
                "SELECT COUNT(*) n FROM matriz_acceso WHERE nivel_codigo<>'—'"
            ).fetchone()["n"],
        }
        alertas_mfa = c.execute("SELECT * FROM v_alertas_mfa").fetchall()
        criticos = c.execute(
            """SELECT r.abreviatura, r.denominacion, COUNT(*) n_admin
               FROM matriz_acceso ma JOIN rol r ON r.id = ma.rol_id
               WHERE ma.nivel_codigo='A'
               GROUP BY r.id ORDER BY n_admin DESC"""
        ).fetchall()
        temporales = c.execute(
            "SELECT u.nombre, r.abreviatura rol, u.fecha_fin FROM usuario u "
            "JOIN rol r ON r.id=u.rol_id WHERE u.estado='Temporal'"
        ).fetchall()
        revocados = c.execute(
            "SELECT u.nombre, r.abreviatura rol, u.notas FROM usuario u "
            "JOIN rol r ON r.id=u.rol_id WHERE u.estado='Revocado'"
        ).fetchall()
        log = c.execute(
            "SELECT * FROM log_auditoria ORDER BY id DESC LIMIT 8").fetchall()

        # ---- datos para el panel de gráficos (sin dependencias externas) ----
        riesgo_roles = {r["riesgo_attack"]: r["n"] for r in c.execute(
            """SELECT riesgo_attack, COUNT(*) n FROM rol
               WHERE activo=1 GROUP BY riesgo_attack""")}
        riesgo = [
            ("Alto", riesgo_roles.get("Alto", 0), "var(--niv-a)"),
            ("Medio", riesgo_roles.get("Medio", 0), "var(--alerta)"),
            ("Bajo", riesgo_roles.get("Bajo", 0), "var(--niv-l)"),
        ]
        max_riesgo = max((n for _, n, _ in riesgo), default=0) or 1

        mfa_total = c.execute(
            "SELECT COUNT(*) n FROM usuario u JOIN rol r ON r.id=u.rol_id "
            "WHERE u.estado IN ('Activo','Temporal') AND r.mfa_requerido "
            "LIKE 'Sí%'").fetchone()["n"]
        mfa_ok = mfa_total - len(alertas_mfa)
        mfa_pct = round(100 * mfa_ok / mfa_total) if mfa_total else 100

        # ---- alertas preventivas: lo que vence en los próximos N días ----
        proximos_vencimientos = c.execute(
            """SELECT 'Usuario temporal' tipo, u.nombre nombre,
                      r.abreviatura contexto, u.fecha_fin,
                      CAST(julianday(u.fecha_fin) - julianday('now','localtime')
                           AS INTEGER) dias
               FROM usuario u JOIN rol r ON r.id=u.rol_id
               WHERE u.estado='Temporal' AND u.fecha_fin IS NOT NULL
                 AND date(u.fecha_fin) BETWEEN date('now','localtime')
                                            AND date('now','localtime',?)
               UNION ALL
               SELECT 'Excepción de acceso' tipo, us.nombre nombre,
                      s.nombre contexto, e.fecha_fin,
                      CAST(julianday(e.fecha_fin) - julianday('now','localtime')
                           AS INTEGER) dias
               FROM acceso_excepcion e
               JOIN usuario us ON us.id=e.usuario_id
               JOIN sistema s ON s.id=e.sistema_id
               WHERE e.fecha_fin IS NOT NULL
                 AND date(e.fecha_fin) BETWEEN date('now','localtime')
                                            AND date('now','localtime',?)
               ORDER BY fecha_fin""",
            (f"+{DIAS_ALERTA_VENCIMIENTO} days", f"+{DIAS_ALERTA_VENCIMIENTO} days")
        ).fetchall()

        return render_template("inicio.html", stats=stats, alertas=alertas_mfa,
                               criticos=criticos, temporales=temporales,
                               revocados=revocados, log=log, riesgo=riesgo,
                               max_riesgo=max_riesgo, mfa_pct=mfa_pct,
                               mfa_ok=mfa_ok, mfa_total=mfa_total,
                               proximos_vencimientos=proximos_vencimientos,
                               dias_alerta=DIAS_ALERTA_VENCIMIENTO)

    # --------------------------------------------------- sistemas (API)
    @app.route("/api/sistemas")
    def api_sistemas():
        """Catálogo de sistemas de la matriz MCA con sus accesos por rol,
        en JSON. Despliegue integrado: es la fuente canónica que el
        Inventario consulta en vivo (server-a-server) para mostrar, en la
        ficha de cada Sistema de información, los accesos reales según
        RBAC — en vez de depender únicamente de su propia copia
        (RolMCA/AccesoRol), que se llena a mano y puede desactualizarse.

        También sirve de listado para la pantalla Sistemas de React (Fase
        3): admite los mismos filtros que ya tenía la vista HTML
        (q, categoria, clasificacion, estado/incluir_inactivos) y agrega
        categoria_id, tecnicas_attack, activo y n_roles — todos campos
        nuevos que un consumidor existente simplemente ignora, así que no
        hay riesgo de romper la integración ya probada con el Inventario.
        """
        c = db()
        q = request.args.get("q", "").strip()
        categoria_f = request.args.get("categoria", "")
        clasif_f = request.args.get("clasificacion", "")
        incluir_inactivos = request.args.get("incluir_inactivos") == "1"

        sql = """SELECT s.*, cs.nombre categoria,
                        SUM(CASE WHEN ma.nivel_codigo<>'—' THEN 1 ELSE 0 END) n_roles
                 FROM sistema s
                 JOIN categoria_sistema cs ON cs.id = s.categoria_id
                 LEFT JOIN matriz_acceso ma ON ma.sistema_id = s.id
                 WHERE 1=1"""
        p = []
        if not incluir_inactivos:
            sql += " AND s.activo = 1"
        if q:
            sql += " AND s.nombre LIKE ?"
            p.append(f"%{q}%")
        if categoria_f:
            sql += " AND s.categoria_id = ?"
            p.append(categoria_f)
        if clasif_f in CLASIFICACIONES:
            sql += " AND s.clasificacion = ?"
            p.append(clasif_f)
        sql += " GROUP BY s.id ORDER BY s.id"
        sistemas = c.execute(sql, p).fetchall()

        accesos = c.execute(
            """SELECT ma.sistema_id, r.abreviatura rol, r.denominacion,
                      ma.nivel_codigo nivel
               FROM matriz_acceso ma
               JOIN rol r ON r.id = ma.rol_id
               WHERE ma.nivel_codigo <> '—' AND r.activo = 1"""
        ).fetchall()
        por_sistema = {}
        for a in accesos:
            por_sistema.setdefault(a["sistema_id"], []).append(
                {"rol": a["rol"], "denominacion": a["denominacion"],
                 "nivel": a["nivel"]})
        excepciones_vigentes = dict(c.execute(
            """SELECT sistema_id, COUNT(*) n FROM acceso_excepcion
               WHERE fecha_fin IS NULL OR date(fecha_fin) >= date('now')
               GROUP BY sistema_id"""
        ).fetchall())
        return jsonify([
            {"id": s["id"], "nombre": s["nombre"], "categoria": s["categoria"],
             "categoria_id": s["categoria_id"], "clasificacion": s["clasificacion"],
             "tecnicas_attack": s["tecnicas_attack"], "activo": bool(s["activo"]),
             "n_roles": s["n_roles"],
             "accesos": por_sistema.get(s["id"], []),
             "excepciones_vigentes": excepciones_vigentes.get(s["id"], 0)}
            for s in sistemas
        ])

    # ------------------------------------------------------ resumen (API)
    @app.route("/api/resumen")
    def api_resumen():
        """KPIs de RBAC en JSON, sin las filas de detalle. Despliegue
        integrado: el Inventario lo consume para el badge de pendientes de
        su pestaña "Matriz RBAC" y para el Panel ejecutivo consolidado
        (ver dashboard_ejecutivo() en inventario/views.py). Reutiliza
        exactamente las mismas consultas que ya usa Inicio, para no tener
        una segunda definición de "qué cuenta como vencido"."""
        c = db()
        roles_total = c.execute(
            "SELECT COUNT(*) n FROM rol WHERE activo=1").fetchone()["n"]
        sistemas_total = c.execute(
            "SELECT COUNT(*) n FROM sistema WHERE activo=1").fetchone()["n"]
        usuarios_activos = c.execute(
            "SELECT COUNT(*) n FROM usuario WHERE estado IN ('Activo','Temporal')"
        ).fetchone()["n"]

        alertas_mfa = c.execute("SELECT COUNT(*) n FROM v_alertas_mfa").fetchone()["n"]
        mfa_total = c.execute(
            "SELECT COUNT(*) n FROM usuario u JOIN rol r ON r.id=u.rol_id "
            "WHERE u.estado IN ('Activo','Temporal') AND r.mfa_requerido "
            "LIKE 'Sí%'").fetchone()["n"]
        mfa_ok = mfa_total - alertas_mfa
        mfa_pct = round(100 * mfa_ok / mfa_total) if mfa_total else 100

        proximos_vencimientos = c.execute(
            """SELECT COUNT(*) n FROM (
                 SELECT u.id FROM usuario u
                 WHERE u.estado='Temporal' AND u.fecha_fin IS NOT NULL
                   AND date(u.fecha_fin) BETWEEN date('now','localtime')
                                              AND date('now','localtime',?)
                 UNION ALL
                 SELECT e.usuario_id FROM acceso_excepcion e
                 WHERE e.fecha_fin IS NOT NULL
                   AND date(e.fecha_fin) BETWEEN date('now','localtime')
                                              AND date('now','localtime',?))""",
            (f"+{DIAS_ALERTA_VENCIMIENTO} days", f"+{DIAS_ALERTA_VENCIMIENTO} days")
        ).fetchone()["n"]

        excepciones_vigentes = c.execute(
            "SELECT COUNT(*) n FROM acceso_excepcion "
            "WHERE fecha_fin IS NULL OR date(fecha_fin) >= date('now')"
        ).fetchone()["n"]
        excepciones_vencidas = c.execute(
            "SELECT COUNT(*) n FROM acceso_excepcion "
            "WHERE fecha_fin IS NOT NULL AND date(fecha_fin) < date('now')"
        ).fetchone()["n"]

        roles_certificacion_vencida = c.execute(
            f"SELECT COUNT(*) n FROM rol r WHERE r.activo=1 "
            f"AND {SQL_REVISION_VENCIDA} = 1").fetchone()["n"]

        pendientes_total = (proximos_vencimientos + excepciones_vencidas
                            + roles_certificacion_vencida)

        return jsonify({
            "roles_total": roles_total,
            "sistemas_total": sistemas_total,
            "usuarios_activos": usuarios_activos,
            "mfa_pct": mfa_pct, "mfa_ok": mfa_ok, "mfa_total": mfa_total,
            "proximos_vencimientos": proximos_vencimientos,
            "excepciones_vigentes": excepciones_vigentes,
            "excepciones_vencidas": excepciones_vencidas,
            "roles_certificacion_vencida": roles_certificacion_vencida,
            "pendientes_total": pendientes_total,
        })


    # ---------------------------------------------------------------- matriz
    @app.route("/matriz")
    def matriz():
        c = db()
        grupo = request.args.get("grupo", "")
        categoria = request.args.get("categoria", "")

        q_rol = ("SELECT r.*, g.nombre grupo, g.codigo gcod FROM rol r "
                 "JOIN grupo_rol g ON g.id=r.grupo_id WHERE r.activo=1")
        p = []
        if grupo:
            q_rol += " AND g.codigo=?"
            p.append(grupo)
        roles = c.execute(q_rol + " ORDER BY r.id", p).fetchall()

        q_sis = ("SELECT s.*, c.nombre categoria FROM sistema s "
                 "JOIN categoria_sistema c ON c.id=s.categoria_id WHERE s.activo=1")
        p2 = []
        if categoria:
            q_sis += " AND c.nombre=?"
            p2.append(categoria)
        sistemas = c.execute(q_sis + " ORDER BY s.id", p2).fetchall()

        celdas = {(m["rol_id"], m["sistema_id"]): m["nivel_codigo"]
                  for m in c.execute("SELECT * FROM matriz_acceso")}
        grupos = c.execute("SELECT * FROM grupo_rol ORDER BY id").fetchall()
        categorias = c.execute(
            "SELECT * FROM categoria_sistema ORDER BY id").fetchall()
        niveles = c.execute(
            "SELECT * FROM nivel_acceso ORDER BY orden").fetchall()
        return render_template("matriz.html", roles=roles, sistemas=sistemas,
                               celdas=celdas, grupos=grupos, categorias=categorias,
                               niveles=niveles, f_grupo=grupo, f_cat=categoria)


    @app.route("/matriz/editar", methods=["POST"])
    def matriz_editar():
        c = db()
        es_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        def salir(mensaje=None, categoria=None, **extra):
            if es_ajax:
                cuerpo = {"ok": categoria != "warn"}
                if mensaje:
                    cuerpo["mensaje"] = mensaje
                cuerpo.update(extra)
                return jsonify(cuerpo), (200 if cuerpo["ok"] else 400)
            if mensaje:
                flash(mensaje, categoria)
            return redirect(request.referrer or url_for("matriz"))

        rol_id = _entero(request.form.get("rol_id"), "rol")
        sistema_id = _entero(request.form.get("sistema_id"), "sistema")
        nivel = request.form.get("nivel", "")
        if rol_id is None or sistema_id is None:
            return salir("Rol o sistema inválido.", "warn")
        nivel_ok = c.execute(
            "SELECT 1 FROM nivel_acceso WHERE codigo=?", (nivel,)).fetchone()
        if not nivel_ok:
            return salir("Nivel de acceso no reconocido; no se aplicó "
                         "ningún cambio.", "warn")
        rol = c.execute("SELECT abreviatura FROM rol WHERE id=?",
                        (rol_id,)).fetchone()
        sis = c.execute("SELECT nombre FROM sistema WHERE id=?",
                        (sistema_id,)).fetchone()
        if not rol or not sis:
            return salir("Rol o sistema no encontrado; no se aplicó "
                         "ningún cambio.", "warn")
        prev = c.execute(
            "SELECT nivel_codigo FROM matriz_acceso WHERE rol_id=? AND sistema_id=?",
            (rol_id, sistema_id)).fetchone()
        anterior = prev["nivel_codigo"] if prev else "—"
        c.execute(
            "UPDATE matriz_acceso SET nivel_codigo=? WHERE rol_id=? AND sistema_id=?",
            (nivel, rol_id, sistema_id))
        c.commit()
        audit("matriz_acceso", "MODIFICACION",
              f"{rol['abreviatura']} × {sis['nombre']}: {anterior} → {nivel}")
        return salir(
            f"Acceso actualizado: {rol['abreviatura']} sobre «{sis['nombre']}» "
            f"ahora es {nivel}.",
            rol_id=rol_id, sistema_id=sistema_id, rol=rol["abreviatura"],
            sistema=sis["nombre"], anterior=anterior, nuevo=nivel)


    @app.route("/matriz/importar", methods=["GET", "POST"])
    def matriz_importar():
        if request.method == "GET":
            return render_template("matriz_importar.html", cambios=None, errores=None)

        c = db()
        archivo = request.files.get("archivo")
        if not archivo or not archivo.filename:
            flash("Seleccione un archivo CSV para importar.", "warn")
            return redirect(url_for("matriz_importar"))
        try:
            texto = archivo.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            flash("No se pudo leer el archivo: use la codificación UTF-8 (el "
                  "mismo formato que genera «Exportar matriz»).", "warn")
            return redirect(url_for("matriz_importar"))

        filas_csv = list(csv.reader(io.StringIO(texto), delimiter=";"))
        if not filas_csv:
            flash("El archivo está vacío.", "warn")
            return redirect(url_for("matriz_importar"))

        encabezado, datos = filas_csv[0], filas_csv[1:]
        roles_por_abrev = {r["abreviatura"]: r["id"] for r in
                           c.execute("SELECT id, abreviatura FROM rol WHERE activo=1")}
        sistemas_por_nombre = {s["nombre"]: s["id"] for s in
                               c.execute("SELECT id, nombre FROM sistema WHERE activo=1")}
        niveles_validos = {n["codigo"] for n in
                           c.execute("SELECT codigo FROM nivel_acceso")}
        actuales = {(m["rol_id"], m["sistema_id"]): m["nivel_codigo"]
                   for m in c.execute("SELECT * FROM matriz_acceso")}

        columnas, errores = [], []
        for i, abrev in enumerate(encabezado[1:], start=1):
            abrev = abrev.strip()
            if abrev in roles_por_abrev:
                columnas.append((i, roles_por_abrev[abrev], abrev))
            else:
                errores.append(f"Columna «{abrev}»: no coincide con ningún rol "
                              "activo; se ignoró toda la columna.")

        cambios = []
        for fila in datos:
            if not fila or not fila[0].strip():
                continue
            nombre_sis = fila[0].strip()
            sid = sistemas_por_nombre.get(nombre_sis)
            if sid is None:
                errores.append(f"Sistema «{nombre_sis}»: no coincide con ningún "
                              "sistema activo; se ignoró la fila.")
                continue
            for i, rid, abrev in columnas:
                if i >= len(fila):
                    continue
                nivel = fila[i].strip()
                if not nivel:
                    continue
                if nivel not in niveles_validos:
                    errores.append(f"«{nombre_sis}» × {abrev}: valor «{nivel}» "
                                  "no es un nivel válido; se ignoró esa celda.")
                    continue
                actual = actuales.get((rid, sid), "—")
                if nivel != actual:
                    cambios.append({"rol_id": rid, "rol": abrev, "sistema_id": sid,
                                    "sistema": nombre_sis, "actual": actual,
                                    "nuevo": nivel})

        if len(errores) > 50:
            errores = errores[:50] + [f"… y {len(errores) - 50} advertencia(s) más."]
        return render_template("matriz_importar.html", cambios=cambios, errores=errores)


    @app.route("/matriz/importar/confirmar", methods=["POST"])
    def matriz_importar_confirmar():
        c = db()
        n = _entero(request.form.get("n"), "cantidad de cambios") or 0
        aplicados, detalle_partes = 0, []
        for i in range(n):
            rid = _entero(request.form.get(f"c{i}_rol"), "rol")
            sid = _entero(request.form.get(f"c{i}_sistema"), "sistema")
            nivel = request.form.get(f"c{i}_nivel", "")
            if rid is None or sid is None:
                continue
            if not c.execute("SELECT 1 FROM nivel_acceso WHERE codigo=?",
                             (nivel,)).fetchone():
                continue
            rol = c.execute("SELECT abreviatura FROM rol WHERE id=?", (rid,)).fetchone()
            sis = c.execute("SELECT nombre FROM sistema WHERE id=?", (sid,)).fetchone()
            if not rol or not sis:
                continue
            c.execute("UPDATE matriz_acceso SET nivel_codigo=? "
                      "WHERE rol_id=? AND sistema_id=?", (nivel, rid, sid))
            aplicados += 1
            if len(detalle_partes) < 30:
                detalle_partes.append(f"{rol['abreviatura']}×{sis['nombre']}→{nivel}")
        c.commit()
        if aplicados:
            detalle = f"Importación CSV: {aplicados} cambio(s) aplicado(s): " + \
                "; ".join(detalle_partes)
            if aplicados > len(detalle_partes):
                detalle += f"; … y {aplicados - len(detalle_partes)} más."
            audit("matriz_acceso", "IMPORTACION", detalle)
            flash(f"Importación aplicada: {aplicados} cambio(s) en la matriz.")
        else:
            flash("No se aplicó ningún cambio.", "warn")
        return redirect(url_for("matriz"))


    @app.route("/matriz/comparar")
    def matriz_comparar():
        c = db()
        rol_a_id = _entero(request.args.get("rol_a"), "rol A") \
            if request.args.get("rol_a") else None
        rol_b_id = _entero(request.args.get("rol_b"), "rol B") \
            if request.args.get("rol_b") else None
        roles = c.execute(
            "SELECT id, abreviatura, denominacion FROM rol WHERE activo=1 "
            "ORDER BY abreviatura").fetchall()

        rol_a = rol_b = None
        filas = []
        if rol_a_id and rol_b_id:
            rol_a = c.execute("SELECT abreviatura, denominacion FROM rol WHERE id=?",
                              (rol_a_id,)).fetchone()
            rol_b = c.execute("SELECT abreviatura, denominacion FROM rol WHERE id=?",
                              (rol_b_id,)).fetchone()
            if rol_a and rol_b:
                niveles_a = {m["sistema_id"]: m["nivel_codigo"] for m in c.execute(
                    "SELECT sistema_id, nivel_codigo FROM matriz_acceso "
                    "WHERE rol_id=?", (rol_a_id,))}
                niveles_b = {m["sistema_id"]: m["nivel_codigo"] for m in c.execute(
                    "SELECT sistema_id, nivel_codigo FROM matriz_acceso "
                    "WHERE rol_id=?", (rol_b_id,))}
                sistemas = c.execute(
                    """SELECT s.id, s.nombre, cat.nombre categoria FROM sistema s
                       JOIN categoria_sistema cat ON cat.id=s.categoria_id
                       WHERE s.activo=1 ORDER BY cat.nombre, s.nombre""").fetchall()
                for s in sistemas:
                    na = niveles_a.get(s["id"], "—")
                    nb = niveles_b.get(s["id"], "—")
                    filas.append({"sistema": s["nombre"], "categoria": s["categoria"],
                                  "nivel_a": na, "nivel_b": nb, "difiere": na != nb})
            else:
                flash("Uno de los roles seleccionados ya no existe.", "warn")

        return render_template("matriz_comparar.html", roles=roles, filas=filas,
                               rol_a=rol_a, rol_b=rol_b, rol_a_id=rol_a_id,
                               rol_b_id=rol_b_id)


    # ---------------------------------------------------------------- roles
    @app.route("/roles")
    def roles():
        c = db()
        q = request.args.get("q", "").strip()
        grupo_f = _entero(request.args.get("grupo", ""), "grupo") \
            if request.args.get("grupo") else None
        riesgo_f = request.args.get("riesgo", "")
        estado_f = request.args.get("estado", "")

        sql = f"""SELECT r.*, g.nombre grupo,
                      SUM(CASE WHEN ma.nivel_codigo='A' THEN 1 ELSE 0 END) n_admin,
                      SUM(CASE WHEN ma.nivel_codigo<>'—' THEN 1 ELSE 0 END) n_accesos,
                      {SQL_REVISION_VENCIDA} revision_vencida
               FROM rol r JOIN grupo_rol g ON g.id=r.grupo_id
               LEFT JOIN matriz_acceso ma ON ma.rol_id=r.id
               WHERE 1=1"""
        p = []
        if q:
            sql += " AND (r.abreviatura LIKE ? OR r.denominacion LIKE ? OR r.codigo LIKE ?)"
            p += [f"%{q}%", f"%{q}%", f"%{q}%"]
        if grupo_f is not None:
            sql += " AND r.grupo_id=?"
            p.append(grupo_f)
        if riesgo_f in RIESGOS_ATTACK:
            sql += " AND r.riesgo_attack=?"
            p.append(riesgo_f)
        if estado_f == "Activo":
            sql += " AND r.activo=1"
        elif estado_f == "Desactivado":
            sql += " AND r.activo=0"
        sql += " GROUP BY r.id ORDER BY r.id"
        filas = c.execute(sql, p).fetchall()
        grupos = c.execute("SELECT * FROM grupo_rol ORDER BY id").fetchall()
        roles_todos = c.execute(
            "SELECT id, abreviatura, denominacion FROM rol WHERE activo=1 "
            "ORDER BY abreviatura").fetchall()
        return render_template("roles.html", roles=filas, grupos=grupos,
                               roles_todos=roles_todos,
                               f_q=q, f_grupo=grupo_f, f_riesgo=riesgo_f,
                               f_estado=estado_f, riesgos=RIESGOS_ATTACK)


    @app.route("/roles/<int:rid>")
    def rol_detalle(rid):
        c = db()
        rol = c.execute(
            f"SELECT r.*, g.nombre grupo, {SQL_REVISION_VENCIDA} revision_vencida "
            "FROM rol r JOIN grupo_rol g ON g.id=r.grupo_id WHERE r.id=?",
            (rid,)).fetchone()
        if not rol:
            abort(404)
        accesos = c.execute(
            """SELECT s.nombre, s.clasificacion, cat.nombre categoria,
                      ma.nivel_codigo nivel, n.nombre nivel_nombre
               FROM matriz_acceso ma
               JOIN sistema s ON s.id=ma.sistema_id
               JOIN categoria_sistema cat ON cat.id=s.categoria_id
               JOIN nivel_acceso n ON n.codigo=ma.nivel_codigo
               WHERE ma.rol_id=? AND ma.nivel_codigo<>'—'
               ORDER BY n.orden, s.id""", (rid,)).fetchall()
        usuarios = c.execute(
            "SELECT * FROM usuario WHERE rol_id=? ORDER BY estado, nombre",
            (rid,)).fetchall()
        grupos = c.execute("SELECT * FROM grupo_rol ORDER BY id").fetchall()
        return render_template("rol_detalle.html", rol=rol, accesos=accesos,
                               usuarios=usuarios, grupos=grupos)



    @app.route("/roles/crear", methods=["POST"])
    def rol_crear():
        f = request.form
        c = db()
        datos, error = _validar_datos_rol(f, c)
        if error:
            flash(error, "warn")
            return redirect(url_for("roles"))

        clonar_de = None
        clonar_raw = f.get("clonar_de", "").strip()
        rol_origen = None
        if clonar_raw:
            clonar_de = _entero(clonar_raw, "rol a clonar")
            if clonar_de is not None:
                rol_origen = c.execute("SELECT abreviatura FROM rol WHERE id=?",
                                       (clonar_de,)).fetchone()
                if not rol_origen:
                    flash("El rol elegido para clonar ya no existe.", "warn")
                    return redirect(url_for("roles"))

        try:
            cur = c.execute(
                """INSERT INTO rol (codigo, abreviatura, denominacion, grupo_id, cosecha,
                                    en_det7, funcion, mfa_requerido, riesgo_attack,
                                    revision_periodica, observaciones)
                   VALUES (:codigo,:abreviatura,:denominacion,:grupo_id,:cosecha,
                           :en_det7,:funcion,:mfa_requerido,:riesgo_attack,
                           :revision_periodica,:observaciones)""", datos)
        except sqlite3.IntegrityError:
            flash("Ya existe un rol con ese código o abreviatura.", "warn")
            return redirect(url_for("roles"))
        rid_nuevo = cur.lastrowid
        # Inicializar la matriz del nuevo rol: copia del rol de origen si se
        # indicó uno, o '—' (sin accesos) en caso contrario.
        c.execute(
            """INSERT INTO matriz_acceso (rol_id, sistema_id, nivel_codigo)
               SELECT ?, s.id, COALESCE(origen.nivel_codigo, '—')
               FROM sistema s
               LEFT JOIN matriz_acceso origen
                      ON origen.sistema_id = s.id AND origen.rol_id = ?""",
            (rid_nuevo, clonar_de))
        c.commit()
        origen_txt = (f"clonando los accesos de {rol_origen['abreviatura']}"
                     if rol_origen else "sin accesos")
        audit("rol", "ALTA",
              f"Rol {datos['abreviatura']} ({datos['denominacion']}) "
              f"creado. Matriz inicializada {origen_txt}.")
        flash(f"Rol «{datos['abreviatura']}» creado "
              f"({'accesos copiados de ' + rol_origen['abreviatura'] if rol_origen else 'sin accesos'}). "
              "Revíselos en la Matriz.")
        return redirect(url_for("rol_detalle", rid=rid_nuevo))


    @app.route("/roles/<int:rid>/editar", methods=["POST"])
    def rol_editar(rid):
        f = request.form
        c = db()
        datos, error = _validar_datos_rol(f, c)
        if error:
            flash(error, "warn")
            return redirect(url_for("rol_detalle", rid=rid))
        try:
            c.execute(
                """UPDATE rol SET codigo=:codigo, abreviatura=:abreviatura,
                                  denominacion=:denominacion, grupo_id=:grupo_id,
                                  cosecha=:cosecha, en_det7=:en_det7,
                                  funcion=:funcion, mfa_requerido=:mfa_requerido,
                                  riesgo_attack=:riesgo_attack,
                                  revision_periodica=:revision_periodica,
                                  observaciones=:observaciones
                   WHERE id=:id""", {**datos, "id": rid})
        except sqlite3.IntegrityError:
            flash("Ya existe otro rol con ese código o abreviatura.", "warn")
            return redirect(url_for("rol_detalle", rid=rid))
        c.commit()
        audit("rol", "MODIFICACION",
              f"Rol {datos['abreviatura']} (id {rid}) actualizado.")
        flash("Rol actualizado.")
        return redirect(url_for("rol_detalle", rid=rid))


    @app.route("/roles/<int:rid>/revisar", methods=["POST"])
    def rol_revisar(rid):
        c = db()
        r = c.execute("SELECT abreviatura, denominacion, revision_periodica "
                      "FROM rol WHERE id=?", (rid,)).fetchone()
        if not r:
            flash("Rol no encontrado.", "warn")
            return redirect(url_for("roles"))
        nota = request.form.get("nota", "").strip()
        c.execute("UPDATE rol SET ultima_revision=date('now','localtime') "
                  "WHERE id=?", (rid,))
        c.commit()
        audit("rol", "REVISION",
              f"Rol {r['abreviatura']} ({r['denominacion']}) revisado "
              f"conforme a su periodicidad ({r['revision_periodica']}, "
              "POL-SI-002)." + (f" Nota: {nota}" if nota else ""))
        flash(f"Rol «{r['abreviatura']}» marcado como revisado hoy.")
        return redirect(request.referrer or url_for("rol_detalle", rid=rid))


    @app.route("/roles/<int:rid>/activo", methods=["POST"])
    def rol_activo(rid):
        c = db()
        r = c.execute("SELECT abreviatura, activo FROM rol WHERE id=?",
                      (rid,)).fetchone()
        nuevo = 0 if r["activo"] else 1
        if nuevo == 0:
            n = c.execute(
                "SELECT COUNT(*) n FROM usuario WHERE rol_id=? "
                "AND estado IN ('Activo','Temporal')", (rid,)).fetchone()["n"]
            if n:
                flash(f"No se puede desactivar {r['abreviatura']}: tiene {n} "
                      "usuario(s) activo(s). Reasigne o revoque primero.", "warn")
                return redirect(request.referrer or url_for("roles"))
        c.execute("UPDATE rol SET activo=? WHERE id=?", (nuevo, rid))
        c.commit()
        audit("rol", "MODIFICACION" if nuevo else "REVOCACION",
              f"Rol {r['abreviatura']} " + ("reactivado." if nuevo else
              "desactivado. Se conserva su historial y su fila en la matriz."))
        flash(f"Rol {r['abreviatura']} " + ("reactivado." if nuevo else "desactivado."))
        return redirect(request.referrer or url_for("roles"))



    @app.route("/roles/<int:rid>/eliminar", methods=["POST"])
    def rol_eliminar(rid):
        c = db()
        r = c.execute("SELECT abreviatura, denominacion FROM rol WHERE id=?",
                      (rid,)).fetchone()
        n = c.execute("SELECT COUNT(*) n FROM usuario WHERE rol_id=?",
                      (rid,)).fetchone()["n"]
        if n:
            flash(f"No se puede eliminar {r['abreviatura']}: {n} usuario(s) lo "
                  "referencian (incluidos revocados). Eliminar el rol destruiría "
                  "su trazabilidad — use Desactivar, o elimine antes esos usuarios.",
                  "warn")
            return redirect(request.referrer or url_for("roles"))
        c.execute("DELETE FROM rol WHERE id=?", (rid,))  # matriz_acceso cae en cascada
        c.commit()
        audit("rol", "ELIMINACION",
              f"Rol {r['abreviatura']} ({r['denominacion']}) eliminado "
              "definitivamente junto con su fila de la matriz.")
        flash(f"Rol {r['abreviatura']} eliminado definitivamente.")
        return redirect(url_for("roles"))


    # ---------------------------------------------------------------- sistemas
    @app.route("/sistemas")
    def sistemas():
        c = db()
        q = request.args.get("q", "").strip()
        cat_f = _entero(request.args.get("categoria", ""), "categoría") \
            if request.args.get("categoria") else None
        clasif_f = request.args.get("clasificacion", "")
        estado_f = request.args.get("estado", "")

        sql = """SELECT s.*, c.nombre categoria,
                      SUM(CASE WHEN ma.nivel_codigo<>'—' THEN 1 ELSE 0 END) n_roles
               FROM sistema s JOIN categoria_sistema c ON c.id=s.categoria_id
               LEFT JOIN matriz_acceso ma ON ma.sistema_id=s.id
               WHERE 1=1"""
        p = []
        if q:
            sql += " AND s.nombre LIKE ?"
            p.append(f"%{q}%")
        if cat_f is not None:
            sql += " AND s.categoria_id=?"
            p.append(cat_f)
        if clasif_f in CLASIFICACIONES:
            sql += " AND s.clasificacion=?"
            p.append(clasif_f)
        if estado_f == "Activo":
            sql += " AND s.activo=1"
        elif estado_f == "Desactivado":
            sql += " AND s.activo=0"
        sql += " GROUP BY s.id ORDER BY s.id"
        filas = c.execute(sql, p).fetchall()
        categorias = c.execute(
            "SELECT * FROM categoria_sistema ORDER BY id").fetchall()
        return render_template("sistemas.html", sistemas=filas,
                               categorias=categorias, f_q=q, f_categoria=cat_f,
                               f_clasificacion=clasif_f, f_estado=estado_f,
                               clasificaciones=CLASIFICACIONES)


    @app.route("/sistemas/<int:sid>")
    def sistema_detalle(sid):
        c = db()
        sis = c.execute(
            "SELECT s.*, c.nombre categoria FROM sistema s "
            "JOIN categoria_sistema c ON c.id=s.categoria_id WHERE s.id=?",
            (sid,)).fetchone()
        if not sis:
            abort(404)
        # ¿Quién puede acceder? — roles y usuarios efectivos
        roles_acc = c.execute(
            """SELECT r.id, r.abreviatura, r.denominacion, ma.nivel_codigo nivel,
                      n.nombre nivel_nombre
               FROM matriz_acceso ma
               JOIN rol r ON r.id=ma.rol_id
               JOIN nivel_acceso n ON n.codigo=ma.nivel_codigo
               WHERE ma.sistema_id=? AND ma.nivel_codigo<>'—' AND r.activo=1
               ORDER BY n.orden, r.id""", (sid,)).fetchall()
        usuarios = c.execute(
            """SELECT u.nombre, u.estado, r.abreviatura rol,
                      COALESCE(e.nivel_codigo, ma.nivel_codigo) nivel,
                      CASE WHEN e.usuario_id IS NOT NULL THEN 1 ELSE 0 END
                        es_excepcion
               FROM usuario u
               JOIN rol r ON r.id=u.rol_id
               JOIN matriz_acceso ma ON ma.rol_id=r.id AND ma.sistema_id=?
               LEFT JOIN acceso_excepcion e ON e.usuario_id=u.id
                    AND e.sistema_id=?
                    AND (e.fecha_fin IS NULL OR date(e.fecha_fin) >= date('now'))
               WHERE COALESCE(e.nivel_codigo, ma.nivel_codigo) <> '—'
                 AND u.estado IN ('Activo','Temporal') AND r.activo=1
               ORDER BY u.nombre""", (sid, sid)).fetchall()
        categorias = c.execute(
            "SELECT * FROM categoria_sistema ORDER BY id").fetchall()
        return render_template("sistema_detalle.html", sis=sis,
                               roles=roles_acc, usuarios=usuarios,
                               categorias=categorias)



    @app.route("/sistemas/crear", methods=["POST"])
    def sistema_crear():
        f = request.form
        c = db()
        datos, error = _validar_datos_sistema(f, c)
        if error:
            flash(error, "warn")
            return redirect(url_for("sistemas"))
        try:
            cur = c.execute(
                """INSERT INTO sistema (nombre, categoria_id, clasificacion,
                                        tecnicas_attack)
                   VALUES (:nombre,:categoria_id,:clasificacion,:tecnicas_attack)""",
                datos)
        except sqlite3.IntegrityError:
            flash("Ya existe un sistema con ese nombre.", "warn")
            return redirect(url_for("sistemas"))
        sid_nuevo = cur.lastrowid
        # Inicializar la matriz del nuevo sistema en '—' para todos los roles
        c.execute(
            "INSERT INTO matriz_acceso (rol_id, sistema_id, nivel_codigo) "
            "SELECT id, ?, '—' FROM rol", (sid_nuevo,))
        c.commit()
        audit("sistema", "ALTA",
              f"Sistema «{datos['nombre']}» creado "
              f"({datos['clasificacion']}). Matriz inicializada sin accesos.")
        flash(f"Sistema «{datos['nombre']}» creado. Defina sus accesos en la Matriz.")
        return redirect(url_for("sistema_detalle", sid=sid_nuevo))


    @app.route("/sistemas/<int:sid>/editar", methods=["POST"])
    def sistema_editar(sid):
        f = request.form
        c = db()
        datos, error = _validar_datos_sistema(f, c)
        if error:
            flash(error, "warn")
            return redirect(url_for("sistema_detalle", sid=sid))
        try:
            c.execute(
                """UPDATE sistema SET nombre=:nombre, categoria_id=:categoria_id,
                                      clasificacion=:clasificacion,
                                      tecnicas_attack=:tecnicas_attack
                   WHERE id=:id""", {**datos, "id": sid})
        except sqlite3.IntegrityError:
            flash("Ya existe otro sistema con ese nombre.", "warn")
            return redirect(url_for("sistema_detalle", sid=sid))
        c.commit()
        audit("sistema", "MODIFICACION",
              f"Sistema «{datos['nombre']}» (id {sid}) actualizado.")
        flash("Sistema actualizado.")
        return redirect(url_for("sistema_detalle", sid=sid))


    @app.route("/sistemas/<int:sid>/activo", methods=["POST"])
    def sistema_activo(sid):
        c = db()
        s = c.execute("SELECT nombre, activo FROM sistema WHERE id=?",
                      (sid,)).fetchone()
        nuevo = 0 if s["activo"] else 1
        c.execute("UPDATE sistema SET activo=? WHERE id=?", (nuevo, sid))
        c.commit()
        audit("sistema", "MODIFICACION" if nuevo else "REVOCACION",
              f"Sistema «{s['nombre']}» " + ("reactivado." if nuevo else
              "desactivado. Se conserva su historial y su columna en la matriz."))
        flash(f"Sistema «{s['nombre']}» " + ("reactivado." if nuevo else "desactivado."))
        return redirect(request.referrer or url_for("sistemas"))



    @app.route("/sistemas/<int:sid>/eliminar", methods=["POST"])
    def sistema_eliminar(sid):
        c = db()
        s = c.execute("SELECT nombre FROM sistema WHERE id=?", (sid,)).fetchone()
        n = c.execute("SELECT COUNT(*) n FROM acceso_excepcion WHERE sistema_id=?",
                      (sid,)).fetchone()["n"]
        if n:
            flash(f"No se puede eliminar «{s['nombre']}»: tiene {n} excepción(es) "
                  "de acceso documentada(s) (control 5.18). Eliminarlo destruiría "
                  "esa trazabilidad — use Desactivar, o retire antes esas "
                  "excepciones desde Excepciones.", "warn")
            return redirect(request.referrer or url_for("sistemas"))
        c.execute("DELETE FROM sistema WHERE id=?", (sid,))  # cascada en matriz
        c.commit()
        audit("sistema", "ELIMINACION",
              f"Sistema «{s['nombre']}» eliminado definitivamente junto con su "
              "columna de la matriz.")
        flash(f"Sistema «{s['nombre']}» eliminado definitivamente.")
        return redirect(url_for("sistemas"))


    # ---------------------------------------------------------------- usuarios
    @app.route("/usuarios")
    def usuarios():
        c = db()
        q = request.args.get("q", "").strip()
        estado_f = request.args.get("estado", "")
        rol_f = _entero(request.args.get("rol", ""), "rol") \
            if request.args.get("rol") else None

        sql = """SELECT u.*, r.abreviatura rol, r.denominacion, r.mfa_requerido,
                      (SELECT COUNT(*) FROM v_accesos_usuario v
                       WHERE v.usuario_id = u.id) n_sistemas,
                      (SELECT COUNT(*) FROM acceso_excepcion e
                       WHERE e.usuario_id = u.id) n_excepciones
               FROM usuario u JOIN rol r ON r.id=u.rol_id WHERE 1=1"""
        p = []
        if q:
            sql += " AND (u.nombre LIKE ? OR r.abreviatura LIKE ? OR r.denominacion LIKE ?)"
            p += [f"%{q}%", f"%{q}%", f"%{q}%"]
        if estado_f in ESTADOS_USUARIO:
            sql += " AND u.estado=?"
            p.append(estado_f)
        if rol_f is not None:
            sql += " AND u.rol_id=?"
            p.append(rol_f)
        sql += (" ORDER BY CASE u.estado WHEN 'Activo' THEN 0 WHEN 'Temporal' THEN 1 "
                "WHEN 'Suspendido' THEN 2 ELSE 3 END, u.nombre")
        filas = c.execute(sql, p).fetchall()
        roles_sel = c.execute(
            "SELECT id, abreviatura, denominacion FROM rol WHERE activo=1 ORDER BY id").fetchall()
        return render_template("usuarios.html", usuarios=filas, roles=roles_sel,
                               f_q=q, f_estado=estado_f,
                               f_rol=rol_f, estados=ESTADOS_USUARIO)


    @app.route("/usuarios/crear", methods=["POST"])
    def usuario_crear():
        f = request.form
        c = db()

        nombre = f.get("nombre", "").strip()
        estado = f.get("estado", "Activo")
        rol_id = _entero(f.get("rol_id"), "rol")
        fecha_inicio = f.get("fecha_inicio") or None
        fecha_fin = f.get("fecha_fin") or None

        if not nombre:
            flash("El nombre completo es obligatorio.", "warn")
            return redirect(url_for("usuarios"))
        if rol_id is None:
            return redirect(url_for("usuarios"))
        rol = c.execute("SELECT * FROM rol WHERE id=? AND activo=1",
                        (rol_id,)).fetchone()
        if not rol:
            flash("Seleccione un rol activo válido.", "warn")
            return redirect(url_for("usuarios"))
        if estado not in ESTADOS_USUARIO:
            flash("Estado no reconocido.", "warn")
            return redirect(url_for("usuarios"))
        if not _fecha_valida(fecha_inicio) or not _fecha_valida(fecha_fin):
            flash("Las fechas deben tener el formato AAAA-MM-DD.", "warn")
            return redirect(url_for("usuarios"))
        if estado == "Temporal":
            if not fecha_inicio or not fecha_fin:
                flash("El acceso Temporal requiere fecha de inicio y de fin.",
                      "warn")
                return redirect(url_for("usuarios"))
            if fecha_fin < fecha_inicio:
                flash("La fecha de fin no puede ser anterior a la de inicio.",
                      "warn")
                return redirect(url_for("usuarios"))

        duplicado = c.execute(
            """SELECT r.abreviatura rol FROM usuario u JOIN rol r ON r.id=u.rol_id
               WHERE u.nombre=? AND u.estado IN ('Activo','Temporal')""",
            (nombre,)).fetchone()

        cur = c.execute(
            """INSERT INTO usuario (nombre, rol_id, mfa_activo, nda, estado,
                                    fecha_inicio, fecha_fin, notas)
               VALUES (?,?,?,?,?,?,?,?)""",
            (nombre, rol_id, f.get("mfa_activo", "No"), f.get("nda", ""),
             estado, fecha_inicio, fecha_fin, f.get("notas", "").strip()))
        c.commit()
        audit("usuario", "ALTA",
              f"{nombre} asignado al rol {rol['abreviatura']} "
              f"({rol['denominacion']}).")
        if rol["mfa_requerido"].startswith("Sí") and not f.get(
                "mfa_activo", "No").startswith("Sí"):
            flash(f"Advertencia: el rol {rol['abreviatura']} exige MFA "
                  "y el usuario no lo tiene activo.", "warn")
        if duplicado:
            if duplicado["rol"] == rol["abreviatura"]:
                flash(f"Aviso: ya existía otro usuario activo llamado «{nombre}» "
                      "con el mismo rol; verifique que no sea un duplicado.", "warn")
            else:
                flash(f"Aviso: ya existía otro usuario activo llamado «{nombre}» "
                      f"con el rol {duplicado['rol']} (distinto al que acaba de "
                      "asignar); verifique que no sea la misma persona con un "
                      "registro sin cerrar.", "warn")
        flash(f"Usuario «{nombre}» creado. Estos son los sistemas "
              "que hereda de su rol; puede registrar excepciones aquí abajo.")
        return redirect(url_for("usuario_detalle", uid=cur.lastrowid))



    @app.route("/usuarios/<int:uid>")
    def usuario_detalle(uid):
        c = db()
        u = c.execute(
            "SELECT u.*, r.abreviatura rol_abrev, r.denominacion, r.mfa_requerido "
            "FROM usuario u JOIN rol r ON r.id=u.rol_id WHERE u.id=?",
            (uid,)).fetchone()
        if not u:
            abort(404)
        # Accesos efectivos: nivel del rol en la matriz, anulado por la excepción si existe
        accesos = c.execute(
            """SELECT s.id sistema_id, s.nombre, cat.nombre categoria,
                      s.clasificacion, ma.nivel_codigo nivel_rol,
                      e.nivel_codigo nivel_exc, e.motivo, e.fecha_fin exc_fin,
                      COALESCE(e.nivel_codigo, ma.nivel_codigo) nivel_efectivo
               FROM sistema s
               JOIN categoria_sistema cat ON cat.id = s.categoria_id
               JOIN matriz_acceso ma ON ma.sistema_id = s.id
                    AND ma.rol_id = (SELECT rol_id FROM usuario WHERE id=?)
               LEFT JOIN acceso_excepcion e
                      ON e.usuario_id = ? AND e.sistema_id = s.id
               WHERE s.activo = 1
               ORDER BY cat.id, s.id""", (uid, uid)).fetchall()
        sistemas_sel = c.execute(
            "SELECT id, nombre FROM sistema WHERE activo=1 ORDER BY nombre"
        ).fetchall()
        roles_sel = c.execute(
            "SELECT id, abreviatura, denominacion FROM rol WHERE activo=1 "
            "ORDER BY id").fetchall()
        niveles = c.execute(
            "SELECT * FROM nivel_acceso ORDER BY orden").fetchall()
        return render_template("usuario_detalle.html", u=u, accesos=accesos,
                               sistemas=sistemas_sel, roles=roles_sel,
                               niveles=niveles)


    @app.route("/usuarios/<int:uid>/editar", methods=["POST"])
    def usuario_editar(uid):
        f = request.form
        c = db()
        nombre = f.get("nombre", "").strip()
        rol_id = _entero(f.get("rol_id"), "rol")
        fecha_inicio = f.get("fecha_inicio") or None
        fecha_fin = f.get("fecha_fin") or None
        if not nombre:
            flash("El nombre completo es obligatorio.", "warn")
            return redirect(url_for("usuario_detalle", uid=uid))
        if rol_id is None:
            return redirect(url_for("usuario_detalle", uid=uid))
        rol = c.execute("SELECT * FROM rol WHERE id=?", (rol_id,)).fetchone()
        if not rol:
            flash("Rol no encontrado.", "warn")
            return redirect(url_for("usuario_detalle", uid=uid))
        if not _fecha_valida(fecha_inicio) or not _fecha_valida(fecha_fin):
            flash("Las fechas deben tener el formato AAAA-MM-DD.", "warn")
            return redirect(url_for("usuario_detalle", uid=uid))
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            flash("La fecha de fin no puede ser anterior a la de inicio.", "warn")
            return redirect(url_for("usuario_detalle", uid=uid))
        c.execute(
            """UPDATE usuario SET nombre=?, rol_id=?, mfa_activo=?, nda=?,
                                  fecha_inicio=?, fecha_fin=?, notas=?,
                                  actualizado=datetime('now','localtime')
               WHERE id=?""",
            (nombre, rol_id, f.get("mfa_activo", "No"),
             f.get("nda", ""), fecha_inicio, fecha_fin,
             f.get("notas", "").strip(), uid))
        c.commit()
        audit("usuario", "MODIFICACION",
              f"{nombre} actualizado; rol {rol['abreviatura']}.")
        if rol["mfa_requerido"].startswith("Sí") and not f.get(
                "mfa_activo", "No").startswith("Sí"):
            flash(f"Advertencia: el rol {rol['abreviatura']} exige MFA "
                  "y el usuario no lo tiene activo.", "warn")
        flash("Usuario actualizado.")
        return redirect(url_for("usuario_detalle", uid=uid))



    @app.route("/usuarios/<int:uid>/asignar", methods=["POST"])
    def usuario_asignar(uid):
        """Asignación de sistemas al usuario: el nivel elegido para cada sistema
        se compara con el que otorga su rol; toda diferencia se registra como
        excepción documentada, y volver al nivel del rol la retira."""
        f = request.form
        motivo = f.get("motivo", "").strip()
        c = db()
        u = c.execute(
            "SELECT u.nombre, u.rol_id, r.abreviatura rol FROM usuario u "
            "JOIN rol r ON r.id=u.rol_id WHERE u.id=?", (uid,)).fetchone()
        niveles_rol = {m["sistema_id"]: m["nivel_codigo"] for m in c.execute(
            "SELECT sistema_id, nivel_codigo FROM matriz_acceso WHERE rol_id=?",
            (u["rol_id"],))}
        nombres = {s["id"]: s["nombre"] for s in c.execute(
            "SELECT id, nombre FROM sistema WHERE activo=1")}
        fecha_fin = f.get("fecha_fin") or None

        cambios, retiros = [], []
        for clave, valor in f.items():
            if not clave.startswith("nivel_"):
                continue
            sid = int(clave.split("_", 1)[1])
            if sid not in niveles_rol:
                continue
            elegido, del_rol = valor, niveles_rol[sid]
            existente = c.execute(
                "SELECT nivel_codigo FROM acceso_excepcion "
                "WHERE usuario_id=? AND sistema_id=?", (uid, sid)).fetchone()
            if elegido == del_rol:
                if existente:
                    c.execute("DELETE FROM acceso_excepcion "
                              "WHERE usuario_id=? AND sistema_id=?", (uid, sid))
                    retiros.append(nombres[sid])
            elif not existente or existente["nivel_codigo"] != elegido:
                if not motivo:
                    flash("Indique el motivo: hay niveles distintos a los del rol "
                          "y toda excepción debe justificarse (control 5.18).",
                          "warn")
                    return redirect(url_for("usuario_detalle", uid=uid))
                c.execute(
                    """INSERT INTO acceso_excepcion
                         (usuario_id, sistema_id, nivel_codigo, motivo, fecha_fin)
                       VALUES (?,?,?,?,?)
                       ON CONFLICT(usuario_id, sistema_id) DO UPDATE SET
                         nivel_codigo=excluded.nivel_codigo,
                         motivo=excluded.motivo, fecha_fin=excluded.fecha_fin""",
                    (uid, sid, elegido, motivo, fecha_fin))
                cambios.append(f"{nombres[sid]}: {del_rol} → {elegido}")
        c.commit()
        if cambios:
            audit("usuario", "MODIFICACION",
                  f"Asignación de sistemas a {u['nombre']} ({u['rol']}): "
                  + "; ".join(cambios) + f". Motivo: {motivo}"
                  + (f". Vigencia hasta {fecha_fin}" if fecha_fin else ""))
        if retiros:
            audit("usuario", "MODIFICACION",
                  f"{u['nombre']}: vuelven al nivel del rol {u['rol']}: "
                  + ", ".join(retiros) + ".")
        if cambios or retiros:
            flash(f"Asignación guardada: {len(cambios)} excepción(es) y "
                  f"{len(retiros)} retiro(s).")
        else:
            flash("Sin cambios: todos los niveles coinciden con los actuales.")
        return redirect(url_for("usuario_detalle", uid=uid))


    @app.route("/usuarios/<int:uid>/excepcion", methods=["POST"])
    def excepcion_crear(uid):
        f = request.form
        if not f.get("motivo", "").strip():
            flash("Toda excepción debe registrar un motivo (control 5.18).", "warn")
            return redirect(url_for("usuario_detalle", uid=uid))
        c = db()
        sistema_id = _entero(f.get("sistema_id"), "sistema")
        if sistema_id is None:
            return redirect(url_for("usuario_detalle", uid=uid))
        nivel = f.get("nivel", "")
        motivo = f["motivo"].strip()
        fecha_fin = f.get("fecha_fin") or None
        if not _fecha_valida(fecha_fin):
            flash("La fecha debe tener el formato AAAA-MM-DD.", "warn")
            return redirect(url_for("usuario_detalle", uid=uid))

        u = c.execute(
            "SELECT u.nombre, u.rol_id, r.abreviatura rol FROM usuario u "
            "JOIN rol r ON r.id=u.rol_id WHERE u.id=?", (uid,)).fetchone()
        s = c.execute("SELECT nombre FROM sistema WHERE id=?",
                      (sistema_id,)).fetchone()
        nivel_ok = c.execute(
            "SELECT 1 FROM nivel_acceso WHERE codigo=?", (nivel,)).fetchone()
        if not u or not s or not nivel_ok:
            flash("Usuario, sistema o nivel no válido; no se aplicó ningún cambio.",
                  "warn")
            return redirect(url_for("usuario_detalle", uid=uid))
        fila_rol = c.execute(
            "SELECT nivel_codigo FROM matriz_acceso WHERE rol_id=? AND sistema_id=?",
            (u["rol_id"], sistema_id)).fetchone()
        nivel_rol = fila_rol["nivel_codigo"] if fila_rol else "—"
        c.execute(
            """INSERT INTO acceso_excepcion (usuario_id, sistema_id, nivel_codigo,
                                             motivo, fecha_fin)
               VALUES (?,?,?,?,?)
               ON CONFLICT(usuario_id, sistema_id) DO UPDATE SET
                 nivel_codigo=excluded.nivel_codigo, motivo=excluded.motivo,
                 fecha_fin=excluded.fecha_fin""",
            (uid, sistema_id, nivel, motivo, fecha_fin))
        c.commit()
        audit("usuario", "MODIFICACION",
              f"Excepción de acceso: {u['nombre']} sobre «{s['nombre']}» → "
              f"{nivel} (el rol {u['rol']} otorga {nivel_rol}). "
              f"Motivo: {motivo}")
        flash(f"Excepción registrada: «{s['nombre']}» con nivel {nivel}.")
        return redirect(url_for("usuario_detalle", uid=uid))


    @app.route("/usuarios/<int:uid>/excepcion/<int:sid>/eliminar", methods=["POST"])
    def excepcion_eliminar(uid, sid):
        c = db()
        u = c.execute("SELECT nombre FROM usuario WHERE id=?", (uid,)).fetchone()
        s = c.execute("SELECT nombre FROM sistema WHERE id=?", (sid,)).fetchone()
        c.execute("DELETE FROM acceso_excepcion WHERE usuario_id=? AND sistema_id=?",
                  (uid, sid))
        c.commit()
        audit("usuario", "MODIFICACION",
              f"Excepción retirada: {u['nombre']} sobre «{s['nombre']}» "
              "vuelve al nivel de su rol.")
        flash(f"Excepción retirada: «{s['nombre']}» vuelve al nivel del rol.")
        return redirect(request.referrer or url_for("usuario_detalle", uid=uid))


    @app.route("/excepciones/masiva")
    def excepcion_masiva():
        c = db()
        usuarios = c.execute(
            """SELECT u.id, u.nombre, r.abreviatura rol FROM usuario u
               JOIN rol r ON r.id=u.rol_id
               WHERE u.estado IN ('Activo','Temporal')
               ORDER BY r.abreviatura, u.nombre""").fetchall()
        sistemas = c.execute(
            "SELECT id, nombre FROM sistema WHERE activo=1 ORDER BY nombre").fetchall()
        niveles = c.execute("SELECT * FROM nivel_acceso ORDER BY orden").fetchall()
        return render_template("excepcion_masiva.html", usuarios=usuarios,
                               sistemas=sistemas, niveles=niveles)


    @app.route("/excepciones/masiva/aplicar", methods=["POST"])
    def excepcion_masiva_aplicar():
        f = request.form
        motivo = f.get("motivo", "").strip()
        if not motivo:
            flash("Toda excepción debe registrar un motivo (control 5.18).", "warn")
            return redirect(url_for("excepcion_masiva"))
        c = db()
        sistema_id = _entero(f.get("sistema_id"), "sistema")
        nivel = f.get("nivel", "")
        fecha_fin = f.get("fecha_fin") or None
        if sistema_id is None:
            return redirect(url_for("excepcion_masiva"))
        if not _fecha_valida(fecha_fin):
            flash("La fecha debe tener el formato AAAA-MM-DD.", "warn")
            return redirect(url_for("excepcion_masiva"))
        s = c.execute("SELECT nombre FROM sistema WHERE id=?",
                      (sistema_id,)).fetchone()
        if not s or not c.execute("SELECT 1 FROM nivel_acceso WHERE codigo=?",
                                  (nivel,)).fetchone():
            flash("Sistema o nivel no válido.", "warn")
            return redirect(url_for("excepcion_masiva"))

        ids = [_entero(v, "usuario") for v in f.getlist("usuario_id")]
        ids = [i for i in ids if i is not None]
        if not ids:
            flash("Seleccione al menos un usuario.", "warn")
            return redirect(url_for("excepcion_masiva"))

        aplicados = 0
        for uid in ids:
            u = c.execute(
                "SELECT u.nombre, u.rol_id, r.abreviatura rol FROM usuario u "
                "JOIN rol r ON r.id=u.rol_id WHERE u.id=?", (uid,)).fetchone()
            if not u:
                continue
            fila_rol = c.execute(
                "SELECT nivel_codigo FROM matriz_acceso WHERE rol_id=? AND sistema_id=?",
                (u["rol_id"], sistema_id)).fetchone()
            nivel_rol = fila_rol["nivel_codigo"] if fila_rol else "—"
            c.execute(
                """INSERT INTO acceso_excepcion (usuario_id, sistema_id, nivel_codigo,
                                                 motivo, fecha_fin)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(usuario_id, sistema_id) DO UPDATE SET
                     nivel_codigo=excluded.nivel_codigo, motivo=excluded.motivo,
                     fecha_fin=excluded.fecha_fin""",
                (uid, sistema_id, nivel, motivo, fecha_fin))
            audit("usuario", "MODIFICACION",
                  f"Excepción de acceso (asignación masiva): {u['nombre']} sobre "
                  f"«{s['nombre']}» → {nivel} (el rol {u['rol']} otorga "
                  f"{nivel_rol}). Motivo: {motivo}")
            aplicados += 1
        c.commit()
        flash(f"Excepción aplicada a {aplicados} usuario(s) sobre «{s['nombre']}».")
        return redirect(url_for("excepciones"))


    # ------------------------------------------------------- excepciones (5.18)
    @app.route("/excepciones")
    def excepciones():
        c = db()
        incluir_vencidas = request.args.get("vencidas") == "1"
        sql = """SELECT u.id usuario_id, u.nombre usuario, u.estado usuario_estado,
                        s.id sistema_id, s.nombre sistema, r.abreviatura rol,
                        COALESCE(ma.nivel_codigo, '—') nivel_rol,
                        e.nivel_codigo nivel_excepcion, e.motivo, e.fecha_fin,
                        e.creado,
                        CASE WHEN e.fecha_fin IS NOT NULL
                                  AND date(e.fecha_fin) < date('now')
                             THEN 1 ELSE 0 END vencida
                 FROM acceso_excepcion e
                 JOIN usuario u ON u.id = e.usuario_id
                 JOIN sistema s ON s.id = e.sistema_id
                 JOIN rol r ON r.id = u.rol_id
                 LEFT JOIN matriz_acceso ma
                        ON ma.rol_id = u.rol_id AND ma.sistema_id = e.sistema_id"""
        if not incluir_vencidas:
            sql += " WHERE e.fecha_fin IS NULL OR date(e.fecha_fin) >= date('now')"
        sql += """ ORDER BY
                 CASE WHEN e.fecha_fin IS NOT NULL AND date(e.fecha_fin) < date('now')
                      THEN 1 ELSE 0 END DESC,
                 e.fecha_fin IS NULL, e.fecha_fin, u.nombre"""
        filas = c.execute(sql).fetchall()
        total_vigentes = c.execute(
            "SELECT COUNT(*) n FROM acceso_excepcion "
            "WHERE fecha_fin IS NULL OR date(fecha_fin) >= date('now')"
        ).fetchone()["n"]
        total_vencidas = c.execute(
            "SELECT COUNT(*) n FROM acceso_excepcion "
            "WHERE fecha_fin IS NOT NULL AND date(fecha_fin) < date('now')"
        ).fetchone()["n"]
        return render_template("excepciones.html", filas=filas,
                               incluir_vencidas=incluir_vencidas,
                               total_vigentes=total_vigentes,
                               total_vencidas=total_vencidas)


    @app.route("/usuarios/<int:uid>/estado", methods=["POST"])
    def usuario_estado(uid):
        nuevo = request.form.get("estado", "")
        if nuevo not in ESTADOS_USUARIO:
            flash("Estado no reconocido; no se aplicó ningún cambio.", "warn")
            return redirect(url_for("usuarios"))
        motivo = request.form.get("motivo", "").strip()
        c = db()
        u = c.execute(
            "SELECT u.nombre, r.abreviatura rol FROM usuario u "
            "JOIN rol r ON r.id=u.rol_id WHERE u.id=?", (uid,)).fetchone()
        c.execute(
            "UPDATE usuario SET estado=?, notas=CASE WHEN ?<>'' THEN ? ELSE notas END, "
            "actualizado=datetime('now','localtime') WHERE id=?",
            (nuevo, motivo, motivo, uid))
        c.commit()
        accion = "REVOCACION" if nuevo == "Revocado" else "MODIFICACION"
        audit("usuario", accion,
              f"{u['nombre']} ({u['rol']}) → estado {nuevo}."
              + (f" Motivo: {motivo}" if motivo else ""))
        flash(f"Estado de «{u['nombre']}» actualizado a {nuevo}.")
        return redirect(url_for("usuarios"))



    @app.route("/usuarios/<int:uid>/eliminar", methods=["POST"])
    def usuario_eliminar(uid):
        c = db()
        u = c.execute(
            "SELECT u.nombre, r.abreviatura rol FROM usuario u "
            "JOIN rol r ON r.id=u.rol_id WHERE u.id=?", (uid,)).fetchone()
        c.execute("DELETE FROM usuario WHERE id=?", (uid,))
        c.commit()
        audit("usuario", "ELIMINACION",
              f"Usuario {u['nombre']} ({u['rol']}) eliminado del registro. "
              "La bitácora conserva sus movimientos previos.")
        flash(f"Usuario «{u['nombre']}» eliminado.")
        return redirect(url_for("usuarios"))


    # ---------------------------------------------------------------- auditoría
    POR_PAGINA_AUDITORIA = 50

    @app.route("/auditoria")
    def auditoria():
        c = db()
        entidad = request.args.get("entidad", "")
        accion = request.args.get("accion", "")
        q = request.args.get("q", "").strip()
        pagina = _entero(request.args.get("pagina", "1"), "página") or 1
        pagina = max(pagina, 1)

        sql = "SELECT * FROM log_auditoria WHERE 1=1"
        p = []
        if entidad:
            sql += " AND entidad=?"
            p.append(entidad)
        if accion:
            sql += " AND accion=?"
            p.append(accion)
        if q:
            sql += " AND (detalle LIKE ? OR responsable LIKE ?)"
            p += [f"%{q}%", f"%{q}%"]
        total = c.execute(
            sql.replace("SELECT *", "SELECT COUNT(*) n", 1), p
        ).fetchone()["n"]
        offset = (pagina - 1) * POR_PAGINA_AUDITORIA
        filas = c.execute(
            sql + " ORDER BY id DESC LIMIT ? OFFSET ?",
            p + [POR_PAGINA_AUDITORIA, offset]).fetchall()

        entidades = [r["entidad"] for r in c.execute(
            "SELECT DISTINCT entidad FROM log_auditoria ORDER BY entidad")]
        acciones = [r["accion"] for r in c.execute(
            "SELECT DISTINCT accion FROM log_auditoria ORDER BY accion")]
        total_paginas = max(1, -(-total // POR_PAGINA_AUDITORIA))  # techo
        return render_template("auditoria.html", log=filas, f_entidad=entidad,
                               f_accion=accion, f_q=q, entidades=entidades,
                               acciones=acciones, pagina=pagina,
                               total_paginas=total_paginas, total=total)


    # ---------------------------------------------------------------- export CSV
    def _celda_segura(valor):
        """Antepone un apóstrofo si la celda podría interpretarse como fórmula
        al abrirse en Excel/Sheets (mitigación de CSV/Formula Injection)."""
        txt = "" if valor is None else str(valor)
        if txt and txt[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + txt
        return txt

    def _csv_response(nombre, encabezados, filas):
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow([_celda_segura(h) for h in encabezados])
        w.writerows([[_celda_segura(v) for v in fila] for fila in filas])
        return Response(
            "\ufeff" + buf.getvalue(), mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={nombre}"})


    @app.route("/export/matriz.csv")
    def export_matriz():
        c = db()
        roles = c.execute("SELECT id, abreviatura FROM rol ORDER BY id").fetchall()
        sistemas = c.execute("SELECT id, nombre FROM sistema ORDER BY id").fetchall()
        celdas = {(m["rol_id"], m["sistema_id"]): m["nivel_codigo"]
                  for m in c.execute("SELECT * FROM matriz_acceso")}
        filas = [[s["nombre"]] + [celdas.get((r["id"], s["id"]), "—")
                                  for r in roles] for s in sistemas]
        return _csv_response(
            "SUIIN-SGSI-MCA-001_matriz.csv",
            ["Sistema"] + [r["abreviatura"] for r in roles], filas)


    @app.route("/export/accesos_usuarios.csv")
    def export_accesos():
        filas = db().execute(
            "SELECT usuario, estado, rol, sistema, categoria, clasificacion, nivel, "
            "CASE es_excepcion WHEN 1 THEN 'Sí' ELSE '' END "
            "FROM v_accesos_usuario ORDER BY usuario, sistema").fetchall()
        return _csv_response(
            "SUIIN-SGSI-MCA-001_accesos_efectivos.csv",
            ["Usuario", "Estado", "Rol", "Sistema", "Categoría",
             "Clasificación", "Nivel", "Excepción"],
            [list(f) for f in filas])



    @app.route("/auditoria/verificar")
    def auditoria_verificar():
        ok, dato = verificar_cadena()
        if ok:
            flash(f"Cadena de auditoría íntegra: {dato} registros "
                  "verificados sin alteraciones.")
        else:
            flash(f"ALERTA: la cadena se rompe en el registro #{dato} — "
                  "la bitácora fue alterada fuera de la aplicación.", "warn")
        return redirect(url_for("auditoria"))
