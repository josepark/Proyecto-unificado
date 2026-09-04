import pytest
from riesgos.models import Activo, Vulnerabilidad, RiesgoContextual, AccionTratamiento

pytestmark = pytest.mark.django_db


class TestActivoCRUD:
    def test_crear_activo_campana_null_no_falla(self, api_client_autenticado):
        """
        Regresión: un <select> vacío en el frontend manda "" no null, y un
        PrimaryKeyRelatedField rechaza "" con un error de validación. El frontend ya
        lo sanea, pero el backend también debe aceptar null explícito sin problema.
        """
        resp = api_client_autenticado.post("/api/activos/", {
            "id_activo": "CRUD-001", "nombre": "Activo de prueba", "valor": 5,
            "campana_red_team_id": None,
        })
        assert resp.status_code == 201, resp.data

    def test_detalle_incluye_todos_los_campos_para_edicion(self, api_client_autenticado, activo):
        """
        Regresión: el listado usa ActivoListSerializer (liviano); si el frontend abre
        el formulario de edición con esos datos en vez de pedir el detalle, PATCHear
        borraría en silencio los campos que el listado no trae (ej. observacion_critica).
        Este test fija el contrato: el detalle SÍ debe traer esos campos.
        """
        activo.observacion_critica = "Dato que no debe perderse"
        activo.save()
        resp = api_client_autenticado.get(f"/api/activos/{activo.id}/")
        assert resp.status_code == 200
        assert resp.data["observacion_critica"] == "Dato que no debe perderse"
        assert "puertos" in resp.data
        assert "vulnerabilidades" in resp.data

    def test_listado_no_incluye_todos_los_campos(self, api_client_autenticado, activo):
        """Confirma que el listado es efectivamente el serializer liviano (no un test
        trivial: si algún día se iguala list/detail, este test debe fallar y avisar)."""
        resp = api_client_autenticado.get("/api/activos/")
        item = next(a for a in resp.data["results"] if a["id_activo"] == activo.id_activo)
        assert "observacion_critica" not in item

    def test_eliminar_activo_elimina_en_cascada_sus_vulnerabilidades(self, api_client_autenticado, activo):
        Vulnerabilidad.objects.create(activo=activo, nombre_vulnerabilidad="x", probabilidad=1, impacto=1)
        assert Vulnerabilidad.objects.filter(activo=activo).count() == 1
        resp = api_client_autenticado.delete(f"/api/activos/{activo.id}/")
        assert resp.status_code == 204
        assert Vulnerabilidad.objects.filter(activo_id=activo.id).count() == 0

    def test_valor_es_requerido(self, api_client_autenticado):
        resp = api_client_autenticado.post("/api/activos/", {
            "id_activo": "SINVALOR-001", "nombre": "x", "valor": None,
        })
        assert resp.status_code == 400
        assert "valor" in resp.data


class TestRiesgoContextualM2M:
    def test_crear_con_activos_relacionados(self, api_client_autenticado, activo):
        resp = api_client_autenticado.post("/api/riesgos-contextuales/", {
            "id_riesgo_contextual": "RC-CRUD-01", "escenario_amenaza": "Prueba",
            "probabilidad": 3, "impacto": 3, "activos_relacionados": [activo.id],
        })
        assert resp.status_code == 201, resp.data
        assert resp.data["activos_relacionados_resumen"] == [activo.id_activo]

    def test_crear_con_controles_iso_vinculados(self, api_client_autenticado, catalogo_iso_minimo):
        control = catalogo_iso_minimo[0]
        resp = api_client_autenticado.post("/api/riesgos-contextuales/", {
            "id_riesgo_contextual": "RC-CRUD-02", "escenario_amenaza": "Prueba",
            "probabilidad": 2, "impacto": 2, "controles_iso_vinculados": [control.id],
        })
        assert resp.status_code == 201, resp.data
        assert control.codigo in resp.data["controles_iso_vinculados_resumen"][0]

    def test_actualizar_reemplaza_la_lista_de_activos(self, api_client_autenticado, activo):
        rc = RiesgoContextual.objects.create(
            id_riesgo_contextual="RC-CRUD-03", escenario_amenaza="x", probabilidad=1, impacto=1)
        rc.activos_relacionados.add(activo)
        otro = Activo.objects.create(id_activo="CRUD-OTRO", nombre="Otro", valor=1)

        resp = api_client_autenticado.patch(f"/api/riesgos-contextuales/{rc.id}/", {
            "activos_relacionados": [otro.id],
        }, format="json")
        assert resp.status_code == 200
        rc.refresh_from_db()
        assert list(rc.activos_relacionados.values_list("id", flat=True)) == [otro.id]


class TestAccionTratamientoOrigen:
    def test_generar_accion_desde_vulnerabilidad_enlaza_el_origen(
            self, api_client_autenticado, activo, plan_tratamiento):
        vuln = Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="Hallazgo crítico", probabilidad=5, impacto=5)

        resp = api_client_autenticado.post("/api/acciones-tratamiento/", {
            "plan": plan_tratamiento.id, "id_riesgo": "R-CRUD-01",
            "descripcion_riesgo": "Generada desde vulnerabilidad", "probabilidad": 5,
            "impacto": 5, "acciones_tratamiento": "Mitigar", "origen_vulnerabilidad": vuln.id,
        })
        assert resp.status_code == 201, resp.data
        assert resp.data["origen_vulnerabilidad_nombre"] == "Hallazgo crítico"

        accion = AccionTratamiento.objects.get(id_riesgo="R-CRUD-01")
        assert accion.origen_vulnerabilidad_id == vuln.id

    def test_borrar_el_origen_no_borra_la_accion(self, api_client_autenticado, activo, plan_tratamiento):
        """origen_vulnerabilidad usa on_delete=SET_NULL — la acción de tratamiento
        (evidencia histórica) no debe desaparecer si se borra el hallazgo técnico."""
        vuln = Vulnerabilidad.objects.create(
            activo=activo, nombre_vulnerabilidad="x", probabilidad=1, impacto=1)
        accion = AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-CRUD-02", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x", origen_vulnerabilidad=vuln)

        vuln.delete()
        accion.refresh_from_db()
        assert accion.origen_vulnerabilidad is None

    def test_generar_accion_desde_riesgo_contextual_enlaza_el_origen(
            self, api_client_autenticado, plan_tratamiento):
        """Hallazgo del análisis de gestión del 2026-08-24: antes, solo
        Vulnerabilidad y RiesgoActivo podían originar una acción trazada —
        los 7 riesgos contextuales quedaban fuera del ciclo hallazgo→acción."""
        rc = RiesgoContextual.objects.create(
            id_riesgo_contextual="RC-CRUD-01", escenario_amenaza="Ingeniería social",
            probabilidad=4, impacto=4)

        resp = api_client_autenticado.post("/api/acciones-tratamiento/", {
            "plan": plan_tratamiento.id, "id_riesgo": "R-CRUD-03",
            "descripcion_riesgo": "Generada desde riesgo contextual", "probabilidad": 4,
            "impacto": 4, "acciones_tratamiento": "Capacitar", "origen_riesgo_contextual": rc.id,
        })
        assert resp.status_code == 201, resp.data
        assert resp.data["origen_riesgo_contextual_id"] == "RC-CRUD-01"

        accion = AccionTratamiento.objects.get(id_riesgo="R-CRUD-03")
        assert accion.origen_riesgo_contextual_id == rc.id

    def test_borrar_el_riesgo_contextual_no_borra_la_accion(self, api_client_autenticado, plan_tratamiento):
        rc = RiesgoContextual.objects.create(
            id_riesgo_contextual="RC-CRUD-02", escenario_amenaza="x", probabilidad=1, impacto=1)
        accion = AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-CRUD-04", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x", origen_riesgo_contextual=rc)

        rc.delete()
        accion.refresh_from_db()
        assert accion.origen_riesgo_contextual is None

    def test_riesgo_contextual_expone_sus_acciones_generadas(self, api_client_autenticado, plan_tratamiento):
        """related_name='acciones_generadas' — mismo patrón que ya usan
        Vulnerabilidad y RiesgoActivo para lo mismo."""
        rc = RiesgoContextual.objects.create(
            id_riesgo_contextual="RC-CRUD-03", escenario_amenaza="x", probabilidad=1, impacto=1)
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-CRUD-05", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x", origen_riesgo_contextual=rc)

        assert rc.acciones_generadas.count() == 1
        assert rc.acciones_generadas.first().id_riesgo == "R-CRUD-05"

    def test_unique_together_plan_id_riesgo(self, api_client_autenticado, plan_tratamiento):
        AccionTratamiento.objects.create(
            plan=plan_tratamiento, id_riesgo="R-DUP", descripcion_riesgo="x",
            probabilidad=1, impacto=1, acciones_tratamiento="x")
        resp = api_client_autenticado.post("/api/acciones-tratamiento/", {
            "plan": plan_tratamiento.id, "id_riesgo": "R-DUP",
            "descripcion_riesgo": "duplicado", "probabilidad": 1, "impacto": 1,
            "acciones_tratamiento": "x",
        })
        assert resp.status_code == 400


class TestCamposVaciosSaneados:
    """El frontend sanea "" -> null antes de enviar, pero el backend debe rechazar
    con un 400 claro (no un 500) si algo llega mal, para que el error sea legible."""

    def test_fecha_vacia_como_cadena_es_rechazada_con_400_no_500(self, api_client_autenticado, activo):
        resp = api_client_autenticado.post("/api/riesgos-activo/", {
            "id_riesgo": "RA-CRUD-EMPTY", "activo": activo.id,
            "probabilidad": 1, "impacto": 1, "fecha_objetivo": "",
        })
        assert resp.status_code == 400
        assert resp.status_code != 500
