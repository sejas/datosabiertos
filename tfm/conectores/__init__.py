"""Registro de conectores por familia de plataforma.

Para añadir Gijón o Zaragoza (fase 2.1) basta con importar la subclase nueva y añadir una
entrada a `FAMILIAS`. Véase la documentación del punto de extensión en `base.py`.
"""

from __future__ import annotations

from ..configuracion import Portal
from ..cortesia import ClienteCortes
from ..registro import RegistroCosecha
from .base import ConectorCatalogo
from .ckan import ConectorCKAN

#: familia declarada en `configuracion.Portal` -> clase de conector.
FAMILIAS: dict[str, type[ConectorCatalogo]] = {
    ConectorCKAN.familia: ConectorCKAN,
    # fase 2.1:
    # ConectorGijon.familia: ConectorGijon,        # REST ad-hoc `descargar.php`
    # ConectorZaragoza.familia: ConectorZaragoza,  # REST propio de zaragoza.es
}


def crear_conector(
    portal: Portal, cliente: ClienteCortes, registro: RegistroCosecha
) -> ConectorCatalogo:
    """Instancia el conector que corresponde a la familia declarada por el portal."""
    try:
        clase = FAMILIAS[portal.familia]
    except KeyError as exc:
        disponibles = ", ".join(sorted(FAMILIAS))
        raise KeyError(
            f"no hay conector para la familia '{portal.familia}' del portal "
            f"'{portal.id}'. Familias registradas: {disponibles}. "
            f"Añade una subclase de ConectorCatalogo (véase tfm/conectores/base.py)."
        ) from exc
    return clase(portal, cliente, registro)


__all__ = ["ConectorCatalogo", "ConectorCKAN", "FAMILIAS", "crear_conector"]
