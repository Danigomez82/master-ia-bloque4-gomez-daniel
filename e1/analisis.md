# E1 · Análisis de la comparativa de proveedores

Mismo prompt de sistema y mismos 5 correos de Tostadero Retiro enviados a tres modelos a través de `llm_client.py`. Datos en `comparativa.csv` (calidad puntuada de 1 a 5).

## Resultados medios por modelo

| Modelo | Segundos | Tokens salida | Coste por correo | Coste 2.000 correos/mes | Calidad media |
|---|---|---|---|---|---|
| openai/gpt-5.4-mini | 1,28 | 56 | $0,000292 | ~$0,58 | 4,0 |
| anthropic/claude-haiku-4.5 | 1,80 | 70 | $0,000416 | ~$0,83 | 3,2 |
| google/gemini-3.8-flash | 5,89 | 524 | $0,001997 | ~$3,99 | 2,6 |

## ¿Por qué Gemini gasta tantos tokens de salida?

Gemini genera unos 400–600 tokens por respuesta, frente a 40–110 de los otros dos, aunque su texto visible tiene la misma longitud (dos frases). La diferencia es el **razonamiento interno**: es un modelo que "piensa" antes de contestar y esos tokens de pensamiento se facturan como salida aunque no aparezcan en la respuesta. Lo confirma la prueba con `max_tokens=20`: devolvió texto vacío, porque agotó el límite razonando antes de escribir nada. Efecto: es unas 7 veces más caro y unas 4,6 veces más lento que OpenAI para una tarea que no necesita razonar.

Además, los tokens de entrada difieren entre proveedores (≈54 en OpenAI, ≈67 en Claude, ≈43 en Gemini) porque cada uno usa un tokenizador distinto; el mismo texto no cuenta igual.

## Calidad

- **OpenAI (4,0):** respuestas útiles y prudentes; no inventa datos. Fallo: en la factura especula con causas genéricas.
- **Claude (3,2):** correcto en la mayoría, honesto en la factura ("no tengo acceso"). Fallos: el correo del hotel rompe el límite de dos frases y es marketing vacío; remite a una "cuenta" que puede no existir.
- **Gemini (2,6):** inventa hechos (horario de reparto "de mañana", "pedido antes del viernes", un producto "Blend Retiro 100% Arábica" con cata, "hemos registrado la incidencia"). En atención al cliente, prometer cosas falsas es el peor error.

## Recomendación para 2.000 correos al mes

**gpt-5.4-mini (OpenAI).** Es el más barato (~$0,58/mes), el más rápido (1,3 s) y el de mejor calidad en esta muestra. El coste no es el factor decisivo (la diferencia máxima son ~$3,4 al mes); pesan más la latencia y, sobre todo, que no invente datos. Gemini se descarta por lento, caro y por inventar hechos; Claude queda como alternativa razonable si se acota la longitud en el prompt.

**Limitaciones:** solo 5 correos por modelo, una única ejecución y puntuación subjetiva; los precios cambian (Gemini tenía un 50 % de descuento el 17/10/2026, a precio de lista costaría el doble). Antes de producción habría que probar con más correos y con datos reales del cliente para que el modelo no tenga que inventarlos.
