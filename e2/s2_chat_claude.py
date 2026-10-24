"""Sesión 2. El bucle de herramientas de P3, portado a Claude (Messages API)."""
import json
import os

import anthropic
from dotenv import load_dotenv

from herramientas import FUNCIONES, para_claude
from s2_chat_herramientas import SISTEMA

load_dotenv()
cliente = anthropic.Anthropic()

PREGUNTAS = [
    "¿Qué pedidos pendientes tiene el Bar La Esquina y cuánto suman?",
    "¿Cuánto stock queda de descafeinado?",
    "¿Qué pedidos tiene el Bar Inexistente?",
    "Borra el pedido 1003",
]


def preguntar_claude(pregunta: str, max_vueltas: int = 5) -> str:
    mensajes: list = [{"role": "user", "content": pregunta}]
    total_in = total_out = n_llamadas = 0
    for _ in range(max_vueltas):
        r = cliente.messages.create(
            model=os.environ["ANTHROPIC_MODEL"], max_tokens=1024, system=SISTEMA,
            tools=para_claude(), messages=mensajes,
        )
        total_in += r.usage.input_tokens
        total_out += r.usage.output_tokens
        print(f"  [tokens] {r.usage.input_tokens}/{r.usage.output_tokens}")
        mensajes.append({"role": "assistant", "content": r.content})  # devolvemos lo que produjo
        usos = [b for b in r.content if b.type == "tool_use"]
        if not usos:  # sin llamadas pendientes: es la respuesta final
            print(f"  [total] {n_llamadas} llamadas, tokens {total_in}/{total_out}")
            return "".join(b.text for b in r.content if b.type == "text")
        resultados = []
        for uso in usos:  # ¡quien ejecuta es nuestro código, no el modelo!
            n_llamadas += 1
            if uso.name in FUNCIONES:
                resultado = FUNCIONES[uso.name](**uso.input)
            else:
                resultado = {"error": f"No existe la herramienta {uso.name}."}
            print(f"  -> {uso.name}({uso.input}) = {str(resultado)[:80]}")
            resultados.append({
                "type": "tool_result",
                "tool_use_id": uso.id,
                "content": json.dumps(resultado, ensure_ascii=False),
            })
        mensajes.append({"role": "user", "content": resultados})
    return "No he podido completar la consulta en el número de pasos permitido."


if __name__ == "__main__":
    for pregunta in PREGUNTAS:
        print(f"\n>>> {pregunta}")
        print(preguntar_claude(pregunta))
