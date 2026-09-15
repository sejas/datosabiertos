"""Tests del servidor MCP y de sus herramientas. Sin red y sin índice real.

Se construye un índice mínimo en un directorio temporal, de modo que estos tests pasan en
una máquina limpia antes de haber cosechado nada.

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datosabiertos.almacen import Almacen  # noqa: E402
from datosabiertos.conectores.ckan import ConectorCKAN  # noqa: E402
from datosabiertos.configuracion import CORPUS, Portal  # noqa: E402
from datosabiertos.mcp import herramientas as h  # noqa: E402
from datosabiertos.mcp.servidor import VERSION_PROTOCOLO, ServidorMCP  # noqa: E402
from datosabiertos.registro import ahora_utc  # noqa: E402

# Se reutilizan dos portales del corpus real para que los `enum` de los esquemas encajen.
PORTAL_MADRID = CORPUS["madrid"]
PORTAL_CORDOBA = CORPUS["cordoba"]

PAQUETE_MADRID = {
    "id": "300402-0-calidad-aire-episodios-ozono",
    "name": "300402-0-calidad-aire-episodios-ozono",
    "title": "Calidad del aire. Episodios de alta contaminación por ozono",
    "notes": "Medidas adoptadas en aplicación del protocolo de episodios de ozono.",
    "state": "active",
    "license_id": "cc-by",
    "modified": "2026-06-11T00:00:00",
    "groups": [{"name": "medio-ambiente", "display_name": "Medio ambiente"}],
    "tags": [{"name": "aire"}, {"name": "ozono"}],
    "resources": [
        {"id": "r1", "name": "CSV", "format": "csv", "url": "https://datos.madrid.es/a.csv",
         "size": "2048"},
        {"id": "r2", "name": "Ficha", "format": "pdf", "url": "https://datos.madrid.es/a.pdf"},
    ],
}

#: Córdoba: 145 de 145 datasets sin licencia declarada. El peor caso medido del corpus.
PAQUETE_CORDOBA = {
    "id": "presupuestos-2022", "name": "presupuestos-2022", "title": "Presupuestos 2022",
    "notes": "Presupuestos 2022", "state": "active", "license_id": "notspecified",
    "modified": "2024-01-22T13:01:44",
    "resources": [{"id": "c1", "format": "pdf", "url": "https://datosabiertos.cordoba.es/p.pdf"}],
}


def _indice_de_prueba(directorio: Path) -> Almacen:
    almacen = Almacen(directorio / "indice.sqlite")
    for portal, paquete in ((PORTAL_MADRID, PAQUETE_MADRID), (PORTAL_CORDOBA, PAQUETE_CORDOBA)):
        conector = ConectorCKAN(portal, cliente=None, registro=None)
        dataset = conector.normalizar(paquete)
        dataset.fecha_sincronizacion = ahora_utc()
        almacen.registrar_portal(portal)
        almacen.insertar(dataset)
    almacen.conexion.commit()
    return almacen


class BaseIndice(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.almacen = _indice_de_prueba(Path(self.directorio.name))

    def tearDown(self):
        self.almacen.cerrar()
        self.directorio.cleanup()


class TestHerramientas(BaseIndice):
    def test_buscar_devuelve_procedencia_completa(self):
        """TODO 3.2: ninguna ficha puede salir sin procedencia."""
        r = h.buscar_datasets(self.almacen, "calidad del aire", ciudad="madrid")
        self.assertEqual(r["n_resultados"], 1)
        ficha = r["resultados"][0]
        for campo in ("url_origen", "fecha_modificacion_origen", "fecha_sincronizacion",
                      "licencia_declarada", "id"):
            self.assertIn(campo, ficha, f"falta {campo}")
        self.assertTrue(ficha["url_origen"].startswith("https://"))

    def test_licencia_no_declarada_se_avisa(self):
        r = h.buscar_datasets(self.almacen, "presupuestos", ciudad="cordoba")
        ficha = r["resultados"][0]
        self.assertFalse(ficha["licencia_declarada"])
        self.assertIsNone(ficha["licencia"])
        self.assertIn("advertencia", ficha)
        self.assertIn("NO declara licencia", ficha["advertencia"])

    def test_sin_resultados_lo_dice_explicitamente(self):
        """La ausencia tiene que viajar como instrucción, no como lista vacía."""
        r = h.buscar_datasets(self.almacen, "estación espacial internacional")
        self.assertEqual(r["n_resultados"], 0)
        self.assertIn("sin_resultados", r)
        self.assertIn("NO inventes", r["sin_resultados"])

    def test_ciudad_desconocida(self):
        r = h.buscar_datasets(self.almacen, "algo", ciudad="narnia")
        self.assertIn("error", r)
        self.assertIn("ciudades_disponibles", r)

    def test_detalle_incluye_temas_y_keywords(self):
        r = h.detalle_dataset(self.almacen, "madrid:300402-0-calidad-aire-episodios-ozono")
        self.assertEqual(r["temas"], ["Medio ambiente"])
        self.assertIn("ozono", r["palabras_clave"])

    def test_identificadores_malos_devuelven_error_no_excepcion(self):
        for malo in ("sin-dos-puntos", "narnia:algo", "madrid:no-existe"):
            with self.subTest(id=malo):
                r = h.detalle_dataset(self.almacen, malo)
                self.assertIn("error", r)
                self.assertIsInstance(r, dict)

    def test_listar_distribuciones(self):
        r = h.listar_distribuciones(self.almacen, "madrid:300402-0-calidad-aire-episodios-ozono")
        self.assertEqual(r["n_distribuciones"], 2)
        formatos = [d["formato"] for d in r["distribuciones"]]
        self.assertIn("CSV", formatos)
        self.assertTrue(r["distribuciones"][0]["tamano_declarado"])
        self.assertFalse(r["distribuciones"][1]["tamano_declarado"])

    def test_comparar_ciudades_declara_las_ausencias(self):
        r = h.comparar_ciudades(self.almacen, "calidad del aire",
                                ciudades=["madrid", "cordoba"])
        self.assertIn("madrid", r["con_datos"])
        self.assertIn("cordoba", r["sin_datos"])
        self.assertIn("ausencia es un resultado", r["nota_sin_datos"])

    def test_catalogo_coherente_con_las_funciones(self):
        """Cada entrada del catálogo apunta a una función real con esquema de objeto."""
        self.assertEqual(len(h.CATALOGO), 4)
        for nombre, (funcion, descripcion, esquema) in h.CATALOGO.items():
            with self.subTest(herramienta=nombre):
                self.assertTrue(callable(funcion))
                self.assertTrue(descripcion.strip())
                self.assertEqual(esquema["type"], "object")
                self.assertIn("required", esquema)


class TestProtocoloMCP(BaseIndice):
    """Sesión JSON-RPC completa contra el servidor, como la haría un cliente real."""

    def _sesion(self, mensajes: list[dict]) -> list[dict]:
        entrada = io.StringIO("".join(json.dumps(m) + "\n" for m in mensajes))
        salida = io.StringIO()
        ServidorMCP(self.almacen).servir(entrada=entrada, salida=salida)
        return [json.loads(linea) for linea in salida.getvalue().splitlines() if linea.strip()]

    def test_handshake_y_listado(self):
        respuestas = self._sesion([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": VERSION_PROTOCOLO,
                        "clientInfo": {"name": "prueba", "version": "1"}, "capabilities": {}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ])
        # la notificación no genera respuesta: 2 mensajes, no 3
        self.assertEqual(len(respuestas), 2)
        inicio = respuestas[0]["result"]
        self.assertEqual(inicio["protocolVersion"], VERSION_PROTOCOLO)
        self.assertIn("tools", inicio["capabilities"])
        self.assertIn("instructions", inicio)
        nombres = {t["name"] for t in respuestas[1]["result"]["tools"]}
        self.assertEqual(nombres, {"buscar_datasets", "detalle_dataset",
                                   "listar_distribuciones", "comparar_ciudades"})

    def test_tools_call(self):
        respuestas = self._sesion([
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "buscar_datasets",
                        "arguments": {"consulta": "calidad del aire", "ciudad": "madrid"}}},
        ])
        resultado = respuestas[0]["result"]
        self.assertFalse(resultado["isError"])
        self.assertIn("content", resultado)
        self.assertEqual(resultado["content"][0]["type"], "text")
        datos = resultado["structuredContent"]
        self.assertEqual(datos["n_resultados"], 1)
        # el texto es JSON legible y coincide con structuredContent
        self.assertEqual(json.loads(resultado["content"][0]["text"]), datos)

    def test_tools_call_marca_isError_en_los_errores(self):
        respuestas = self._sesion([
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "detalle_dataset", "arguments": {"id": "narnia:x"}}},
        ])
        self.assertTrue(respuestas[0]["result"]["isError"])

    def test_herramienta_desconocida_no_tumba_la_sesion(self):
        respuestas = self._sesion([
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "invocar_a_cthulhu", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 2, "method": "ping"},
        ])
        self.assertTrue(respuestas[0]["result"]["isError"])
        self.assertEqual(respuestas[1]["result"], {})

    def test_argumentos_invalidos(self):
        respuestas = self._sesion([
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "buscar_datasets", "arguments": {"parametro_absurdo": 1}}},
        ])
        self.assertTrue(respuestas[0]["result"]["isError"])
        self.assertIn("argumentos inválidos",
                      respuestas[0]["result"]["structuredContent"]["error"])

    def test_metodo_no_implementado(self):
        respuestas = self._sesion([
            {"jsonrpc": "2.0", "id": 1, "method": "resources/list"},
        ])
        self.assertEqual(respuestas[0]["error"]["code"], -32601)

    def test_json_mal_formado_no_tumba_la_sesion(self):
        entrada = io.StringIO('{esto no es json}\n' + json.dumps(
            {"jsonrpc": "2.0", "id": 2, "method": "ping"}) + "\n")
        salida = io.StringIO()
        ServidorMCP(self.almacen).servir(entrada=entrada, salida=salida)
        respuestas = [json.loads(l) for l in salida.getvalue().splitlines() if l.strip()]
        self.assertEqual(respuestas[0]["error"]["code"], -32700)
        self.assertEqual(respuestas[1]["result"], {})


if __name__ == "__main__":
    unittest.main()


class TestSoloLectura(BaseIndice):
    """El endpoint HTTP abre el índice en solo lectura: no debe poder escribir."""

    def test_no_escribe_y_sigue_consultando(self):
        import sqlite3
        ruta = self.almacen.ruta
        self.almacen.cerrar()
        lector = Almacen(ruta, solo_lectura=True)
        try:
            self.assertTrue(lector.solo_lectura)
            self.assertEqual(lector.estadisticas()["datasets"], 2)
            self.assertTrue(lector.buscar("calidad del aire"))
            with self.assertRaises(sqlite3.OperationalError):
                lector.conexion.execute("DELETE FROM dataset")
        finally:
            lector.cerrar()
            self.almacen = Almacen(ruta)  # para que tearDown no falle

    def test_indice_inexistente_falla_pronto(self):
        with self.assertRaises(FileNotFoundError):
            Almacen(Path(self.directorio.name) / "no-existe.sqlite", solo_lectura=True)


class TestTransporteHTTP(BaseIndice):
    """El manejador HTTP encamina al mismo ServidorMCP que stdio."""

    def test_las_rutas_declaradas_existen(self):
        from datosabiertos.mcp import http as modulo
        for metodo in ("do_GET", "do_POST", "do_OPTIONS"):
            self.assertTrue(hasattr(modulo.Manejador, metodo))
        self.assertLessEqual(modulo.TAMANO_MAXIMO, 10_000_000)

    def test_una_notificacion_no_produce_respuesta(self):
        """Si atender() devuelve None, el HTTP responde 202 sin cuerpo."""
        servidor = ServidorMCP(self.almacen)
        self.assertIsNone(servidor.atender({"jsonrpc": "2.0",
                                            "method": "notifications/initialized"}))
