#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUIIN-RBAC — API REST en JSON para la SPA unificada de React.

La interfaz HTML (Jinja2 + plantillas) fue retirada; este módulo expone
todas las operaciones de negocio bajo /api/. nginx las publica como
/rbac/api/… con auth_request contra el Inventario.
"""
import sqlite3

from flask import jsonify, request

from db import audit, db, verificar_cadena
import negocio


# --------------------------------------------------------------- adaptador
class _FormLike:
    """Envuelve un dict JSON con la misma interfaz que request.form
    (.get()), normalizando tipos — JSON puede traer booleanos/números
    donde el formulario HTML siempre traía texto — para poder reutilizar
    los validadores existentes (_validar_datos_rol, _validar_datos_sistema)
    sin duplicarlos ni reescribirlos."""

    def __init__(self, data):
        normalizado = {}
        for k, v in (data or {}).items():
            if isinstance(v, bool):
                normalizado[k] = "1" if v else "0"
            elif v is None:
                normalizado[k] = ""
            else:
                normalizado[k] = str(v)
        self._d = normalizado

    def get(self, key, default=None):
        return self._d.get(key, default)


def _json_body():
    return _FormLike(request.get_json(silent=True) or {})


def _fila_a_dict(fila):
    return dict(fila) if fila is not None else None


def registrar(app):
    # ------------------------------------------------------------- salud
    @app.route("/")
    def raiz():
        return jsonify({"servicio": "SUIIN-RBAC", "modo": "api"})

    # ------------------------------------------------------------- CSRF
    @app.route("/api/csrf")
    def api_csrf():
        """El front-end lo pide una vez y reenvía el valor como encabezado
        X-CSRF-Token en cada POST/PUT/DELETE."""
        from auth import csrf_token_actual
        return jsonify({"csrf_token": csrf_token_actual()})

    # --------------------------------------------------- sistemas (integración Inventario)
    @app.route("/api/sistemas")
    def api_sistemas():
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
        if clasif_f in negocio.CLASIFICACIONES:
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

    # ------------------------------------------------------ resumen (integración Inventario)
    @app.route("/api/resumen")
    def api_resumen():
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
            (f"+{negocio.DIAS_ALERTA_VENCIMIENTO} days",
             f"+{negocio.DIAS_ALERTA_VENCIMIENTO} days")
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
            f"AND {negocio.SQL_REVISION_VENCIDA} = 1").fetchone()["n"]

        pendientes_total = (proximos_vencimientos + excepciones_vencidas
                            + roles_certificacion_vencida + alertas_mfa)

        return jsonify({
            "roles_total": roles_total,
            "sistemas_total": sistemas_total,
            "usuarios_activos": usuarios_activos,
            "mfa_pct": mfa_pct, "mfa_ok": mfa_ok, "mfa_total": mfa_total,
            "proximos_vencimientos": proximos_vencimientos,
            "excepciones_vigentes": excepciones_vigentes,
            "excepciones_vencidas": excepciones_vencidas,
            "roles_certificacion_vencida": roles_certificacion_vencida,
            "alertas_mfa": alertas_mfa,
            "pendientes_total": pendientes_total,
            "desglose_pendientes": {
                "proximos_vencimientos": proximos_vencimientos,
                "excepciones_vencidas": excepciones_vencidas,
                "roles_certificacion_vencida": roles_certificacion_vencida,
                "alertas_mfa": alertas_mfa,
            },
        })

    # -------------------------------------------------------- catálogos
    @app.route("/api/inicio")
    def api_inicio():
        """Version en JSON del tablero de Inicio (inicio()) — /api/resumen
        solo trae los KPIs agregados; esto agrega las filas de detalle que
        necesita un tablero real (alertas MFA nominales, roles criticos,
        temporales, revocados, ultimos movimientos, grafico de riesgo por
        rol y vencimientos proximos), reutilizando las mismas consultas."""
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
        alertas_mfa = [dict(r) for r in c.execute("SELECT * FROM v_alertas_mfa")]
        criticos = [dict(r) for r in c.execute(
            """SELECT r.abreviatura, r.denominacion, COUNT(*) n_admin
               FROM matriz_acceso ma JOIN rol r ON r.id = ma.rol_id
               WHERE ma.nivel_codigo='A'
               GROUP BY r.id ORDER BY n_admin DESC""")]
        temporales = [dict(r) for r in c.execute(
            "SELECT u.nombre, r.abreviatura rol, u.fecha_fin FROM usuario u "
            "JOIN rol r ON r.id=u.rol_id WHERE u.estado='Temporal'")]
        revocados = [dict(r) for r in c.execute(
            "SELECT u.nombre, r.abreviatura rol, u.notas FROM usuario u "
            "JOIN rol r ON r.id=u.rol_id WHERE u.estado='Revocado'")]
        log = [dict(r) for r in c.execute(
            "SELECT * FROM log_auditoria ORDER BY id DESC LIMIT 8")]

        riesgo_roles = {r["riesgo_attack"]: r["n"] for r in c.execute(
            """SELECT riesgo_attack, COUNT(*) n FROM rol
               WHERE activo=1 GROUP BY riesgo_attack""")}
        riesgo = [
            {"nombre": "Alto", "n": riesgo_roles.get("Alto", 0), "color": "#e0475a"},
            {"nombre": "Medio", "n": riesgo_roles.get("Medio", 0), "color": "#e0812f"},
            {"nombre": "Bajo", "n": riesgo_roles.get("Bajo", 0), "color": "#4bab7c"},
        ]
        max_riesgo = max((x["n"] for x in riesgo), default=0) or 1

        mfa_total = c.execute(
            "SELECT COUNT(*) n FROM usuario u JOIN rol r ON r.id=u.rol_id "
            "WHERE u.estado IN ('Activo','Temporal') AND r.mfa_requerido "
            "LIKE 'Sí%'").fetchone()["n"]
        mfa_ok = mfa_total - len(alertas_mfa)
        mfa_pct = round(100 * mfa_ok / mfa_total) if mfa_total else 100

        proximos_vencimientos = [dict(r) for r in c.execute(
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
            (f"+{negocio.DIAS_ALERTA_VENCIMIENTO} days", f"+{negocio.DIAS_ALERTA_VENCIMIENTO} days"))]

        return jsonify({
            "stats": stats, "alertas_mfa": alertas_mfa, "criticos": criticos,
            "temporales": temporales, "revocados": revocados, "log": log,
            "riesgo": riesgo, "max_riesgo": max_riesgo, "mfa_pct": mfa_pct,
            "mfa_ok": mfa_ok, "mfa_total": mfa_total,
            "proximos_vencimientos": proximos_vencimientos,
            "dias_alerta": negocio.DIAS_ALERTA_VENCIMIENTO,
        })

    # -------------------------------------------------------- catálogos
    @app.route("/api/catalogos")
    def api_catalogos():
        """Catálogos auxiliares para poblar los formularios de React
        (grupos de rol, categorías de sistema, niveles de acceso) — evita
        tres llamadas sueltas para datos que casi no cambian."""
        c = db()
        grupos = [dict(r) for r in c.execute(
            "SELECT id, codigo, nombre FROM grupo_rol ORDER BY nombre")]
        categorias = [dict(r) for r in c.execute(
            "SELECT id, nombre FROM categoria_sistema ORDER BY nombre")]
        niveles = [dict(r) for r in c.execute(
            "SELECT codigo, nombre, descripcion, orden FROM nivel_acceso ORDER BY orden")]
        entidades_auditoria = [r["entidad"] for r in c.execute(
            "SELECT DISTINCT entidad FROM log_auditoria ORDER BY entidad")]
        acciones_auditoria = [r["accion"] for r in c.execute(
            "SELECT DISTINCT accion FROM log_auditoria ORDER BY accion")]
        return jsonify({
            "grupos_rol": grupos,
            "categorias_sistema": categorias,
            "niveles_acceso": niveles,
            "riesgos_attack": list(negocio.RIESGOS_ATTACK),
            "clasificaciones": list(negocio.CLASIFICACIONES),
            "estados_usuario": list(negocio.ESTADOS_USUARIO),
            "entidades_auditoria": entidades_auditoria,
            "acciones_auditoria": acciones_auditoria,
        })

    # -------------------------------------------------------------- roles
    @app.route("/api/roles")
    def api_roles_lista():
        c = db()
        incluir_inactivos = request.args.get("incluir_inactivos") == "1"
        q = request.args.get("q", "").strip()
        sql = (f"SELECT r.*, g.nombre grupo, {negocio.SQL_REVISION_VENCIDA} revision_vencida "
               "FROM rol r JOIN grupo_rol g ON g.id = r.grupo_id WHERE 1=1")
        params = []
        if not incluir_inactivos:
            sql += " AND r.activo = 1"
        if q:
            sql += " AND (r.abreviatura LIKE ? OR r.denominacion LIKE ? OR r.codigo LIKE ?)"
            params += [f"%{q}%"] * 3
        sql += " ORDER BY r.abreviatura"
        filas = [dict(r) for r in c.execute(sql, params)]
        return jsonify(filas)

    @app.route("/api/roles/<int:rid>")
    def api_rol_detalle(rid):
        c = db()
        rol = c.execute(
            f"SELECT r.*, g.nombre grupo, {negocio.SQL_REVISION_VENCIDA} revision_vencida "
            "FROM rol r JOIN grupo_rol g ON g.id=r.grupo_id WHERE r.id=?",
            (rid,)).fetchone()
        if not rol:
            return jsonify({"detail": "Rol no encontrado."}), 404
        accesos = [dict(r) for r in c.execute(
            """SELECT s.id sistema_id, s.nombre, s.clasificacion, cat.nombre categoria,
                      ma.nivel_codigo nivel, n.nombre nivel_nombre
               FROM matriz_acceso ma
               JOIN sistema s ON s.id=ma.sistema_id
               JOIN categoria_sistema cat ON cat.id=s.categoria_id
               JOIN nivel_acceso n ON n.codigo=ma.nivel_codigo
               WHERE ma.rol_id=? AND ma.nivel_codigo<>'—'
               ORDER BY n.orden, s.id""", (rid,))]
        usuarios = [dict(r) for r in c.execute(
            "SELECT * FROM usuario WHERE rol_id=? ORDER BY estado, nombre", (rid,))]
        data = dict(rol)
        data["accesos"] = accesos
        data["usuarios"] = usuarios
        return jsonify(data)

    @app.route("/api/roles", methods=["POST"])
    def api_rol_crear():
        c = db()
        cuerpo = _json_body()
        datos, error = negocio._validar_datos_rol(cuerpo, c)
        if error:
            return jsonify({"detail": error}), 400
        clonar_raw = (cuerpo.get("clonar_de") or "").strip()
        rol_origen = None
        clonar_de = None
        if clonar_raw:
            try:
                clonar_de = int(clonar_raw)
            except (TypeError, ValueError):
                return jsonify({"detail": "El rol a clonar no es válido."}), 400
            rol_origen = c.execute("SELECT abreviatura FROM rol WHERE id=?",
                                   (clonar_de,)).fetchone()
            if not rol_origen:
                return jsonify({"detail": "El rol elegido para clonar ya no existe."}), 400
        try:
            cur = c.execute(
                """INSERT INTO rol (codigo, abreviatura, denominacion, grupo_id,
                                    cosecha, en_det7, funcion, mfa_requerido,
                                    riesgo_attack, revision_periodica, observaciones)
                   VALUES (:codigo, :abreviatura, :denominacion, :grupo_id, :cosecha,
                           :en_det7, :funcion, :mfa_requerido, :riesgo_attack,
                           :revision_periodica, :observaciones)""", datos)
        except sqlite3.IntegrityError:
            return jsonify({"detail": "Ya existe un rol con ese código o abreviatura."}), 409
        rid = cur.lastrowid
        # Igual que rol_crear() en negocio.py: inicializar la fila del nuevo rol
        # en la matriz — copiando el rol de origen si se indicó uno, o en
        # '—' (sin accesos, mínimo privilegio) en caso contrario. Sin este
        # paso, el rol quedaba sin ninguna fila en matriz_acceso al crearse
        # por la API (aunque sí funcionaba al crearse desde el formulario
        # HTML), y "Clonar accesos desde" no tenía ningún efecto real.
        c.execute(
            """INSERT INTO matriz_acceso (rol_id, sistema_id, nivel_codigo)
               SELECT ?, s.id, COALESCE(origen.nivel_codigo, '—')
               FROM sistema s
               LEFT JOIN matriz_acceso origen
                      ON origen.sistema_id = s.id AND origen.rol_id = ?""",
            (rid, clonar_de))
        c.commit()
        origen_txt = (f"clonando los accesos de {rol_origen['abreviatura']}"
                     if rol_origen else "sin accesos")
        audit("rol", "ALTA",
              f"Rol {datos['abreviatura']} ({datos['denominacion']}) creado vía API. "
              f"Matriz inicializada {origen_txt}.")
        return jsonify({"id": rid, **datos}), 201

    @app.route("/api/roles/<int:rid>", methods=["PUT"])
    def api_rol_editar(rid):
        c = db()
        if not c.execute("SELECT 1 FROM rol WHERE id=?", (rid,)).fetchone():
            return jsonify({"detail": "Rol no encontrado."}), 404
        datos, error = negocio._validar_datos_rol(_json_body(), c)
        if error:
            return jsonify({"detail": error}), 400
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
            return jsonify({"detail": "Ya existe otro rol con ese código o abreviatura."}), 409
        c.commit()
        audit("rol", "MODIFICACION", f"Rol {datos['abreviatura']} (id {rid}) actualizado vía API.")
        return jsonify({"id": rid, **datos})

    @app.route("/api/roles/<int:rid>/activo", methods=["DELETE", "POST"])
    def api_rol_toggle_activo(rid):
        """Baja/alta lógica (nunca se borra un rol, por trazabilidad)."""
        c = db()
        r = c.execute("SELECT abreviatura, activo FROM rol WHERE id=?", (rid,)).fetchone()
        if not r:
            return jsonify({"detail": "Rol no encontrado."}), 404
        nuevo = 0 if r["activo"] else 1
        if nuevo == 0:
            n = c.execute(
                "SELECT COUNT(*) n FROM usuario WHERE rol_id=? "
                "AND estado IN ('Activo','Temporal')", (rid,)).fetchone()["n"]
            if n:
                return jsonify({
                    "detail": f"No se puede desactivar {r['abreviatura']}: tiene {n} "
                              "usuario(s) activo(s). Reasigne o revoque primero."
                }), 409
        c.execute("UPDATE rol SET activo=? WHERE id=?", (nuevo, rid))
        c.commit()
        audit("rol", "MODIFICACION",
              f"Rol {r['abreviatura']} marcado como {'activo' if nuevo else 'inactivo'} vía API.")
        return jsonify({"id": rid, "activo": bool(nuevo)})

    @app.route("/api/roles/<int:rid>/certificar", methods=["POST"])
    def api_rol_certificar(rid):
        c = db()
        r = c.execute("SELECT abreviatura, denominacion, revision_periodica "
                      "FROM rol WHERE id=?", (rid,)).fetchone()
        if not r:
            return jsonify({"detail": "Rol no encontrado."}), 404
        nota = (request.get_json(silent=True) or {}).get("nota", "").strip()
        c.execute("UPDATE rol SET ultima_revision=date('now','localtime') WHERE id=?", (rid,))
        c.commit()
        audit("rol", "REVISION",
              f"Rol {r['abreviatura']} ({r['denominacion']}) revisado conforme a su "
              f"periodicidad ({r['revision_periodica']}, POL-SI-002) vía API."
              + (f" Nota: {nota}" if nota else ""))
        return jsonify({"id": rid, "certificado": True})

    @app.route("/api/roles/<int:rid>", methods=["DELETE"])
    def api_rol_eliminar(rid):
        """Elimina definitivamente un rol — misma salvaguarda que
        rol_eliminar() en negocio.py: no se permite si algún usuario (incluso
        revocado) todavía lo referencia, para no destruir su trazabilidad."""
        c = db()
        r = c.execute("SELECT abreviatura, denominacion FROM rol WHERE id=?", (rid,)).fetchone()
        if not r:
            return jsonify({"detail": "Rol no encontrado."}), 404
        n = c.execute("SELECT COUNT(*) n FROM usuario WHERE rol_id=?", (rid,)).fetchone()["n"]
        if n:
            return jsonify({
                "detail": f"No se puede eliminar {r['abreviatura']}: {n} usuario(s) lo "
                          "referencian (incluidos revocados). Eliminar el rol destruiría "
                          "su trazabilidad — use Desactivar, o elimine antes esos usuarios."
            }), 409
        c.execute("DELETE FROM rol WHERE id=?", (rid,))  # matriz_acceso cae en cascada
        c.commit()
        audit("rol", "ELIMINACION",
              f"Rol {r['abreviatura']} ({r['denominacion']}) eliminado definitivamente "
              "vía API, junto con su fila de la matriz.")
        return "", 204

    # ---------------------------------------------------------- sistemas (escritura)
    # La lectura (GET /api/sistemas, GET /api/sistemas/<id>) ya vive en
    # negocio.py — se construyó primero para el cruce en vivo con el
    # Inventario (sección 8.6/7.1 del README). Aquí solo se agrega la
    # escritura, reutilizando _validar_datos_sistema.
    @app.route("/api/sistemas/<int:sid>")
    def api_sistema_detalle(sid):
        """No existía ningún endpoint JSON para leer un sistema individual
        — solo escritura (PUT/DELETE/activo). Sin esto, un formulario de
        edición en React no tenía forma de precargar sus datos."""
        c = db()
        sis = c.execute(
            "SELECT s.*, c.nombre categoria FROM sistema s "
            "JOIN categoria_sistema c ON c.id=s.categoria_id WHERE s.id=?",
            (sid,)).fetchone()
        if not sis:
            return jsonify({"detail": "Sistema no encontrado."}), 404
        roles_acc = [dict(r) for r in c.execute(
            """SELECT r.id, r.abreviatura, r.denominacion, ma.nivel_codigo nivel,
                      n.nombre nivel_nombre
               FROM matriz_acceso ma
               JOIN rol r ON r.id=ma.rol_id
               JOIN nivel_acceso n ON n.codigo=ma.nivel_codigo
               WHERE ma.sistema_id=? AND ma.nivel_codigo<>'—' AND r.activo=1
               ORDER BY n.orden, r.id""", (sid,))]
        usuarios = [dict(r) for r in c.execute(
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
               ORDER BY u.nombre""", (sid, sid))]
        data = dict(sis)
        data["roles"] = roles_acc
        data["usuarios"] = usuarios
        return jsonify(data)

    @app.route("/api/sistemas", methods=["POST"])
    def api_sistema_crear():
        c = db()
        datos, error = negocio._validar_datos_sistema(_json_body(), c)
        if error:
            return jsonify({"detail": error}), 400
        try:
            cur = c.execute(
                """INSERT INTO sistema (nombre, categoria_id, clasificacion, tecnicas_attack)
                   VALUES (:nombre,:categoria_id,:clasificacion,:tecnicas_attack)""", datos)
        except sqlite3.IntegrityError:
            return jsonify({"detail": "Ya existe un sistema con ese nombre."}), 409
        sid_nuevo = cur.lastrowid
        c.execute("INSERT INTO matriz_acceso (rol_id, sistema_id, nivel_codigo) "
                  "SELECT id, ?, '—' FROM rol", (sid_nuevo,))
        c.commit()
        audit("sistema", "ALTA",
              f"Sistema «{datos['nombre']}» creado vía API ({datos['clasificacion']}). "
              "Matriz inicializada sin accesos.")
        return jsonify({"id": sid_nuevo, **datos}), 201

    @app.route("/api/sistemas/<int:sid>", methods=["PUT"])
    def api_sistema_editar(sid):
        c = db()
        if not c.execute("SELECT 1 FROM sistema WHERE id=?", (sid,)).fetchone():
            return jsonify({"detail": "Sistema no encontrado."}), 404
        datos, error = negocio._validar_datos_sistema(_json_body(), c)
        if error:
            return jsonify({"detail": error}), 400
        try:
            c.execute(
                """UPDATE sistema SET nombre=:nombre, categoria_id=:categoria_id,
                                      clasificacion=:clasificacion,
                                      tecnicas_attack=:tecnicas_attack
                   WHERE id=:id""", {**datos, "id": sid})
        except sqlite3.IntegrityError:
            return jsonify({"detail": "Ya existe otro sistema con ese nombre."}), 409
        c.commit()
        audit("sistema", "MODIFICACION", f"Sistema «{datos['nombre']}» (id {sid}) actualizado vía API.")
        return jsonify({"id": sid, **datos})

    @app.route("/api/sistemas/<int:sid>/activo", methods=["DELETE", "POST"])
    def api_sistema_toggle_activo(sid):
        c = db()
        s = c.execute("SELECT nombre, activo FROM sistema WHERE id=?", (sid,)).fetchone()
        if not s:
            return jsonify({"detail": "Sistema no encontrado."}), 404
        nuevo = 0 if s["activo"] else 1
        c.execute("UPDATE sistema SET activo=? WHERE id=?", (nuevo, sid))
        c.commit()
        audit("sistema", "MODIFICACION" if nuevo else "REVOCACION",
              f"Sistema «{s['nombre']}» " + ("reactivado vía API." if nuevo else
              "desactivado vía API. Se conserva su historial y su columna en la matriz."))
        return jsonify({"id": sid, "activo": bool(nuevo)})

    @app.route("/api/sistemas/<int:sid>", methods=["DELETE"])
    def api_sistema_eliminar(sid):
        c = db()
        s = c.execute("SELECT nombre FROM sistema WHERE id=?", (sid,)).fetchone()
        if not s:
            return jsonify({"detail": "Sistema no encontrado."}), 404
        n = c.execute("SELECT COUNT(*) n FROM acceso_excepcion WHERE sistema_id=?",
                      (sid,)).fetchone()["n"]
        if n:
            return jsonify({
                "detail": f"No se puede eliminar «{s['nombre']}»: tiene {n} excepción(es) "
                          "de acceso documentada(s) (control 5.18). Use Desactivar, o retire "
                          "antes esas excepciones."
            }), 409
        c.execute("DELETE FROM sistema WHERE id=?", (sid,))
        c.commit()
        audit("sistema", "ELIMINACION",
              f"Sistema «{s['nombre']}» eliminado definitivamente vía API junto con su "
              "columna de la matriz.")
        return jsonify({"id": sid, "eliminado": True})

    # -------------------------------------------------------------- usuarios
    def _validar_datos_usuario(f, c, uid_actual=None):
        """Misma validación que ya usaban usuario_crear/usuario_editar en
        negocio.py (no se extrajo a una función compartida allá para no
        arriesgar ese código ya probado; aquí se reimplementa idéntica
        para la API)."""
        nombre = f.get("nombre", "").strip()
        if not nombre:
            return None, "El nombre completo es obligatorio."
        try:
            rol_id = int(f.get("rol_id"))
        except (TypeError, ValueError):
            return None, "Seleccione un rol válido."
        rol = c.execute("SELECT * FROM rol WHERE id=?", (rol_id,)).fetchone()
        if not rol or (uid_actual is None and not rol["activo"]):
            return None, "Seleccione un rol activo válido."
        estado = f.get("estado", "Activo")
        if estado not in negocio.ESTADOS_USUARIO:
            return None, "Estado no reconocido."
        fecha_inicio = f.get("fecha_inicio") or None
        fecha_fin = f.get("fecha_fin") or None
        if not negocio._fecha_valida(fecha_inicio) or not negocio._fecha_valida(fecha_fin):
            return None, "Las fechas deben tener el formato AAAA-MM-DD."
        if estado == "Temporal":
            if not fecha_inicio or not fecha_fin:
                return None, "El acceso Temporal requiere fecha de inicio y de fin."
            if fecha_fin < fecha_inicio:
                return None, "La fecha de fin no puede ser anterior a la de inicio."
        elif fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            return None, "La fecha de fin no puede ser anterior a la de inicio."
        return {
            "nombre": nombre, "rol_id": rol_id, "estado": estado,
            "mfa_activo": f.get("mfa_activo", "No"), "nda": f.get("nda", ""),
            "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin,
            "notas": f.get("notas", "").strip(),
        }, None

    @app.route("/api/usuarios")
    def api_usuarios_lista():
        c = db()
        q = request.args.get("q", "").strip()
        estado_f = request.args.get("estado", "")
        rol_f = request.args.get("rol", "")
        sql = """SELECT u.*, r.abreviatura rol, r.denominacion, r.mfa_requerido,
                        (SELECT COUNT(*) FROM v_accesos_usuario v
                         WHERE v.usuario_id = u.id) n_sistemas,
                        (SELECT COUNT(*) FROM acceso_excepcion e
                         WHERE e.usuario_id = u.id) n_excepciones
                 FROM usuario u JOIN rol r ON r.id=u.rol_id WHERE 1=1"""
        p = []
        if q:
            sql += " AND (u.nombre LIKE ? OR r.abreviatura LIKE ? OR r.denominacion LIKE ?)"
            p += [f"%{q}%"] * 3
        if estado_f in negocio.ESTADOS_USUARIO:
            sql += " AND u.estado=?"
            p.append(estado_f)
        if rol_f:
            sql += " AND u.rol_id=?"
            p.append(rol_f)
        sql += (" ORDER BY CASE u.estado WHEN 'Activo' THEN 0 WHEN 'Temporal' THEN 1 "
                "WHEN 'Suspendido' THEN 2 ELSE 3 END, u.nombre")
        return jsonify([dict(r) for r in c.execute(sql, p)])

    @app.route("/api/usuarios/<int:uid>")
    def api_usuario_detalle(uid):
        c = db()
        u = c.execute(
            "SELECT u.*, r.abreviatura rol_abrev, r.denominacion, r.mfa_requerido "
            "FROM usuario u JOIN rol r ON r.id=u.rol_id WHERE u.id=?", (uid,)).fetchone()
        if not u:
            return jsonify({"detail": "Usuario no encontrado."}), 404
        accesos = [dict(r) for r in c.execute(
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
               ORDER BY cat.id, s.id""", (uid, uid))]
        data = dict(u)
        data["accesos"] = accesos
        return jsonify(data)

    @app.route("/api/usuarios", methods=["POST"])
    def api_usuario_crear():
        c = db()
        datos, error = _validar_datos_usuario(_json_body(), c)
        if error:
            return jsonify({"detail": error}), 400
        rol = c.execute("SELECT abreviatura, denominacion, mfa_requerido FROM rol WHERE id=?",
                        (datos["rol_id"],)).fetchone()
        cur = c.execute(
            """INSERT INTO usuario (nombre, rol_id, mfa_activo, nda, estado,
                                    fecha_inicio, fecha_fin, notas)
               VALUES (:nombre,:rol_id,:mfa_activo,:nda,:estado,:fecha_inicio,:fecha_fin,:notas)""",
            datos)
        c.commit()
        uid_nuevo = cur.lastrowid
        audit("usuario", "ALTA",
              f"{datos['nombre']} asignado al rol {rol['abreviatura']} "
              f"({rol['denominacion']}) vía API.")
        aviso_mfa = rol["mfa_requerido"].startswith("Sí") and not datos["mfa_activo"].startswith("Sí")
        return jsonify({"id": uid_nuevo, **datos, "aviso_mfa": aviso_mfa}), 201

    @app.route("/api/usuarios/<int:uid>", methods=["PUT"])
    def api_usuario_editar(uid):
        c = db()
        if not c.execute("SELECT 1 FROM usuario WHERE id=?", (uid,)).fetchone():
            return jsonify({"detail": "Usuario no encontrado."}), 404
        datos, error = _validar_datos_usuario(_json_body(), c, uid_actual=uid)
        if error:
            return jsonify({"detail": error}), 400
        rol = c.execute("SELECT abreviatura, mfa_requerido FROM rol WHERE id=?",
                        (datos["rol_id"],)).fetchone()
        c.execute(
            """UPDATE usuario SET nombre=:nombre, rol_id=:rol_id, mfa_activo=:mfa_activo,
                                  nda=:nda, estado=:estado, fecha_inicio=:fecha_inicio,
                                  fecha_fin=:fecha_fin, notas=:notas,
                                  actualizado=datetime('now','localtime')
               WHERE id=:id""", {**datos, "id": uid})
        c.commit()
        audit("usuario", "MODIFICACION", f"{datos['nombre']} actualizado vía API; rol {rol['abreviatura']}.")
        aviso_mfa = rol["mfa_requerido"].startswith("Sí") and not datos["mfa_activo"].startswith("Sí")
        return jsonify({"id": uid, **datos, "aviso_mfa": aviso_mfa})

    @app.route("/api/usuarios/<int:uid>/estado", methods=["PUT"])
    def api_usuario_estado(uid):
        c = db()
        cuerpo = request.get_json(silent=True) or {}
        nuevo = cuerpo.get("estado", "")
        if nuevo not in negocio.ESTADOS_USUARIO:
            return jsonify({"detail": "Estado no reconocido."}), 400
        u = c.execute(
            "SELECT u.nombre, r.abreviatura rol FROM usuario u "
            "JOIN rol r ON r.id=u.rol_id WHERE u.id=?", (uid,)).fetchone()
        if not u:
            return jsonify({"detail": "Usuario no encontrado."}), 404
        motivo = cuerpo.get("motivo", "").strip()
        c.execute(
            "UPDATE usuario SET estado=?, notas=CASE WHEN ?<>'' THEN ? ELSE notas END, "
            "actualizado=datetime('now','localtime') WHERE id=?",
            (nuevo, motivo, motivo, uid))
        c.commit()
        accion = "REVOCACION" if nuevo == "Revocado" else "MODIFICACION"
        audit("usuario", accion,
              f"{u['nombre']} ({u['rol']}) → estado {nuevo} vía API."
              + (f" Motivo: {motivo}" if motivo else ""))
        return jsonify({"id": uid, "estado": nuevo})

    @app.route("/api/usuarios/<int:uid>", methods=["DELETE"])
    def api_usuario_eliminar(uid):
        c = db()
        u = c.execute(
            "SELECT u.nombre, r.abreviatura rol FROM usuario u "
            "JOIN rol r ON r.id=u.rol_id WHERE u.id=?", (uid,)).fetchone()
        if not u:
            return jsonify({"detail": "Usuario no encontrado."}), 404
        c.execute("DELETE FROM usuario WHERE id=?", (uid,))
        c.commit()
        audit("usuario", "ELIMINACION",
              f"Usuario {u['nombre']} ({u['rol']}) eliminado del registro vía API. "
              "La bitácora conserva sus movimientos previos.")
        return jsonify({"id": uid, "eliminado": True})

    # ---------------------------------------------------------------- matriz
    @app.route("/api/matriz")
    def api_matriz():
        c = db()
        grupo = request.args.get("grupo", "")
        categoria = request.args.get("categoria", "")

        q_rol = ("SELECT r.*, g.nombre grupo, g.codigo gcod FROM rol r "
                 "JOIN grupo_rol g ON g.id=r.grupo_id WHERE r.activo=1")
        p = []
        if grupo:
            q_rol += " AND g.codigo=?"
            p.append(grupo)
        roles = [dict(r) for r in c.execute(q_rol + " ORDER BY r.id", p)]

        q_sis = ("SELECT s.*, c.nombre categoria FROM sistema s "
                 "JOIN categoria_sistema c ON c.id=s.categoria_id WHERE s.activo=1")
        p2 = []
        if categoria:
            q_sis += " AND c.nombre=?"
            p2.append(categoria)
        sistemas = [dict(r) for r in c.execute(q_sis + " ORDER BY s.id", p2)]

        celdas = {f"{m['rol_id']}:{m['sistema_id']}": m["nivel_codigo"]
                  for m in c.execute("SELECT * FROM matriz_acceso")}
        niveles = [dict(r) for r in c.execute("SELECT * FROM nivel_acceso ORDER BY orden")]
        return jsonify({"roles": roles, "sistemas": sistemas, "celdas": celdas, "niveles": niveles})

    @app.route("/api/matriz/heatmap")
    def api_matriz_heatmap():
        """Accesos nivel Admin (A) por categoría de sistema — vista resumida."""
        c = db()
        filas = c.execute(
            """SELECT cat.nombre categoria,
                      COUNT(DISTINCT s.id) sistemas,
                      SUM(CASE WHEN ma.nivel_codigo='A' THEN 1 ELSE 0 END) n_admin,
                      SUM(CASE WHEN ma.nivel_codigo NOT IN ('—','L') THEN 1 ELSE 0 END) n_elevados
               FROM sistema s
               JOIN categoria_sistema cat ON cat.id = s.categoria_id
               JOIN matriz_acceso ma ON ma.sistema_id = s.id
               JOIN rol r ON r.id = ma.rol_id AND r.activo = 1
               WHERE s.activo = 1
               GROUP BY cat.id ORDER BY n_admin DESC, cat.nombre"""
        ).fetchall()
        return jsonify([dict(r) for r in filas])

    @app.route("/api/matriz/comparar")
    def api_matriz_comparar():
        """Version en JSON de matriz_comparar() — util para revisiones de
        minimo privilegio (comparar dos roles parecidos), sin equivalente
        en la API hasta ahora, solo en la vista HTML."""
        c = db()
        try:
            rol_a_id = int(request.args["rol_a"])
            rol_b_id = int(request.args["rol_b"])
        except (KeyError, ValueError):
            return jsonify({"detail": "Indique rol_a y rol_b (ids numéricos)."}), 400

        rol_a = c.execute("SELECT id, abreviatura, denominacion FROM rol WHERE id=?",
                          (rol_a_id,)).fetchone()
        rol_b = c.execute("SELECT id, abreviatura, denominacion FROM rol WHERE id=?",
                          (rol_b_id,)).fetchone()
        if not rol_a or not rol_b:
            return jsonify({"detail": "Uno de los roles seleccionados ya no existe."}), 404

        niveles_a = {m["sistema_id"]: m["nivel_codigo"] for m in c.execute(
            "SELECT sistema_id, nivel_codigo FROM matriz_acceso WHERE rol_id=?", (rol_a_id,))}
        niveles_b = {m["sistema_id"]: m["nivel_codigo"] for m in c.execute(
            "SELECT sistema_id, nivel_codigo FROM matriz_acceso WHERE rol_id=?", (rol_b_id,))}
        sistemas = c.execute(
            """SELECT s.id, s.nombre, cat.nombre categoria FROM sistema s
               JOIN categoria_sistema cat ON cat.id=s.categoria_id
               WHERE s.activo=1 ORDER BY cat.nombre, s.nombre""").fetchall()

        filas = []
        for s in sistemas:
            na = niveles_a.get(s["id"], "—")
            nb = niveles_b.get(s["id"], "—")
            filas.append({"sistema": s["nombre"], "categoria": s["categoria"],
                          "nivel_a": na, "nivel_b": nb, "difiere": na != nb})

        return jsonify({
            "rol_a": dict(rol_a), "rol_b": dict(rol_b), "filas": filas,
            "num_diferencias": sum(1 for f in filas if f["difiere"]),
        })

    @app.route("/api/matriz", methods=["PUT"])
    def api_matriz_editar():
        c = db()
        cuerpo = request.get_json(silent=True) or {}
        try:
            rol_id = int(cuerpo.get("rol_id"))
            sistema_id = int(cuerpo.get("sistema_id"))
        except (TypeError, ValueError):
            return jsonify({"detail": "Rol o sistema inválido."}), 400
        nivel = cuerpo.get("nivel", "")
        if not c.execute("SELECT 1 FROM nivel_acceso WHERE codigo=?", (nivel,)).fetchone():
            return jsonify({"detail": "Nivel de acceso no reconocido."}), 400
        rol = c.execute("SELECT abreviatura FROM rol WHERE id=?", (rol_id,)).fetchone()
        sis = c.execute("SELECT nombre FROM sistema WHERE id=?", (sistema_id,)).fetchone()
        if not rol or not sis:
            return jsonify({"detail": "Rol o sistema no encontrado."}), 404
        prev = c.execute(
            "SELECT nivel_codigo FROM matriz_acceso WHERE rol_id=? AND sistema_id=?",
            (rol_id, sistema_id)).fetchone()
        anterior = prev["nivel_codigo"] if prev else "—"
        c.execute(
            "UPDATE matriz_acceso SET nivel_codigo=? WHERE rol_id=? AND sistema_id=?",
            (nivel, rol_id, sistema_id))
        c.commit()
        audit("matriz_acceso", "MODIFICACION",
              f"{rol['abreviatura']} × {sis['nombre']}: {anterior} → {nivel} vía API")
        return jsonify({"rol_id": rol_id, "sistema_id": sistema_id,
                        "anterior": anterior, "nuevo": nivel})

    @app.route("/api/matriz/importar/analizar", methods=["POST"])
    def api_matriz_importar_analizar():
        c = db()
        archivo = request.files.get("archivo")
        if not archivo or not archivo.filename:
            return jsonify({"detail": "Seleccione un archivo CSV para importar."}), 400
        try:
            texto = archivo.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return jsonify({"detail": "No se pudo leer el archivo: use codificación "
                            "UTF-8 (el mismo formato que genera «Exportar matriz»)."}), 400
        resultado = negocio.analizar_importacion_matriz(c, texto)
        if resultado[0] is None:
            return jsonify({"detail": resultado[1]}), 400
        cambios, errores = resultado
        return jsonify({"cambios": cambios, "errores": errores,
                        "total_cambios": len(cambios)})

    @app.route("/api/matriz/importar/confirmar", methods=["POST"])
    def api_matriz_importar_confirmar():
        c = db()
        cuerpo = request.get_json(silent=True) or {}
        cambios = cuerpo.get("cambios") or []
        if not isinstance(cambios, list) or not cambios:
            return jsonify({"detail": "No hay cambios para aplicar."}), 400
        aplicados = negocio.aplicar_importacion_matriz(c, cambios, audit)
        if not aplicados:
            return jsonify({"detail": "No se aplicó ningún cambio."}), 400
        return jsonify({"aplicados": aplicados})

    @app.route("/api/export/matriz.csv")
    def api_export_matriz():
        c = db()
        roles = c.execute("SELECT id, abreviatura FROM rol ORDER BY id").fetchall()
        sistemas = c.execute("SELECT id, nombre FROM sistema ORDER BY id").fetchall()
        celdas = {(m["rol_id"], m["sistema_id"]): m["nivel_codigo"]
                  for m in c.execute("SELECT * FROM matriz_acceso")}
        filas = [[s["nombre"]] + [celdas.get((r["id"], s["id"]), "—")
                                  for r in roles] for s in sistemas]
        return negocio.csv_response(
            "SUIIN-SGSI-MCA-001_matriz.csv",
            ["Sistema"] + [r["abreviatura"] for r in roles], filas)

    @app.route("/api/export/accesos_usuarios.csv")
    def api_export_accesos():
        filas = db().execute(
            "SELECT usuario, estado, rol, sistema, categoria, clasificacion, nivel, "
            "CASE es_excepcion WHEN 1 THEN 'Sí' ELSE '' END "
            "FROM v_accesos_usuario ORDER BY usuario, sistema").fetchall()
        return negocio.csv_response(
            "SUIIN-SGSI-MCA-001_accesos_efectivos.csv",
            ["Usuario", "Estado", "Rol", "Sistema", "Categoría",
             "Clasificación", "Nivel", "Excepción"],
            [list(f) for f in filas])

    # ------------------------------------------------------------ excepciones
    @app.route("/api/excepciones")
    def api_excepciones_lista():
        """Antes solo traía las columnas crudas de acceso_excepcion — sin
        el nivel que otorga el rol (para comparar), el estado del usuario,
        el indicador de vencida, ni el filtro/los totales que ya tenía la
        vista HTML. Se iguala aquí para que la pantalla de React tenga la
        misma información."""
        c = db()
        incluir_vencidas = request.args.get("vencidas") == "1"
        sql = """SELECT u.id usuario_id, u.nombre usuario, u.estado usuario_estado,
                        s.id sistema_id, s.nombre sistema, r.abreviatura rol,
                        COALESCE(ma.nivel_codigo, '—') nivel_rol,
                        e.nivel_codigo nivel_excepcion, e.motivo, e.fecha_fin, e.creado,
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
        filas = [dict(r) for r in c.execute(sql)]
        for f in filas:
            f["vencida"] = bool(f["vencida"])
        total_vigentes = c.execute(
            "SELECT COUNT(*) n FROM acceso_excepcion "
            "WHERE fecha_fin IS NULL OR date(fecha_fin) >= date('now')").fetchone()["n"]
        total_vencidas = c.execute(
            "SELECT COUNT(*) n FROM acceso_excepcion "
            "WHERE fecha_fin IS NOT NULL AND date(fecha_fin) < date('now')").fetchone()["n"]
        return jsonify({"filas": filas, "total_vigentes": total_vigentes,
                        "total_vencidas": total_vencidas})

    @app.route("/api/excepciones/masiva", methods=["POST"])
    def api_excepcion_masiva():
        """Version en JSON de excepcion_masiva_aplicar() — no existia
        ningun endpoint API para la asignacion masiva, solo la vista HTML."""
        c = db()
        cuerpo = request.get_json(silent=True) or {}
        motivo = (cuerpo.get("motivo") or "").strip()
        if not motivo:
            return jsonify({"detail": "Toda excepción debe registrar un motivo (control 5.18)."}), 400
        try:
            sistema_id = int(cuerpo.get("sistema_id"))
        except (TypeError, ValueError):
            return jsonify({"detail": "Sistema inválido."}), 400
        nivel = cuerpo.get("nivel", "")
        fecha_fin = cuerpo.get("fecha_fin") or None
        if not negocio._fecha_valida(fecha_fin):
            return jsonify({"detail": "La fecha debe tener el formato AAAA-MM-DD."}), 400
        s = c.execute("SELECT nombre FROM sistema WHERE id=?", (sistema_id,)).fetchone()
        if not s or not c.execute("SELECT 1 FROM nivel_acceso WHERE codigo=?", (nivel,)).fetchone():
            return jsonify({"detail": "Sistema o nivel no válido."}), 404
        ids = [i for i in (cuerpo.get("usuario_ids") or []) if isinstance(i, int)]
        if not ids:
            return jsonify({"detail": "Seleccione al menos un usuario."}), 400

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
                  f"Excepción de acceso (asignación masiva vía API): {u['nombre']} sobre "
                  f"«{s['nombre']}» → {nivel} (el rol {u['rol']} otorga {nivel_rol}). "
                  f"Motivo: {motivo}")
            aplicados += 1
        c.commit()
        return jsonify({"aplicados": aplicados, "sistema": s["nombre"]}), 201

    @app.route("/api/usuarios/<int:uid>/excepciones", methods=["POST"])
    def api_excepcion_crear(uid):
        c = db()
        cuerpo = request.get_json(silent=True) or {}
        motivo = cuerpo.get("motivo", "").strip()
        if not motivo:
            return jsonify({"detail": "Toda excepción debe registrar un motivo (control 5.18)."}), 400
        try:
            sistema_id = int(cuerpo.get("sistema_id"))
        except (TypeError, ValueError):
            return jsonify({"detail": "Sistema inválido."}), 400
        nivel = cuerpo.get("nivel", "")
        fecha_fin = cuerpo.get("fecha_fin") or None
        if not negocio._fecha_valida(fecha_fin):
            return jsonify({"detail": "La fecha debe tener el formato AAAA-MM-DD."}), 400

        u = c.execute(
            "SELECT u.nombre, u.rol_id, r.abreviatura rol FROM usuario u "
            "JOIN rol r ON r.id=u.rol_id WHERE u.id=?", (uid,)).fetchone()
        s = c.execute("SELECT nombre FROM sistema WHERE id=?", (sistema_id,)).fetchone()
        if not u or not s or not c.execute(
                "SELECT 1 FROM nivel_acceso WHERE codigo=?", (nivel,)).fetchone():
            return jsonify({"detail": "Usuario, sistema o nivel no válido."}), 404
        fila_rol = c.execute(
            "SELECT nivel_codigo FROM matriz_acceso WHERE rol_id=? AND sistema_id=?",
            (u["rol_id"], sistema_id)).fetchone()
        nivel_rol = fila_rol["nivel_codigo"] if fila_rol else "—"
        c.execute(
            """INSERT INTO acceso_excepcion (usuario_id, sistema_id, nivel_codigo, motivo, fecha_fin)
               VALUES (?,?,?,?,?)
               ON CONFLICT(usuario_id, sistema_id) DO UPDATE SET
                 nivel_codigo=excluded.nivel_codigo, motivo=excluded.motivo,
                 fecha_fin=excluded.fecha_fin""",
            (uid, sistema_id, nivel, motivo, fecha_fin))
        c.commit()
        audit("usuario", "MODIFICACION",
              f"Excepción de acceso vía API: {u['nombre']} sobre «{s['nombre']}» → "
              f"{nivel} (el rol {u['rol']} otorga {nivel_rol}). Motivo: {motivo}")
        return jsonify({"usuario_id": uid, "sistema_id": sistema_id, "nivel": nivel}), 201

    @app.route("/api/usuarios/<int:uid>/excepciones/<int:sid>", methods=["DELETE"])
    def api_excepcion_eliminar(uid, sid):
        c = db()
        u = c.execute("SELECT nombre FROM usuario WHERE id=?", (uid,)).fetchone()
        s = c.execute("SELECT nombre FROM sistema WHERE id=?", (sid,)).fetchone()
        if not u or not s:
            return jsonify({"detail": "Usuario o sistema no encontrado."}), 404
        c.execute("DELETE FROM acceso_excepcion WHERE usuario_id=? AND sistema_id=?", (uid, sid))
        c.commit()
        audit("usuario", "MODIFICACION",
              f"Excepción retirada vía API: {u['nombre']} sobre «{s['nombre']}» "
              "vuelve al nivel de su rol.")
        return jsonify({"eliminado": True})

    # ---------------------------------------------------------------- auditoría
    @app.route("/api/auditoria")
    def api_auditoria():
        c = db()
        entidad = request.args.get("entidad", "")
        accion = request.args.get("accion", "")
        q = request.args.get("q", "").strip()
        try:
            pagina = max(1, int(request.args.get("pagina", "1")))
        except ValueError:
            pagina = 1
        por_pagina = 50

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
        total = c.execute(sql.replace("SELECT *", "SELECT COUNT(*) n", 1), p).fetchone()["n"]
        offset = (pagina - 1) * por_pagina
        filas = [dict(r) for r in c.execute(
            sql + " ORDER BY id DESC LIMIT ? OFFSET ?", p + [por_pagina, offset])]
        return jsonify({
            "registros": filas, "total": total, "pagina": pagina,
            "total_paginas": max(1, -(-total // por_pagina)),
        })

    @app.route("/api/auditoria/verificar")
    def api_auditoria_verificar():
        ok, dato = verificar_cadena()
        return jsonify({"integra": ok, "detalle": dato})
