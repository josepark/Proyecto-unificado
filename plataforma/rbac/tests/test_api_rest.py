#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas de la API REST en JSON de RBAC (api_rest.py) — fase 1 de la
migración a React. Usa el mismo fixture `cliente` (base temporal aislada,
nunca la real) que el resto de la suite."""
import sqlite3

import pytest

import db as capa_db
import seed


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    ruta = str(tmp_path / "prueba_api.db")
    seed.crear(ruta)
    monkeypatch.setattr(capa_db, "DB", ruta)

    from app import crear_app
    aplicacion = crear_app()
    aplicacion.config["TESTING"] = True
    with aplicacion.test_client() as c:
        yield c


def _csrf(c):
    return c.get("/api/csrf").get_json()["csrf_token"]


def _headers(c):
    return {"X-CSRF-Token": _csrf(c)}


def _rol_valido(**extra):
    datos = {"codigo": "X1", "abreviatura": "PRB", "denominacion": "Rol de prueba",
             "grupo_id": 1, "mfa_requerido": "No", "riesgo_attack": "Bajo",
             "revision_periodica": "Anual"}
    datos.update(extra)
    return datos


# --------------------------------------------------------------- catálogos
def test_csrf_endpoint_devuelve_token(cliente):
    r = cliente.get("/api/csrf")
    assert r.status_code == 200
    assert len(r.get_json()["csrf_token"]) >= 32


def test_catalogos_devuelve_las_listas_esperadas(cliente):
    r = cliente.get("/api/catalogos")
    assert r.status_code == 200
    data = r.get_json()
    for clave in ("grupos_rol", "categorias_sistema", "niveles_acceso",
                  "riesgos_attack", "clasificaciones", "estados_usuario"):
        assert clave in data and len(data[clave]) > 0


def test_api_inicio_expone_los_datos_del_tablero(cliente):
    """No existía ningún equivalente JSON del tablero de Inicio — solo la
    vista HTML. Debe traer las mismas secciones, no solo los KPIs
    agregados que ya daba /api/resumen."""
    r = cliente.get("/api/inicio")
    assert r.status_code == 200
    data = r.get_json()
    for clave in ("stats", "alertas_mfa", "criticos", "temporales",
                  "revocados", "log", "riesgo", "max_riesgo", "mfa_pct",
                  "mfa_ok", "mfa_total", "proximos_vencimientos", "dias_alerta"):
        assert clave in data
    for clave in ("roles", "sistemas", "usuarios", "accesos"):
        assert clave in data["stats"]
    assert len(data["riesgo"]) == 3
    assert {"nombre", "n", "color"} <= data["riesgo"][0].keys()


# ------------------------------------------------------------------ roles
def test_lista_roles_devuelve_solo_activos_por_defecto(cliente):
    r = cliente.get("/api/roles")
    assert r.status_code == 200
    assert all(rol["activo"] for rol in r.get_json())


def test_lista_roles_filtra_por_busqueda(cliente):
    todos = cliente.get("/api/roles").get_json()
    alguno = todos[0]
    r = cliente.get(f"/api/roles?q={alguno['abreviatura']}")
    assert any(x["id"] == alguno["id"] for x in r.get_json())


def test_detalle_rol_incluye_accesos_y_usuarios(cliente):
    algun_id = cliente.get("/api/roles").get_json()[0]["id"]
    r = cliente.get(f"/api/roles/{algun_id}")
    assert r.status_code == 200
    data = r.get_json()
    assert "accesos" in data and "usuarios" in data
    assert "revision_vencida" in data


def test_detalle_rol_inexistente_404(cliente):
    r = cliente.get("/api/roles/999999")
    assert r.status_code == 404


def test_crear_rol_sin_csrf_rechazado(cliente):
    r = cliente.post("/api/roles", json=_rol_valido())
    assert r.status_code == 403


def test_crear_rol_con_csrf_funciona(cliente):
    r = cliente.post("/api/roles", headers=_headers(cliente), json=_rol_valido())
    assert r.status_code == 201
    assert r.get_json()["abreviatura"] == "PRB"

    # y aparece en la lista
    lista = cliente.get("/api/roles").get_json()
    assert any(x["abreviatura"] == "PRB" for x in lista)


def test_crear_rol_datos_invalidos_devuelve_400(cliente):
    malo = _rol_valido(riesgo_attack="Inventado")
    r = cliente.post("/api/roles", headers=_headers(cliente), json=malo)
    assert r.status_code == 400


def test_crear_rol_codigo_duplicado_devuelve_409(cliente):
    h = _headers(cliente)
    cliente.post("/api/roles", headers=h, json=_rol_valido())
    r = cliente.post("/api/roles", headers=h, json=_rol_valido(abreviatura="OTRA"))
    assert r.status_code == 409


def test_editar_rol(cliente):
    h = _headers(cliente)
    creado = cliente.post("/api/roles", headers=h, json=_rol_valido()).get_json()
    r = cliente.put(f"/api/roles/{creado['id']}", headers=h,
                    json=_rol_valido(denominacion="Rol de prueba editado", riesgo_attack="Alto"))
    assert r.status_code == 200
    assert r.get_json()["denominacion"] == "Rol de prueba editado"
    assert r.get_json()["riesgo_attack"] == "Alto"


def test_certificar_rol_actualiza_revision_vencida(cliente):
    h = _headers(cliente)
    creado = cliente.post("/api/roles", headers=h, json=_rol_valido()).get_json()
    antes = cliente.get(f"/api/roles/{creado['id']}").get_json()
    assert antes["revision_vencida"] == 1  # nunca revisado

    r = cliente.post(f"/api/roles/{creado['id']}/certificar", headers=h, json={"nota": "ok"})
    assert r.status_code == 200

    despues = cliente.get(f"/api/roles/{creado['id']}").get_json()
    assert despues["revision_vencida"] == 0


def test_baja_logica_rol(cliente):
    h = _headers(cliente)
    creado = cliente.post("/api/roles", headers=h, json=_rol_valido()).get_json()
    r = cliente.delete(f"/api/roles/{creado['id']}/activo", headers=h)
    assert r.status_code == 200
    assert r.get_json()["activo"] is False

    assert creado["id"] not in [x["id"] for x in cliente.get("/api/roles").get_json()]
    assert creado["id"] in [x["id"] for x in
                            cliente.get("/api/roles?incluir_inactivos=1").get_json()]


def test_crear_rol_inicializa_fila_en_la_matriz(cliente):
    """Antes de este arreglo, un rol creado por la API quedaba sin NINGUNA
    fila en matriz_acceso (a diferencia de crearlo desde el formulario
    HTML) — la matriz debe tener una celda '—' por cada sistema activo."""
    h = _headers(cliente)
    creado = cliente.post("/api/roles", headers=h, json=_rol_valido()).get_json()
    n_sistemas = len(cliente.get("/api/sistemas").get_json())

    matriz = cliente.get("/api/matriz").get_json()
    celdas_del_rol = [k for k in matriz["celdas"] if k.startswith(f"{creado['id']}:")]
    assert len(celdas_del_rol) == n_sistemas
    assert all(v == "—" for k, v in matriz["celdas"].items() if k in celdas_del_rol)


def test_crear_rol_clonando_copia_los_accesos_del_origen(cliente):
    h = _headers(cliente)
    # Rol origen con al menos un acceso real (no '—') para clonar.
    origen = cliente.post("/api/roles", headers=h,
                          json=_rol_valido(codigo="X1", abreviatura="ORI")).get_json()
    sistema_id = cliente.get("/api/sistemas").get_json()[0]["id"]
    cliente.put("/api/matriz", headers=h,
               json={"rol_id": origen["id"], "sistema_id": sistema_id, "nivel": "C"})

    clon = cliente.post("/api/roles", headers=h,
                        json=_rol_valido(codigo="X2", abreviatura="CLN",
                                        clonar_de=str(origen["id"]))).get_json()

    matriz = cliente.get("/api/matriz").get_json()
    assert matriz["celdas"][f"{clon['id']}:{sistema_id}"] == "C"


def test_crear_rol_clonando_de_id_inexistente_da_400(cliente):
    h = _headers(cliente)
    r = cliente.post("/api/roles", headers=h,
                     json=_rol_valido(abreviatura="CLX", clonar_de="999999"))
    assert r.status_code == 400


def test_eliminar_rol_sin_usuarios_funciona(cliente):
    h = _headers(cliente)
    creado = cliente.post("/api/roles", headers=h, json=_rol_valido()).get_json()
    r = cliente.delete(f"/api/roles/{creado['id']}", headers=h)
    assert r.status_code == 204
    assert creado["id"] not in [x["id"] for x in
                                cliente.get("/api/roles?incluir_inactivos=1").get_json()]


def test_eliminar_rol_inexistente_da_404(cliente):
    h = _headers(cliente)
    r = cliente.delete("/api/roles/999999", headers=h)
    assert r.status_code == 404


def test_eliminar_rol_con_usuarios_devuelve_409(cliente):
    h = _headers(cliente)
    creado = cliente.post("/api/roles", headers=h, json=_rol_valido()).get_json()
    cliente.post("/api/usuarios", headers=h,
                json={"nombre": "Persona de prueba", "rol_id": creado["id"], "estado": "Activo"})
    r = cliente.delete(f"/api/roles/{creado['id']}", headers=h)
    assert r.status_code == 409
    # y sigue existiendo
    assert creado["id"] in [x["id"] for x in
                            cliente.get("/api/roles?incluir_inactivos=1").get_json()]


def test_eliminar_rol_sin_csrf_rechazado(cliente):
    creado = cliente.post("/api/roles", headers=_headers(cliente), json=_rol_valido()).get_json()
    r = cliente.delete(f"/api/roles/{creado['id']}")
    assert r.status_code == 403


def test_baja_logica_rechazada_si_tiene_usuarios_activos(cliente):
    # buscar un rol de la semilla que sí tenga usuarios activos asignados
    con = sqlite3.connect(capa_db.DB)
    rid = con.execute(
        "SELECT rol_id FROM usuario WHERE estado IN ('Activo','Temporal') LIMIT 1"
    ).fetchone()[0]
    r = cliente.delete(f"/api/roles/{rid}/activo", headers=_headers(cliente))
    assert r.status_code == 409


def test_escrituras_de_la_api_quedan_en_la_bitacora(cliente):
    h = _headers(cliente)
    cliente.post("/api/roles", headers=h, json=_rol_valido())
    con = sqlite3.connect(capa_db.DB)
    detalle = con.execute(
        "SELECT detalle FROM log_auditoria ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert "PRB" in detalle and "API" in detalle


# --------------------------------------------------------------- sistemas
def _sistema_valido(**extra):
    datos = {"nombre": "Sistema de Prueba API", "clasificacion": "Interna",
             "categoria_id": 1}
    datos.update(extra)
    return datos


def test_crear_sistema(cliente):
    r = cliente.post("/api/sistemas", headers=_headers(cliente), json=_sistema_valido())
    assert r.status_code == 201
    sid = r.get_json()["id"]
    # queda con matriz inicializada en '—' para todos los roles
    con = sqlite3.connect(capa_db.DB)
    n_roles = con.execute("SELECT COUNT(*) FROM rol").fetchone()[0]
    n_celdas = con.execute("SELECT COUNT(*) FROM matriz_acceso WHERE sistema_id=?", (sid,)).fetchone()[0]
    assert n_celdas == n_roles


def test_crear_sistema_clasificacion_invalida_400(cliente):
    r = cliente.post("/api/sistemas", headers=_headers(cliente),
                     json=_sistema_valido(clasificacion="Inventada"))
    assert r.status_code == 400


def test_detalle_sistema_incluye_roles_y_usuarios(cliente):
    """No existía ningún GET /api/sistemas/<id> — solo escritura."""
    h = _headers(cliente)
    creado = cliente.post("/api/sistemas", headers=h, json=_sistema_valido()).get_json()
    r = cliente.get(f"/api/sistemas/{creado['id']}")
    assert r.status_code == 200
    data = r.get_json()
    for clave in ("nombre", "categoria", "categoria_id", "clasificacion",
                  "tecnicas_attack", "activo", "roles", "usuarios"):
        assert clave in data
    assert data["nombre"] == _sistema_valido()["nombre"]


def test_detalle_sistema_inexistente_404(cliente):
    r = cliente.get("/api/sistemas/999999")
    assert r.status_code == 404


def test_lista_sistemas_incluye_campos_nuevos_sin_romper_los_existentes(cliente):
    """El endpoint ya lo consumía el Inventario server-a-server — los
    campos nuevos deben ser aditivos, nunca reemplazar los que ya había."""
    r = cliente.get("/api/sistemas")
    assert r.status_code == 200
    primero = r.get_json()[0]
    originales = {"id", "nombre", "categoria", "clasificacion", "accesos", "excepciones_vigentes"}
    nuevos = {"categoria_id", "tecnicas_attack", "activo", "n_roles"}
    assert originales <= primero.keys()
    assert nuevos <= primero.keys()


def test_lista_sistemas_excluye_inactivos_por_defecto(cliente):
    h = _headers(cliente)
    creado = cliente.post("/api/sistemas", headers=h, json=_sistema_valido()).get_json()
    cliente.delete(f"/api/sistemas/{creado['id']}/activo", headers=h)  # desactivar

    sin_inactivos = cliente.get("/api/sistemas").get_json()
    assert creado["id"] not in [s["id"] for s in sin_inactivos]

    con_inactivos = cliente.get("/api/sistemas?incluir_inactivos=1").get_json()
    assert creado["id"] in [s["id"] for s in con_inactivos]


def test_editar_sistema(cliente):
    h = _headers(cliente)
    creado = cliente.post("/api/sistemas", headers=h, json=_sistema_valido()).get_json()
    r = cliente.put(f"/api/sistemas/{creado['id']}", headers=h,
                    json=_sistema_valido(nombre="Sistema Renombrado"))
    assert r.status_code == 200
    assert r.get_json()["nombre"] == "Sistema Renombrado"


def test_desactivar_reactivar_sistema(cliente):
    h = _headers(cliente)
    creado = cliente.post("/api/sistemas", headers=h, json=_sistema_valido()).get_json()
    r1 = cliente.delete(f"/api/sistemas/{creado['id']}/activo", headers=h)
    assert r1.status_code == 200 and r1.get_json()["activo"] is False
    r2 = cliente.delete(f"/api/sistemas/{creado['id']}/activo", headers=h)
    assert r2.status_code == 200 and r2.get_json()["activo"] is True


def test_eliminar_sistema_sin_excepciones(cliente):
    h = _headers(cliente)
    creado = cliente.post("/api/sistemas", headers=h, json=_sistema_valido()).get_json()
    r = cliente.delete(f"/api/sistemas/{creado['id']}", headers=h)
    assert r.status_code == 200
    assert r.get_json()["eliminado"] is True


def test_eliminar_sistema_con_excepciones_rechazado(cliente):
    h = _headers(cliente)
    uid = cliente.get("/api/usuarios").get_json()[0]["id"]
    sid = cliente.get("/api/sistemas").get_json()[0]["id"]
    cliente.post(f"/api/usuarios/{uid}/excepciones", headers=h,
                json={"sistema_id": sid, "nivel": "L", "motivo": "prueba"})
    r = cliente.delete(f"/api/sistemas/{sid}", headers=h)
    assert r.status_code == 409


# --------------------------------------------------------------- usuarios
def _usuario_valido(rol_id, **extra):
    datos = {"nombre": "Usuario de Prueba API", "rol_id": rol_id, "estado": "Activo"}
    datos.update(extra)
    return datos


def _algun_rol_id(cliente):
    return cliente.get("/api/roles").get_json()[0]["id"]


def test_lista_usuarios(cliente):
    r = cliente.get("/api/usuarios")
    assert r.status_code == 200
    assert len(r.get_json()) > 0


def test_crear_usuario(cliente):
    rid = _algun_rol_id(cliente)
    r = cliente.post("/api/usuarios", headers=_headers(cliente), json=_usuario_valido(rid))
    assert r.status_code == 201
    assert r.get_json()["nombre"] == "Usuario de Prueba API"


def test_crear_usuario_temporal_exige_fechas(cliente):
    rid = _algun_rol_id(cliente)
    r = cliente.post("/api/usuarios", headers=_headers(cliente),
                     json=_usuario_valido(rid, estado="Temporal"))
    assert r.status_code == 400


def test_crear_usuario_temporal_con_fechas_funciona(cliente):
    rid = _algun_rol_id(cliente)
    r = cliente.post("/api/usuarios", headers=_headers(cliente),
                     json=_usuario_valido(rid, estado="Temporal",
                                         fecha_inicio="2026-01-01", fecha_fin="2026-06-01"))
    assert r.status_code == 201


def test_detalle_usuario_incluye_accesos(cliente):
    algun_id = cliente.get("/api/usuarios").get_json()[0]["id"]
    r = cliente.get(f"/api/usuarios/{algun_id}")
    assert r.status_code == 200
    assert "accesos" in r.get_json()


def test_editar_usuario(cliente):
    h = _headers(cliente)
    rid = _algun_rol_id(cliente)
    creado = cliente.post("/api/usuarios", headers=h, json=_usuario_valido(rid)).get_json()
    r = cliente.put(f"/api/usuarios/{creado['id']}", headers=h,
                    json=_usuario_valido(rid, nombre="Nombre Editado"))
    assert r.status_code == 200
    assert r.get_json()["nombre"] == "Nombre Editado"


def test_cambiar_estado_usuario(cliente):
    h = _headers(cliente)
    rid = _algun_rol_id(cliente)
    creado = cliente.post("/api/usuarios", headers=h, json=_usuario_valido(rid)).get_json()
    r = cliente.put(f"/api/usuarios/{creado['id']}/estado", headers=h,
                    json={"estado": "Suspendido", "motivo": "prueba"})
    assert r.status_code == 200
    assert r.get_json()["estado"] == "Suspendido"


def test_eliminar_usuario(cliente):
    h = _headers(cliente)
    rid = _algun_rol_id(cliente)
    creado = cliente.post("/api/usuarios", headers=h, json=_usuario_valido(rid)).get_json()
    r = cliente.delete(f"/api/usuarios/{creado['id']}", headers=h)
    assert r.status_code == 200
    assert cliente.get(f"/api/usuarios/{creado['id']}").status_code == 404


# ----------------------------------------------------------------- matriz
def test_matriz_devuelve_roles_sistemas_y_celdas(cliente):
    r = cliente.get("/api/matriz")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data["roles"]) > 0 and len(data["sistemas"]) > 0 and len(data["celdas"]) > 0


def test_matriz_comparar_detecta_diferencias(cliente):
    """No existía ningún equivalente JSON de matriz_comparar() — solo la
    vista HTML (comparación de dos roles para revisiones de mínimo
    privilegio)."""
    h = _headers(cliente)
    m = cliente.get("/api/matriz").get_json()
    rol_a, rol_b = m["roles"][0], m["roles"][1]
    sistema_id = m["sistemas"][0]["id"]
    # Aseguramos una diferencia real entre ambos roles en ese sistema
    cliente.put("/api/matriz", headers=h,
               json={"rol_id": rol_a["id"], "sistema_id": sistema_id, "nivel": "A"})
    cliente.put("/api/matriz", headers=h,
               json={"rol_id": rol_b["id"], "sistema_id": sistema_id, "nivel": "L"})

    r = cliente.get(f"/api/matriz/comparar?rol_a={rol_a['id']}&rol_b={rol_b['id']}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["rol_a"]["abreviatura"] == rol_a["abreviatura"]
    assert data["rol_b"]["abreviatura"] == rol_b["abreviatura"]
    assert data["num_diferencias"] >= 1
    fila = next(f for f in data["filas"] if f["sistema"] == m["sistemas"][0]["nombre"])
    assert fila["nivel_a"] == "A" and fila["nivel_b"] == "L" and fila["difiere"] is True


def test_matriz_comparar_sin_parametros_da_400(cliente):
    r = cliente.get("/api/matriz/comparar")
    assert r.status_code == 400


def test_matriz_comparar_rol_inexistente_da_404(cliente):
    m = cliente.get("/api/matriz").get_json()
    r = cliente.get(f"/api/matriz/comparar?rol_a=999999&rol_b={m['roles'][0]['id']}")
    assert r.status_code == 404


def test_editar_celda_de_matriz(cliente):
    m = cliente.get("/api/matriz").get_json()
    rol_id, sistema_id = m["roles"][0]["id"], m["sistemas"][0]["id"]
    r = cliente.put("/api/matriz", headers=_headers(cliente),
                    json={"rol_id": rol_id, "sistema_id": sistema_id, "nivel": "L"})
    assert r.status_code == 200
    assert r.get_json()["nuevo"] == "L"

    m2 = cliente.get("/api/matriz").get_json()
    assert m2["celdas"][f"{rol_id}:{sistema_id}"] == "L"


def test_editar_celda_nivel_invalido_400(cliente):
    m = cliente.get("/api/matriz").get_json()
    rol_id, sistema_id = m["roles"][0]["id"], m["sistemas"][0]["id"]
    r = cliente.put("/api/matriz", headers=_headers(cliente),
                    json={"rol_id": rol_id, "sistema_id": sistema_id, "nivel": "Z"})
    assert r.status_code == 400


# ------------------------------------------------------------ excepciones
def test_lista_excepciones(cliente):
    h = _headers(cliente)
    uid = cliente.get("/api/usuarios").get_json()[0]["id"]
    sid = cliente.get("/api/sistemas").get_json()[0]["id"]
    cliente.post(f"/api/usuarios/{uid}/excepciones", headers=h,
                json={"sistema_id": sid, "nivel": "L", "motivo": "prueba"})
    r = cliente.get("/api/excepciones")
    assert r.status_code == 200
    data = r.get_json()
    assert set(data.keys()) == {"filas", "total_vigentes", "total_vencidas"}
    assert len(data["filas"]) > 0
    assert data["total_vigentes"] > 0
    fila = data["filas"][0]
    for clave in ("usuario", "usuario_estado", "sistema", "rol", "nivel_rol",
                  "nivel_excepcion", "motivo", "vencida"):
        assert clave in fila
    assert fila["vencida"] is False


def test_lista_excepciones_excluye_vencidas_por_defecto(cliente):
    h = _headers(cliente)
    uid = cliente.get("/api/usuarios").get_json()[0]["id"]
    sid = cliente.get("/api/sistemas").get_json()[0]["id"]
    cliente.post(f"/api/usuarios/{uid}/excepciones", headers=h,
                json={"sistema_id": sid, "nivel": "L", "motivo": "vencida",
                     "fecha_fin": "2020-01-01"})

    sin_vencidas = cliente.get("/api/excepciones").get_json()
    assert sin_vencidas["total_vencidas"] == 1
    assert not any(f["vencida"] for f in sin_vencidas["filas"])

    con_vencidas = cliente.get("/api/excepciones?vencidas=1").get_json()
    assert any(f["vencida"] for f in con_vencidas["filas"])


def test_excepcion_masiva_aplica_a_varios_usuarios(cliente):
    h = _headers(cliente)
    usuarios = cliente.get("/api/usuarios").get_json()[:2]
    sid = cliente.get("/api/sistemas").get_json()[0]["id"]
    r = cliente.post("/api/excepciones/masiva", headers=h, json={
        "sistema_id": sid, "nivel": "L", "motivo": "asignación grupal de prueba",
        "usuario_ids": [u["id"] for u in usuarios],
    })
    assert r.status_code == 201
    assert r.get_json()["aplicados"] == 2

    filas = cliente.get("/api/excepciones").get_json()["filas"]
    ids_con_excepcion = {f["usuario_id"] for f in filas if f["sistema_id"] == sid}
    assert {u["id"] for u in usuarios} <= ids_con_excepcion


def test_excepcion_masiva_sin_motivo_da_400(cliente):
    h = _headers(cliente)
    sid = cliente.get("/api/sistemas").get_json()[0]["id"]
    r = cliente.post("/api/excepciones/masiva", headers=h,
                     json={"sistema_id": sid, "nivel": "L", "motivo": "", "usuario_ids": [1]})
    assert r.status_code == 400


def test_excepcion_masiva_sin_usuarios_da_400(cliente):
    h = _headers(cliente)
    sid = cliente.get("/api/sistemas").get_json()[0]["id"]
    r = cliente.post("/api/excepciones/masiva", headers=h,
                     json={"sistema_id": sid, "nivel": "L", "motivo": "ok", "usuario_ids": []})
    assert r.status_code == 400


def test_excepcion_masiva_sin_csrf_rechazada(cliente):
    sid = cliente.get("/api/sistemas").get_json()[0]["id"]
    r = cliente.post("/api/excepciones/masiva",
                     json={"sistema_id": sid, "nivel": "L", "motivo": "ok", "usuario_ids": [1]})
    assert r.status_code == 403


def test_crear_excepcion_sin_motivo_400(cliente):
    uid = cliente.get("/api/usuarios").get_json()[0]["id"]
    sid = cliente.get("/api/sistemas").get_json()[0]["id"]
    r = cliente.post(f"/api/usuarios/{uid}/excepciones", headers=_headers(cliente),
                     json={"sistema_id": sid, "nivel": "L", "motivo": ""})
    assert r.status_code == 400


def test_crear_y_eliminar_excepcion(cliente):
    h = _headers(cliente)
    uid = cliente.get("/api/usuarios").get_json()[0]["id"]
    sid = cliente.get("/api/sistemas").get_json()[0]["id"]
    r = cliente.post(f"/api/usuarios/{uid}/excepciones", headers=h,
                     json={"sistema_id": sid, "nivel": "L", "motivo": "prueba de excepcion"})
    assert r.status_code == 201

    r2 = cliente.delete(f"/api/usuarios/{uid}/excepciones/{sid}", headers=h)
    assert r2.status_code == 200 and r2.get_json()["eliminado"] is True


# ------------------------------------------------------------- auditoría
def test_auditoria_lista_paginada(cliente):
    r = cliente.get("/api/auditoria")
    assert r.status_code == 200
    data = r.get_json()
    assert "registros" in data and "total" in data and data["total"] > 0


def test_auditoria_filtra_por_entidad(cliente):
    r = cliente.get("/api/auditoria?entidad=rol")
    assert all(x["entidad"] == "rol" for x in r.get_json()["registros"])


def test_auditoria_verificar_cadena_integra(cliente):
    r = cliente.get("/api/auditoria/verificar")
    assert r.status_code == 200
    assert r.get_json()["integra"] is True
