"""Tests de recuperación de rbac.db corrupta."""
import os
import sqlite3

import pytest

from recuperar_rbac_db import DB, REFERENCIA, integridad_ok, recuperar_si_corrupta


@pytest.fixture()
def copia_db(tmp_path):
    origen = REFERENCIA if os.path.exists(REFERENCIA) else DB
    destino = tmp_path / "rbac.db"
    ref = tmp_path / "rbac.db.referencia"
    import shutil

    shutil.copy2(origen, destino)
    shutil.copy2(origen, ref)
    return destino, ref


def test_integridad_ok_en_base_sana(copia_db):
    db_path, _ = copia_db
    assert integridad_ok(db_path)


def test_recupera_cuando_falta_sistema(copia_db, monkeypatch):
    db_path, ref = copia_db
    con = sqlite3.connect(db_path)
    con.execute("DROP TABLE sistema")
    con.commit()
    con.close()
    assert not integridad_ok(db_path)

    monkeypatch.setattr("recuperar_rbac_db.REFERENCIA", str(ref))
    monkeypatch.setattr("recuperar_rbac_db.DB", str(db_path))

    assert recuperar_si_corrupta(str(db_path), str(ref)) is True
    assert integridad_ok(db_path)


def test_completa_migracion_interrumpida_sistema_new(copia_db):
    from migrar_espacio_datos import _completar_migracion_sistema_interrumpida

    db_path, _ = copia_db
    con = sqlite3.connect(db_path)
    con.execute("ALTER TABLE sistema RENAME TO sistema_new")
    con.commit()
    assert _completar_migracion_sistema_interrumpida(con)
    assert integridad_ok(db_path)
    con.close()
