"""Sesión 3, P2. Experimentos con el agente sin editar los ficheros del kit.

Uso:  python s3_experimentos.py todos   (los cuatro seguidos; rechaza solo la aprobación)
      python s3_experimentos.py 2   (max_pasos=2)
      python s3_experimentos.py 3   (rechaza la aprobación: escribe n)
      python s3_experimentos.py 4   (crear_incidencia sin «Úsala solo si...»)
      python s3_experimentos.py 5   (SISTEMA sin el paso 1)
"""
import builtins
import copy
import sys

from herramientas import DEFINICIONES, FUNCIONES
from s3_agente import SISTEMA, Agente, Herramienta

CORREO = ("Buenas, os escribo del Restaurante Lumbre. La cafetera de dos grupos no "
          "calienta y hoy no podemos servir cafés. ¿Además, cuándo llega el pedido pendiente?")


def construir(definiciones):
    return [
        Herramienta(d["name"], d["description"], d["parameters"], FUNCIONES[d["name"]],
                    requiere_aprobacion=(d["name"] == "crear_incidencia"))
        for d in definiciones
    ]



def exp2():
    print("== Experimento 2: max_pasos=2 ==")
    agente = Agente(SISTEMA, construir(DEFINICIONES), max_pasos=2)
    print(agente.ejecutar(CORREO))


def exp3():
    print("== Experimento 3: rechaza la aprobación ==")
    agente = Agente(SISTEMA, construir(DEFINICIONES))
    print(agente.ejecutar(CORREO))


def exp4():
    print("== Experimento 4: descripción de crear_incidencia sin «Úsala solo si...» ==")
    defs = copy.deepcopy(DEFINICIONES)
    for d in defs:
        if d["name"] == "crear_incidencia":
            d["description"] = d["description"].replace(
                " Úsala solo si el cliente describe una avería concreta.", "")
            print("Descripción ahora:", d["description"])
    agente = Agente(SISTEMA, construir(defs))
    print(agente.ejecutar("¿Revisáis las máquinas en agosto?"))


def exp5():
    print("== Experimento 5: SISTEMA sin el paso 1 (identificar al cliente) ==")
    sistema = SISTEMA.replace(
        "1. Identifica al cliente con buscar_cliente antes de usar su id.\n", "")
    assert sistema != SISTEMA, "no se ha podido quitar el paso 1"
    agente = Agente(sistema, construir(DEFINICIONES))
    print(agente.ejecutar(CORREO))


EXPERIMENTOS = {"2": exp2, "3": exp3, "4": exp4, "5": exp5}

if __name__ == "__main__":
    exp = sys.argv[1] if len(sys.argv) > 1 else ""
    if exp == "todos":
        # Rechaza siempre la aprobación para no llenar la base de datos de incidencias
        def rechazar(pregunta=""):
            print(pregunta + "n  (rechazado automáticamente)")
            return "n"
        builtins.input = rechazar
        for f in EXPERIMENTOS.values():
            f()
            print()
    elif exp in EXPERIMENTOS:
        EXPERIMENTOS[exp]()
    else:
        print(__doc__)
