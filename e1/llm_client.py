"""Sesión 1. Una interfaz común para varios proveedores (patrón Adapter).

El resto del bloque usará LLM.responder() cuando el proveedor dé igual."""
import os
import time
from dataclasses import dataclass

import anthropic
import openai
from dotenv import load_dotenv
from google import genai

load_dotenv()

OPENROUTER = "https://openrouter.ai/api/v1"

# Precios en USD por millón de tokens (entrada, salida), con el id del modelo tal y como
# va en .env, p. ej. "openai/gpt-5.4-mini". Rellénalos con https://openrouter.ai/models:
# cambian a menudo y no conviene fiarse de la memoria.
# Consultados en openrouter.ai el 17/10/2026. Gemini 3.8 Flash tenía un 50 % de descuento
# (precio de lista: 1.50 / 7.50); si el descuento termina, actualiza esa línea.
PRECIOS: dict[str, tuple[float, float]] = {
    "openai/gpt-5.4-mini": (0.75, 4.50),
    "anthropic/claude-haiku-4.5": (1.00, 5.00),
    "google/gemini-3.8-flash": (0.75, 3.75),
}


@dataclass
class Respuesta:
    texto: str
    tokens_entrada: int
    tokens_salida: int
    segundos: float
    modelo: str

    @property
    def coste_usd(self) -> float | None:
        if self.modelo not in PRECIOS:
            return None
        p_in, p_out = PRECIOS[self.modelo]
        return (self.tokens_entrada * p_in + self.tokens_salida * p_out) / 1_000_000


class LLM:
    """proveedor: 'openai' | 'claude' | 'gemini' | 'ollama'.

    Cada proveedor habla un formato de API: Responses (OpenAI), Messages (Claude),
    Interactions (Gemini nativo) o Chat Completions (Gemini vía OpenRouter y Ollama)."""

    def __init__(self, proveedor: str, modelo: str | None = None):
        self.proveedor = proveedor
        defecto = {
            "openai": os.getenv("OPENAI_MODEL"),
            "claude": os.getenv("ANTHROPIC_MODEL"),
            "gemini": os.getenv("GEMINI_MODEL"),
            "ollama": "llama3.2",
        }
        self.modelo = modelo or defecto[proveedor]
        if proveedor == "openai":
            self.formato = "responses"
            self._c = openai.OpenAI(max_retries=3)  # reintentos con espera exponencial
        elif proveedor == "claude":
            self.formato = "messages"
            self._c = anthropic.Anthropic(max_retries=3)
        elif proveedor == "gemini" and os.getenv("GEMINI_API_KEY"):  # opcional: API nativa
            self.formato = "interactions"
            self.modelo = self.modelo.removeprefix("google/")
            self._c = genai.Client()
        elif proveedor == "gemini":  # por defecto, vía OpenRouter
            self.formato = "chat"
            self._c = openai.OpenAI(base_url=OPENROUTER, api_key=os.environ["OPENROUTER_API_KEY"],
                                    max_retries=3)
        elif proveedor == "ollama":  # Ollama expone una API compatible con OpenAI
            self.formato = "chat"
            self._c = openai.OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        else:
            raise ValueError(f"Proveedor no soportado: {proveedor}")

    def responder(self, sistema: str, prompt: str, temperatura: float | None = None,
                  max_tokens: int | None = None) -> Respuesta:
        extra = {} if temperatura is None else {"temperature": temperatura}
        t0 = time.perf_counter()
        if self.formato == "responses":
            # OpenAI (Responses API): el límite de salida se llama max_output_tokens.
            opciones = dict(extra)
            if max_tokens is not None:
                opciones["max_output_tokens"] = max_tokens
            r = self._c.responses.create(
                model=self.modelo, instructions=sistema, input=prompt, **opciones
            )
            texto, t_in, t_out = r.output_text, r.usage.input_tokens, r.usage.output_tokens
        elif self.formato == "messages":
            # Claude (Messages API): max_tokens es obligatorio, el sistema va aparte
            # y el texto llega en bloques (se unen los de tipo "text").
            r = self._c.messages.create(
                model=self.modelo,
                system=sistema,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens if max_tokens is not None else 1024,
                **extra,
            )
            texto = "".join(b.text for b in r.content if b.type == "text")
            t_in, t_out = r.usage.input_tokens, r.usage.output_tokens
        elif self.formato == "interactions":
            opciones = dict(extra)
            if max_tokens is not None:
                opciones["max_output_tokens"] = max_tokens
            config = {"generation_config": opciones} if opciones else {}
            r = self._c.interactions.create(
                model=self.modelo, system_instruction=sistema, input=prompt, **config
            )
            texto, t_in, t_out = r.output_text, r.usage.total_input_tokens, r.usage.total_output_tokens
        else:  # Chat Completions, el formato "clásico" de OpenAI que imitan casi todos
            opciones = dict(extra)
            if max_tokens is not None:
                opciones["max_tokens"] = max_tokens
            r = self._c.chat.completions.create(
                model=self.modelo,
                messages=[{"role": "system", "content": sistema}, {"role": "user", "content": prompt}],
                **opciones,
            )
            # Con un límite bajo, un modelo que razona puede gastarlo todo pensando y
            # devolver content=None: lo convertimos en "" para no romper el programa.
            texto = r.choices[0].message.content or ""
            t_in, t_out = r.usage.prompt_tokens, r.usage.completion_tokens
        return Respuesta(texto, t_in, t_out, time.perf_counter() - t0, self.modelo)


if __name__ == "__main__":
    for proveedor in ["openai", "claude", "gemini"]:
        try:
            r = LLM(proveedor).responder("Responde en una frase.", "¿Qué es un token?")
        except NotImplementedError as e:
            print(f"{proveedor:7} pendiente: {e}")
            continue
        print(f"{proveedor:7} {r.segundos:5.2f} s  {r.tokens_entrada:4}/{r.tokens_salida:<4} {r.texto}")
