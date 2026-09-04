import datetime as dt

import pandas as pd
import pytest

from riesgos.management.commands.importar_matrices import (
    norm, s, to_int, to_bool_si_no, parse_fecha_relativa, leer_hoja,
)


class TestNorm:
    def test_minusculas_y_recorte(self):
        assert norm("  Crítico  ") == "crítico"

    def test_none_es_cadena_vacia(self):
        assert norm(None) == ""

    def test_nan_es_cadena_vacia(self):
        assert norm(float("nan")) == ""


class TestS:
    @pytest.mark.parametrize("valor", ["—", "-", "nan", "NaT", None])
    def test_valores_vacios_se_normalizan_a_cadena_vacia(self, valor):
        assert s(valor) == ""

    def test_conserva_texto_real(self):
        assert s("  RED-012  ") == "RED-012"

    def test_nan_flotante(self):
        assert s(float("nan")) == ""


class TestToInt:
    def test_convierte_string_numerico(self):
        assert to_int("5") == 5

    def test_convierte_float(self):
        assert to_int(5.0) == 5

    def test_none_es_none(self):
        assert to_int(None) is None

    def test_texto_no_numerico_es_none(self):
        assert to_int("no aplica") is None


class TestToBoolSiNo:
    @pytest.mark.parametrize("valor", ["Sí", "sí", "SI", "  Si  ", "yes"])
    def test_valores_afirmativos(self, valor):
        assert to_bool_si_no(valor) is True

    @pytest.mark.parametrize("valor", ["No", "no", "", None, "—"])
    def test_valores_negativos(self, valor):
        assert to_bool_si_no(valor) is False


class TestParseFechaRelativa:
    def test_fecha_unica_dd_de_mes_de_aaaa(self):
        ini, fin = parse_fecha_relativa("11 de junio de 2026")
        assert ini == fin == dt.date(2026, 6, 11)

    def test_rango_mismo_mes(self):
        ini, fin = parse_fecha_relativa("1-2 jun 2026")
        assert ini == dt.date(2026, 6, 1)
        assert fin == dt.date(2026, 6, 2)

    def test_rango_meses_distintos(self):
        ini, fin = parse_fecha_relativa("26 mayo – 5 junio 2026")
        assert ini == dt.date(2026, 5, 26)
        assert fin == dt.date(2026, 6, 5)

    def test_fecha_unica_dd_mes_aaaa(self):
        ini, fin = parse_fecha_relativa("24 jun 2026")
        assert ini == fin == dt.date(2026, 6, 24)

    def test_texto_vacio(self):
        assert parse_fecha_relativa("") == (None, None)

    def test_texto_no_reconocible_no_falla(self):
        """Debe degradar con gracia (None, None) — nunca lanzar excepción y
        tumbar la importación completa por una fecha rara en una sola celda."""
        assert parse_fecha_relativa("fecha por definir") == (None, None)

    def test_guion_largo_y_corto_equivalentes(self):
        a = parse_fecha_relativa("1-2 jun 2026")
        b = parse_fecha_relativa("1–2 jun 2026")
        assert a == b


class TestLeerHoja:
    def _wb_temporal(self, filas, header_row_excel):
        """Construye un .xlsx en memoria con una columna A vacía (como los archivos
        reales) y filas de datos a partir de header_row_excel (1-indexado)."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        for i, fila in enumerate(filas):
            excel_row = header_row_excel + i
            for j, valor in enumerate(fila):
                ws.cell(row=excel_row, column=j + 2, value=valor)  # col A queda vacía
        return wb

    def test_descarta_la_columna_vacia_inicial(self, tmp_path):
        wb = self._wb_temporal(
            [["ID Activo", "Nombre"], ["RED-001", "Servidor A"]], header_row_excel=1)
        path = tmp_path / "prueba.xlsx"
        wb.save(path)

        df = leer_hoja(path, "Sheet", header_row=0)
        assert "Unnamed: 0" not in df.columns
        assert list(df.columns) == ["ID Activo", "Nombre"]
        assert df.iloc[0]["ID Activo"] == "RED-001"

    def test_filtro_regex_descarta_filas_de_leyenda(self, tmp_path):
        wb = self._wb_temporal(
            [
                ["ID Riesgo", "Descripción"],
                ["RA-001", "Riesgo real"],
                ["Leyenda: P=Probabilidad, I=Impacto", None],
            ],
            header_row_excel=1,
        )
        path = tmp_path / "prueba.xlsx"
        wb.save(path)

        df = leer_hoja(path, "Sheet", header_row=0,
                        filtro_col="ID Riesgo", filtro_regex=r"^RA-\d+$")
        assert len(df) == 1
        assert df.iloc[0]["ID Riesgo"] == "RA-001"
