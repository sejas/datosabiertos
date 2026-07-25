"""Tests del índice local. Solo `unittest` de la stdlib; no tocan la red.

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tfm.almacen import Almacen  # noqa: E402
from tfm.conectores.ckan import ConectorCKAN  # noqa: E402
from tfm.configuracion import Portal  # noqa: E402
from tfm.esquema import construir_consulta_fts  # noqa: E402
from tfm.modelo import (  # noqa: E402
    LICENCIA_NO_DECLARADA,
    entero_o_none,
    normalizar_fecha,
    normalizar_licencia,
)
from tfm.registro import ahora_utc  # noqa: E402

PORTAL = Portal(
    id="prueba", municipio="Villaprueba", familia="ckan",
    url_api="https://ejemplo.test/api/3/action", url_base="https://ejemplo.test",
)

PAQUETE_CKAN = {
    "id": "abc-123",
    "name": "calidad-del-aire-2025",
    "title": "Calidad del Aire. Datos horarios 2025",
    "notes": "Mediciones horarias de las estaciones de vigilancia de la calidad del aire.",
    "state": "active",
    "license_id": "cc-by",
    "license_title": "Creative Commons Attribution",
    "metadata_modified": "2026-03-14T10:22:31.123456",
    "modified": "2026-03-01T00:00:00+01:00",
    "organization": {"name": "medio-ambiente", "title": "Área de Medio Ambiente"},
    "groups": [{"name": "medio-ambiente", "display_name": "Medio ambiente"}],
    "tags": [{"name": "aire"}, {"display_name": "Árboles y zonas verdes"}],
    "resources": [
        {"id": "r1", "name": "CSV 2025", "format": "csv", "url": "https://ejemplo.test/a.csv",
         "size": "1048576", "last_modified": "2026-03-10T00:00:00"},
        {"id": "r2", "name": "Ficha PDF", "format": "PDF", "url": "https://ejemplo.test/a.pdf",
         "size": None},
    ],
}


class ConectorFalso(ConectorCKAN):
    """Conector CKAN sin red: sirve un paquete fijo."""

    def listar_crudos(self):
        yield PAQUETE_CKAN


class TestNormalizacion(unittest.TestCase):
    def test_licencia_ausente_no_se_asume_cc_by(self):
        """TODO 3.2: la ausencia de licencia es un dato, nunca CC-BY."""
        for valor in (None, "", "notspecified", "Not Specified", "  "):
            with self.subTest(valor=valor):
                licencia = normalizar_licencia(valor)
                self.assertFalse(licencia.declarada)
                self.assertEqual(licencia.identificador, LICENCIA_NO_DECLARADA)
                self.assertNotIn("cc-by", licencia.identificador)

    def test_licencia_declarada_se_conserva(self):
        licencia = normalizar_licencia("by-sa-40", "Reconocimiento-CompartirIgual 4.0")
        self.assertTrue(licencia.declarada)
        self.assertEqual(licencia.identificador, "by-sa-40")

    def test_other_at_es_licencia_declarada(self):
        """Los `other-*` de CKAN son licencia declarada aunque no sean estándar."""
        self.assertTrue(normalizar_licencia("other-at").declarada)

    def test_fechas_heterogeneas(self):
        self.assertEqual(normalizar_fecha("2026-03-14T10:22:31.123456"), "2026-03-14T10:22:31")
        self.assertEqual(normalizar_fecha("2026-03-01T00:00:00+01:00"), "2026-03-01T00:00:00")
        self.assertEqual(normalizar_fecha("2026-03-01"), "2026-03-01T00:00:00")
        self.assertEqual(normalizar_fecha(""), "")
        self.assertEqual(normalizar_fecha("no es una fecha"), "")

    def test_tamano_heterogeneo(self):
        self.assertEqual(entero_o_none("1048576"), 1048576)
        self.assertIsNone(entero_o_none(""))
        self.assertIsNone(entero_o_none(None))
        self.assertIsNone(entero_o_none("grande"))


class TestConectorCKAN(unittest.TestCase):
    def setUp(self):
        self.conector = ConectorFalso(PORTAL, cliente=None, registro=None)

    def test_paquete_a_dataset(self):
        dataset = self.conector.normalizar(PAQUETE_CKAN)
        self.assertEqual(dataset.titulo, "Calidad del Aire. Datos horarios 2025")
        self.assertEqual(dataset.portal_id, "prueba")
        self.assertEqual(dataset.url_origen, "https://ejemplo.test/dataset/calidad-del-aire-2025")
        self.assertEqual(dataset.publicador.titulo, "Área de Medio Ambiente")
        self.assertEqual([t.titulo for t in dataset.temas], ["Medio ambiente"])
        self.assertIn("Árboles y zonas verdes", dataset.palabras_clave)
        self.assertEqual(len(dataset.distribuciones), 2)

    def test_prefiere_modified_sobre_metadata_modified(self):
        """La fecha del publicador manda sobre la del sistema de metadatos de CKAN."""
        dataset = self.conector.normalizar(PAQUETE_CKAN)
        self.assertEqual(dataset.fecha_modificacion_origen, "2026-03-01T00:00:00")
        self.assertEqual(dataset.fecha_modificacion_metadatos, "2026-03-14T10:22:31")

    def test_distribucion_sin_tamano(self):
        dataset = self.conector.normalizar(PAQUETE_CKAN)
        self.assertEqual(dataset.distribuciones[0].tamano_bytes, 1048576)
        self.assertIsNone(dataset.distribuciones[1].tamano_bytes)
        self.assertEqual(dataset.distribuciones[1].formato, "PDF")

    def test_descarta_borradores(self):
        self.assertIsNone(self.conector.normalizar({**PAQUETE_CKAN, "state": "deleted"}))


class TestConsultaFTS(unittest.TestCase):
    def test_descarta_palabras_vacias(self):
        expresion = construir_consulta_fts("calidad del aire")
        self.assertNotIn('"del"', expresion)
        self.assertIn("calidad", expresion)

    def test_consulta_solo_de_palabras_vacias_no_queda_vacia(self):
        self.assertNotEqual(construir_consulta_fts("de la"), "")

    def test_escapa_sintaxis_de_fts(self):
        """Un `-` o unas comillas del usuario no deben romper la consulta."""
        for entrada in ('aire-2025', 'datos "raros"', "OR AND *", "presupuesto: 2025"):
            with self.subTest(entrada=entrada):
                self.assertNotEqual(construir_consulta_fts(entrada), "")


class TestAlmacen(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.almacen = Almacen(Path(self.directorio.name) / "indice.sqlite")
        conector = ConectorFalso(PORTAL, cliente=None, registro=None)
        dataset = conector.normalizar(PAQUETE_CKAN)
        dataset.fecha_sincronizacion = ahora_utc()
        self.almacen.registrar_portal(PORTAL)
        self.dataset_id = self.almacen.insertar(dataset)
        self.almacen.conexion.commit()

    def tearDown(self):
        self.almacen.cerrar()
        self.directorio.cleanup()

    def test_busqueda_insensible_a_acentos(self):
        """"arboles" sin tilde debe encontrar "Árboles" (FTS5 remove_diacritics 2)."""
        self.assertTrue(self.almacen.buscar("arboles"))
        self.assertTrue(self.almacen.buscar("árboles"))

    def test_busqueda_insensible_a_mayusculas(self):
        self.assertTrue(self.almacen.buscar("calidad del aire"))
        self.assertTrue(self.almacen.buscar("CALIDAD DEL AIRE"))

    def test_busqueda_por_plural(self):
        self.assertTrue(self.almacen.buscar("mediciones"))

    def test_resultados_llevan_procedencia(self):
        """Ninguna fila puede salir del índice sin procedencia (TODO 3.2)."""
        fila = self.almacen.buscar("calidad del aire")[0]
        self.assertTrue(fila["url_origen"])
        self.assertTrue(fila["fecha_sincronizacion"])
        self.assertTrue(fila["fecha_modificacion_origen"])
        self.assertEqual(fila["licencia"], "cc-by")
        self.assertEqual(fila["licencia_declarada"], 1)

    def test_insertar_sin_procedencia_falla(self):
        conector = ConectorFalso(PORTAL, cliente=None, registro=None)
        dataset = conector.normalizar(PAQUETE_CKAN)
        dataset.fecha_sincronizacion = ""
        with self.assertRaises(ValueError):
            self.almacen.insertar(dataset)

    def test_reindexar_es_idempotente(self):
        conector = ConectorFalso(PORTAL, cliente=None, registro=None)

        def datasets():
            dataset = conector.normalizar(PAQUETE_CKAN)
            dataset.fecha_sincronizacion = ahora_utc()
            yield dataset

        for _ in range(3):
            self.almacen.reemplazar_portal(PORTAL, datasets())
        estadisticas = self.almacen.estadisticas()
        self.assertEqual(estadisticas["datasets"], 1)
        self.assertEqual(estadisticas["distribuciones"], 2)

    def test_filtro_por_anio(self):
        self.assertTrue(self.almacen.buscar("calidad", anio=2026))
        self.assertFalse(self.almacen.buscar("calidad", anio=1999))

    def test_estadisticas_cuentan_sin_licencia(self):
        self.assertEqual(self.almacen.estadisticas()["sin_licencia"], 0)


class TestSoporteSQLite(unittest.TestCase):
    def test_fts5_disponible(self):
        conexion = sqlite3.connect(":memory:")
        try:
            conexion.execute(
                "CREATE VIRTUAL TABLE t USING fts5(a, tokenize='unicode61 remove_diacritics 2')"
            )
        except sqlite3.OperationalError as exc:  # pragma: no cover
            self.fail(f"SQLite sin FTS5 o sin remove_diacritics 2: {exc}")
        finally:
            conexion.close()


if __name__ == "__main__":
    unittest.main()
