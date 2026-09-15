"""Interfaz de línea de órdenes del índice local.

    python -m datosabiertos.index build [--portal madrid] [--sin-crudo] [--verboso]
    python -m datosabiertos.index portales
    python -m datosabiertos.index buscar "calidad del aire" [--portal malaga] [--anio 2025]
    python -m datosabiertos.index estado
    python -m datosabiertos.index errores [--portal madrid]

`build` reconstruye desde cero los portales indicados (o el corpus entero). Es idempotente:
cada portal se vacía antes de reindexarse, así que ejecutarlo dos veces deja el mismo índice.
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import configuracion as cfg
from .almacen import Almacen
from .conectores import crear_conector
from .cortesia import ClienteCortes
from .registro import RegistroCosecha


def _mb(bytes_: int) -> str:
    return f"{bytes_ / 1e6:.1f} MB"


def construir(args: argparse.Namespace) -> int:
    portales = cfg.portales(args.portal)
    registro = RegistroCosecha(cfg.RUTA_LOG, verboso=args.verboso)
    cliente = ClienteCortes(registro)
    registro.info("-", f"cosecha de {len(portales)} portal(es): {', '.join(p.id for p in portales)}")
    comienzo = time.monotonic()

    def cosechar(portal):
        """Cosecha en memoria; la escritura en SQLite se hace después, en un solo hilo."""
        conector = crear_conector(portal, cliente, registro)
        return portal, list(conector.cosechar())

    with ThreadPoolExecutor(max_workers=cfg.CONCURRENCIA_PORTALES) as ejecutor:
        cosechados = list(ejecutor.map(cosechar, portales))

    fallos = 0
    with Almacen(cfg.RUTA_INDICE) as almacen:
        for portal, datasets in cosechados:
            resumen = registro.resumen(portal.id)
            if not datasets:
                fallos += 1
                registro.aviso(portal.id, "0 datasets cosechados: no se toca el índice existente")
            else:
                total = almacen.reemplazar_portal(
                    portal, datasets, guardar_crudo=not args.sin_crudo
                )
                resumen.n_distribuciones = sum(len(d.distribuciones) for d in datasets)
                registro.info(portal.id, f"{total} datasets indexados")
            almacen.registrar_cosecha(resumen, registro.errores_de(portal.id))
        estadisticas = almacen.estadisticas()

    segundos = time.monotonic() - comienzo
    print(f"\nÍndice: {cfg.RUTA_INDICE}")
    print(f"Construido en {segundos:.0f}s · {_mb(estadisticas['bytes_indice'])}")
    print(f"{estadisticas['datasets']} datasets · {estadisticas['distribuciones']} distribuciones "
          f"· {estadisticas['keywords']} keywords")
    print(f"Sin licencia declarada: {estadisticas['sin_licencia']}")
    print(f"\n{'portal':<12}{'municipio':<14}{'datasets':>9}{'sin lic.':>10}")
    for fila in estadisticas["por_portal"]:
        print(f"{fila['id']:<12}{fila['municipio']:<14}{fila['n']:>9}{fila['sin_licencia'] or 0:>10}")
    if fallos:
        print(f"\n{fallos} portal(es) sin resultados. Revisa: python -m datosabiertos.index errores")
    return 1 if fallos == len(portales) else 0


def listar_portales(_args: argparse.Namespace) -> int:
    print(f"{'id':<12}{'municipio':<16}{'familia':<8}url_api")
    for portal in cfg.portales(None):
        print(f"{portal.id:<12}{portal.municipio:<16}{portal.familia:<8}{portal.url_api}")
    if cfg.PENDIENTES_FASE_2_1:
        print("\nPendientes de la fase 2.1 (sin conector todavía):")
        for identificador, nota in cfg.PENDIENTES_FASE_2_1.items():
            print(f"  {identificador:<10} {nota}")
    return 0


def buscar(args: argparse.Namespace) -> int:
    with Almacen(cfg.RUTA_INDICE) as almacen:
        filas = almacen.buscar(
            consulta=args.consulta, portal_id=args.portal, tema=args.tema,
            anio=args.anio, limite=args.limite,
        )
        if not filas:
            print("Sin resultados.")
            return 1
        for fila in filas:
            licencia = fila["licencia"] if fila["licencia_declarada"] else "NO DECLARADA"
            print(f"\n[{fila['municipio']}] {fila['titulo']}")
            print(f"  {(fila['descripcion'] or '')[:140].strip()}")
            print(f"  {fila['num_distribuciones']} distribuciones · licencia: {licencia}")
            print(f"  modificado en origen: {fila['fecha_modificacion_origen'] or 'sin fecha'}"
                  f" · sincronizado: {fila['fecha_sincronizacion']}")
            print(f"  {fila['url_origen']}")
    return 0


def exportar_web(args: argparse.Namespace) -> int:
    """Genera el índice ligero que consume el cliente del navegador.

    Quita el JSON crudo y la bitácora de errores, compacta con VACUUM y deja al lado una
    copia comprimida. 65 MB -> 21 MB -> 3,4 MB en gzip. Sin este comando el despliegue no
    sería reproducible desde el repositorio, porque `datos/` no se versiona.
    """
    import gzip
    import shutil
    import sqlite3

    destino = Path(args.destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(cfg.RUTA_INDICE, destino)
    conexion = sqlite3.connect(destino)
    for tabla in ("dataset_crudo", "error_cosecha"):
        conexion.execute(f"DROP TABLE IF EXISTS {tabla}")
    conexion.commit()
    conexion.execute("VACUUM")
    conexion.close()

    comprimido = destino.with_suffix(destino.suffix + ".gz")
    with open(destino, "rb") as origen, gzip.open(comprimido, "wb", compresslevel=9) as salida:
        shutil.copyfileobj(origen, salida)

    print(f"{cfg.RUTA_INDICE} ({_mb(cfg.RUTA_INDICE.stat().st_size)})")
    print(f"  -> {destino} ({_mb(destino.stat().st_size)})")
    print(f"  -> {comprimido} ({_mb(comprimido.stat().st_size)})  <- lo que viaja al navegador")
    return 0


def estado(_args: argparse.Namespace) -> int:
    with Almacen(cfg.RUTA_INDICE) as almacen:
        estadisticas = almacen.estadisticas()
        print(f"Índice: {cfg.RUTA_INDICE} ({_mb(estadisticas['bytes_indice'])})")
        print(f"{estadisticas['datasets']} datasets · {estadisticas['distribuciones']} "
              f"distribuciones · {estadisticas['sin_licencia']} sin licencia declarada")
        for fila in estadisticas["por_portal"]:
            print(f"  {fila['municipio']:<16}{fila['n']:>6} datasets")
        ultimas = almacen.conexion.execute(
            "SELECT portal_id, fin, estado, n_datasets, n_peticiones, n_reintentos, segundos "
            "FROM cosecha ORDER BY id DESC LIMIT 10"
        ).fetchall()
        if ultimas:
            print("\nÚltimas cosechas:")
            for fila in ultimas:
                print(f"  {fila['fin'] or '':<22}{fila['portal_id']:<12}{fila['estado']:<9}"
                      f"{fila['n_datasets']:>6} ds  {fila['n_peticiones']:>4} pet."
                      f"  {fila['n_reintentos']:>3} rei.  {fila['segundos']:>7.1f}s")
    return 0


def errores(args: argparse.Namespace) -> int:
    with Almacen(cfg.RUTA_INDICE) as almacen:
        sql = ("SELECT momento, portal_id, tipo, codigo_http, intento, definitivo, mensaje, url "
               "FROM error_cosecha")
        parametros = ()
        if args.portal:
            sql += " WHERE portal_id = ?"
            parametros = (args.portal[0],)
        sql += " ORDER BY id DESC LIMIT ?"
        filas = almacen.conexion.execute(sql, (*parametros, args.limite)).fetchall()
        if not filas:
            print("Sin errores registrados.")
            return 0
        for fila in filas:
            marca = "DEFINITIVO" if fila["definitivo"] else f"intento {fila['intento']}"
            print(f"{fila['momento']}  {fila['portal_id']:<10}{fila['tipo']:<14}{marca:<12}"
                  f"{fila['mensaje'][:90]}")
    return 0


def principal(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="python -m datosabiertos.index", description="Índice local de catálogos municipales."
    )
    subordenes = analizador.add_subparsers(dest="orden", required=True)

    orden_build = subordenes.add_parser("build", help="cosecha e indexa (idempotente)")
    orden_build.add_argument("--portal", action="append", help="portal concreto; repetible")
    orden_build.add_argument("--sin-crudo", action="store_true",
                             help="no guardar el JSON original (índice más pequeño)")
    orden_build.add_argument("--verboso", action="store_true")
    orden_build.set_defaults(funcion=construir)

    subordenes.add_parser("portales", help="lista el corpus").set_defaults(funcion=listar_portales)

    orden_buscar = subordenes.add_parser("buscar", help="busca en el índice")
    orden_buscar.add_argument("consulta")
    orden_buscar.add_argument("--portal")
    orden_buscar.add_argument("--tema")
    orden_buscar.add_argument("--anio", type=int)
    orden_buscar.add_argument("--limite", type=int, default=10)
    orden_buscar.set_defaults(funcion=buscar)

    subordenes.add_parser("estado", help="resumen del índice").set_defaults(funcion=estado)

    orden_web = subordenes.add_parser(
        "exportar-web", help="índice ligero + gzip para el cliente del navegador")
    orden_web.add_argument("--destino", default="web/datos/indice.sqlite")
    orden_web.set_defaults(funcion=exportar_web)

    orden_errores = subordenes.add_parser("errores", help="errores de cosecha registrados")
    orden_errores.add_argument("--portal", action="append")
    orden_errores.add_argument("--limite", type=int, default=30)
    orden_errores.set_defaults(funcion=errores)

    args = analizador.parse_args(argv)
    return args.funcion(args)


if __name__ == "__main__":
    sys.exit(principal())
