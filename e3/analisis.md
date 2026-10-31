# E3 · Agentes I: el bucle agéntico, razonamiento y planificación

Modelo en todas las pruebas: `anthropic/claude-haiku-4.5` (vía OpenRouter). Correo de prueba: el Restaurante Lumbre avisa de que su cafetera de dos grupos no calienta, no pueden servir cafés, y pregunta por su pedido pendiente.

## P1. Agente desde cero (`s3_agente.py`)

El bucle de la sesión 2 pasa a ser una clase `Agente` con herramientas declarativas (`Herramienta`), errores devueltos al modelo como datos (`is_error`), aprobación humana en las herramientas que modifican datos (`crear_incidencia`) y límite de pasos (`max_pasos=8`). Cada paso imprime su traza.

Traza de la ejecución con el correo de ejemplo:

| Paso | Qué hizo | Resultado |
|---|---|---|
| 1 | `buscar_cliente("Restaurante Lumbre")` | id 2, Chamberí |
| 2 | `consultar_pedidos(cliente_id=2)` y `crear_incidencia(cliente_id=2, maquina="MAQ-002", prioridad="alta")` | Pedido 1003 pendiente (496,40 €). Incidencia pedida: **pidió aprobación y la aprobé**, se creó la incidencia nº 3. |
| Final | Respuesta al cliente | Cuenta la incidencia (prioridad alta) y el pedido pendiente con datos reales. |

Dos fallos que la traza deja ver: el modelo escribió `MAQ-002`, un SKU que **no existe** (la cafetera de dos grupos es `MAQ-010`) y no consultó el catálogo con `stock_producto`; y prometió que el equipo técnico contactaría «hoy», algo que ninguna herramienta respalda. La base de datos aceptó la máquina porque `maquina` es texto libre. La aprobación humana es lo que permite verlo antes de que se ejecute.

## P2. Experimentos

| Experimento | Qué observé |
|---|---|
| 1. Correo de ejemplo | Secuencia: `buscar_cliente` → `consultar_pedidos` + `crear_incidencia` (prioridad **alta**, porque el local no puede servir café). Respuesta final con datos reales del pedido 1003. |
| 2. `max_pasos=2` | Paso 1: `buscar_cliente`. Paso 2: `crear_incidencia` (rechazada) y `consultar_pedidos`. Se agota el límite y el cliente solo recibe «He alcanzado el límite de pasos sin terminar. Paso el caso a una persona.», sin ninguna de la información ya obtenida. El corte es seguro, pero poco informativo para el cliente. |
| 3. Rechazar la aprobación | El modelo **no reintenta** (no vuelve a llamar a `crear_incidencia`). Lo explica y propone «escalarlo manualmente con nuestro equipo técnico», pero esa acción no existe, y promete «os contactaremos inmediatamente». Sigue informando bien del pedido. |
| 4. Quitar «Úsala solo si el cliente describe una avería» y preguntar «¿Revisáis las máquinas en agosto?» | **No creó ninguna incidencia** ni llamó a ninguna herramienta: pidió aclaración. Con este modelo la frase no era imprescindible; con otro más impulsivo podría serlo. |
| 5. Quitar el paso 1 de `SISTEMA` | **No inventó el `cliente_id`**: hizo igualmente `buscar_cliente` y obtuvo el 2. Tras el rechazo dijo que había «escalado la avería a un operador especializado», lo que no ocurrió. |

Observaciones transversales:

- El SKU de la máquina cambia entre ejecuciones (`MAQ-002` en las ejecuciones 1 y 2, `MAQ-010` en la 3 y la 5): sin consultar el catálogo, el modelo adivina.
- Tras un rechazo, el modelo tiende a dar a entender al cliente que el problema sigue en marcha. El rechazo humano no se traduce en un mensaje honesto.
- El rechazo no cancela las otras llamadas del mismo paso: `consultar_pedidos` se ejecutó igualmente.

## P3. El mismo agente con LangChain (`s3_agente_langchain.py`)

Con `create_agent`, el bucle lo pone el framework. La aprobación humana es `HumanInTheLoopMiddleware(interrupt_on={"crear_incidencia": True})`, el límite de pasos es `ModelCallLimitMiddleware(run_limit=8)`, y el `InMemorySaver` guarda el estado para poder pausar y reanudar. Al ejecutarlo pidió aprobación de `crear_incidencia(cliente_id=2, maquina="MAQ-002", ..., prioridad="alta")`; al aprobar, se creó la incidencia nº 4 y respondió al cliente con ella. Reproduce los mismos fallos que la versión manual (SKU inventado y promesa de contacto).

## Comparación razonada: desde cero frente a LangChain

| Criterio | Desde cero | LangChain |
|---|---|---|
| Líneas de código (sin vacías ni comentarios) | 80, con la clase `Agente`, el bucle y el `SISTEMA` | 47, reutilizando `SISTEMA` y las funciones |
| Trazas | Imprime cada paso, herramienta, argumentos y resultado | En mi ejecución solo se vio la petición de aprobación y la respuesta final |
| Aprobación humana | Un `input()` dentro de `_ejecutar`: sencillo, pero bloquea el proceso | Middleware + checkpointer: pausa y reanuda el grafo (válido incluso entre procesos) |
| Límite de pasos | `max_pasos` en el bucle, con mensaje propio | `ModelCallLimitMiddleware` |
| Errores de herramientas | Se devuelven al modelo con `is_error`, controlados por nosotros | Los gestiona el framework |
| Cambio de proveedor | Reescribir el bucle (Messages, Responses, Chat Completions) | Cambiar la cadena del modelo |
| Control del formato de mensajes | Total | Limitado |

**Qué se gana con LangChain:** menos código y varias funciones ya resueltas: pausar y reanudar con estado guardado, límite de llamadas y cambio de proveedor con una cadena. Para una aprobación que ha de sobrevivir a que el operador responda horas después, el checkpointer aporta algo que el `input()` no da.

**Qué se pierde:** la visibilidad. En el agente propio vi cada paso y detecté el SKU inexistente y las promesas no respaldadas; en LangChain, el bucle queda dentro del framework y las trazas exigen configuración adicional. El control fino de los mensajes y del texto de cada error también queda del lado del framework.

**Conclusión:** para aprender y depurar, o cuando hace falta controlar exactamente cada paso y cada mensaje, conviene el agente desde cero. Para producción con aprobaciones asíncronas, varios proveedores y menos mantenimiento, LangChain. Ninguno corrige por sí solo los fallos que aparecieron en las pruebas, porque vienen del modelo y del diseño de las herramientas: `maquina` debería validarse contra el catálogo y el mensaje tras un rechazo debería ser honesto. Esas protecciones hay que añadirlas en cualquiera de las dos versiones.