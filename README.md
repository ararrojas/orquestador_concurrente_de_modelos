# orquestador_concurrente_de_modelos

Simulación de un backend que consulta varios modelos de IA de forma concurrente con `asyncio`.

## Requisitos

Python 3.12+ (sin dependencias externas).

```bash
python3.12 -m venv .venv
.venv/bin/python main.py
```

## Qué demuestra `main.py`

1. **Simulación**: `gpt_4_call` (1.2 s), `claude_3_call` (0.8 s) y `local_llama_call` (3.0 s) usan `await asyncio.sleep()`.
2. **Orquestación**: las tres se lanzan a la vez con `asyncio.gather`; los logs muestran que arrancan en el mismo milisegundo.
3. **Resiliencia**: `asyncio.timeout(2)` por llamada; `local_llama` lanza `TimeoutError`, se captura y se registra, y se conservan las respuestas de las otras dos. Una variante envuelve todo el `gather` en un único `asyncio.timeout(2)` (cancela todo lo pendiente) y también captura el error sin detener el programa.
4. **Control de flujo**: 10 llamadas simuladas limitadas por `asyncio.Semaphore(2)`; el log muestra que nunca hay más de 2 en curso.
