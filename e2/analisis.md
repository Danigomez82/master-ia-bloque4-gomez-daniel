# E2 · Salidas estructuradas y uso de herramientas

## P1. Clasificador de correos con evaluación

Modelos (vía OpenRouter): `openai/gpt-5.4-mini` (Responses API), `anthropic/claude-haiku-4.5` (Messages API) y `google/gemini-3.8-flash` (Chat Completions). El esquema `CorreoClasificado` fuerza `tipo` ∈ {pedido, incidencia, consulta, mixto}, `cliente`, `lineas`, `urgente` y `resumen`.

### Aciertos de cada proveedor

| Proveedor | 6 casos originales | 19 casos ampliados |
|---|---|---|
| OpenAI | 6/6 | 19/19 |
| Claude | 6/6 | 19/19 |
| Gemini | 6/6 | 19/19 |

Se ampliaron los casos a 19, con estos casos difíciles: ironía (la cafetera que gotea "gracias por nada" y el pedido con tono sarcástico), dos clientes en el mismo correo, un correo en inglés, un correo sin nombre de negocio, correos mixtos con la avería escondida en medio, y dos clientes que no existen en la base de datos (Cafetería El Rincón y Bar El Faro).

### Fallos revisados y etiquetas corregidas

Ninguno de los tres proveedores falló en el campo `tipo`, así que no hubo fallos que revisar ni etiquetas que corregir. Revisé las etiquetas que me parecían más discutibles y las dejé como estaban, porque los tres modelos coincidieron con ellas:

- «La última entrega llegó con 40 minutos de retraso» → `incidencia` (es una queja sin petición concreta, pero el retraso es un problema de servicio).
- «¿Cuándo llega mi pedido 1002?» → `consulta`.
- El pedido con tono irónico («ahora que ya no queda blend os acordáis de nosotros: mandad 25 kg») → `pedido`: la ironía no cambia que haya una petición.

Con 19 casos y tres modelos que acertaron todos, el conjunto no sirve para distinguir entre proveedores: haría falta una muestra más grande y con casos más ambiguos.

### Validación de negocio

Se añadió una función `buscar_cliente` que consulta la tabla `clientes` de `tostadero.db` y se avisa cuando el correo nombra un cliente que no existe. Los tres proveedores produjeron los mismos tres avisos:

| Cliente extraído | Motivo |
|---|---|
| `Cafetería El Rincón` | No existe en la base de datos (caso preparado a propósito). |
| `Bar El Faro` | No existe en la base de datos (caso preparado a propósito). |
| `Bar La Esquina y Panadería Ibiza` | Los dos negocios existen, pero el modelo los junta en un solo texto. |

El tercer aviso no es un error de los modelos, sino del diseño del esquema: `cliente` es un único `str | None` y un correo con dos clientes no cabe. Lo correcto sería cambiarlo por `clientes: list[str]` y validar cada uno por separado.

Esto también muestra que el esquema garantiza la forma de la respuesta, pero no que tenga sentido: sin la comprobación contra la base de datos, los clientes inventados habrían pasado como válidos.

## P3. Bucle de herramientas con OpenAI

Modelo: `openai/gpt-5.4-mini` (Responses API). El bucle llama al modelo, ejecuta en Python las herramientas que pide y le devuelve los resultados hasta que responde sin pedir más. Tokens indicados como entrada/salida.

| # | Pregunta | Herramientas (en orden, con argumentos) | Respuesta del asistente |
|---|---|---|---|
| 1 | ¿Qué pedidos pendientes tiene el Bar La Esquina y cuánto suman? | 1. `buscar_cliente(texto="Bar La Esquina")` → id 1. 2. `consultar_pedidos(cliente_id=1)` → pedidos 1001 (entregado, 169 €) y 1004 (pendiente, 98 €). | Un pedido pendiente, el 1004 del 30/09/2026, y un total pendiente de 98,00 €. Filtró bien el 1001, que está entregado. |
| 2 | ¿Cuánto stock queda de descafeinado? | 1. `stock_producto(texto="descafeinado")` → CAF-003, stock 45. | Quedan 45 unidades de Café descafeinado 1 kg (CAF-003). |
| 3 | ¿Qué pedidos tiene el Bar Inexistente? | 1. `buscar_cliente(texto="Bar Inexistente")` → `[]`. No llegó a llamar a `consultar_pedidos`. | No encontró ningún cliente con ese nombre y ofreció buscar por una parte del nombre. |
| 4 | Borra el pedido 1003 | Ninguna (0 llamadas). | Dijo que no puede borrar pedidos con las herramientas disponibles y ofreció consultar los pedidos del cliente o derivarlo a un agente. |

**Análisis**

- **Pregunta 1 (herramientas encadenadas):** necesita dos llamadas en orden, porque `consultar_pedidos` pide un `cliente_id` que solo se obtiene con `buscar_cliente`. El modelo lo dedujo de las descripciones de las herramientas (la de `buscar_cliente` dice que se use antes que cualquier otra que pida `cliente_id`). La suma la hizo con el resultado real de la base de datos, sin inventar cifras. Gastó 1041 tokens de entrada y 84 de salida en tres vueltas.
- **Pregunta 3 (resultado vacío):** el resultado vacío no es un error, es una respuesta válida. El modelo lo interpretó bien, se detuvo y no inventó pedidos ni probó con ids al azar. Esto lo guía la instrucción del sistema («si no encuentras algo, dilo. No inventes cifras»).
- **Pregunta 4 (herramienta inexistente):** no hay herramienta para borrar y el modelo no intentó llamar a ninguna. Respondió directamente que no puede, sin ejecutar nada. Es el comportamiento esperable, y además el código tampoco permitiría borrar: solo ejecuta funciones que están en `FUNCIONES`.
- **Coste de tokens:** cada vuelta reenvía el historial completo, por eso la entrada crece en las preguntas con varias llamadas (270 → 334 → 437 en la pregunta 1).

## P4. El mismo asistente con Claude

Modelo: `anthropic/claude-haiku-4.5` (Messages API), con `para_claude()`, el mismo `SISTEMA` y las mismas herramientas que en P3. El bucle usa bloques `tool_use` / `tool_result` en lugar de `function_call` / `function_call_output`. Tokens como entrada/salida, sumando todas las vueltas de cada pregunta.

| # | Pregunta | Llamadas OpenAI | Llamadas Claude | Tokens OpenAI | Tokens Claude |
|---|---|---|---|---|---|
| 1 | Pedidos pendientes del Bar La Esquina y suma | 2 (`buscar_cliente` → `consultar_pedidos`) | 2 (las mismas, mismo orden) | 1041 / 84 | 3502 / 227 |
| 2 | Stock de descafeinado | 1 (`stock_producto`) | 1 (la misma) | 597 / 49 | 2153 / 105 |
| 3 | Pedidos del Bar Inexistente | 1 (`buscar_cliente` → vacío) | 1 (la misma) | 563 / 54 | 2134 / 165 |
| 4 | Borra el pedido 1003 | 0 | 0 | 263 / 43 | 1015 / 169 |
| | **Total** | **4** | **4** | **2464 / 230 (≈ $0,0029)** | **8804 / 666 (≈ $0,0121)** |

**Calidad de la respuesta final**

- **Datos:** los dos usan los datos reales de la base de datos y llegan a las mismas cifras (98,00 € pendientes, 45 unidades de CAF-003). Ninguno inventa datos.
- **Pregunta 2:** Claude añade además el precio unitario (19,80 €), que venía en el resultado de la herramienta.
- **Pregunta 3:** los dos se paran al no encontrar el cliente y piden verificar el nombre.
- **Pregunta 4:** OpenAI contesta en dos frases. Claude es más largo: enumera las funciones disponibles y sugiere contactar con «el sistema ERP» o «un supervisor», cosas que no constan en las herramientas y que son una suposición suya.
- **Estilo:** OpenAI es más conciso, Claude más completo y con más formato.

**Conclusión**

- **Mismo comportamiento:** con herramientas hacen lo mismo, y la diferencia está en el coste.
- **Claude gasta unas 3,4–3,9 veces más tokens de entrada:** incluso en la pregunta 4, donde no llama a ninguna herramienta, gasta 1015 frente a 263. La diferencia viene de que Claude cuenta con otro tokenizador y de que las definiciones de las herramientas y las instrucciones internas de tool use pesan más en su entrada. Ese bloque fijo se paga en cada vuelta.
- **Más tokens de salida:** Claude responde con más texto, unas 2–4 veces más que OpenAI.
- **Resultado:** para un asistente interno con estas cuatro herramientas, OpenAI da la misma calidad útil por menos de la cuarta parte del coste.