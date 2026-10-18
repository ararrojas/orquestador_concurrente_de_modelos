"""Orquestador concurrente de modelos de IA simulados con asyncio."""

import asyncio
import logging
import random
import sys
import time

if sys.version_info < (3, 12):
    sys.exit("Se requiere Python 3.12 o superior")

TOTAL_TIMEOUT = 2.0
MAX_CONCURRENT = 2
NUM_SIMULATIONS = 10

logging.basicConfig(level=logging.INFO, format="[%(relativeCreated)5d ms] %(levelname)-7s %(message)s")
log = logging.getLogger("orquestador")


# ---------------------------------------------------------------------------
# 2. Simulación de llamadas (latencia de red con asyncio.sleep, no bloqueante)
# ---------------------------------------------------------------------------

async def _simulated_call(model: str, latency: float, prompt: str) -> str:
    log.info("→ %-12s inicia (latencia simulada %.1fs)", model, latency)
    await asyncio.sleep(latency)
    log.info("← %-12s responde", model)
    return f"[{model}] respuesta a: {prompt!r}"


async def gpt_4_call(prompt: str) -> str:
    return await _simulated_call("gpt-4", 1.2, prompt)


async def claude_3_call(prompt: str) -> str:
    return await _simulated_call("claude-3", 0.8, prompt)


async def local_llama_call(prompt: str) -> str:
    # Más lenta que el límite: provocará un TimeoutError controlado.
    return await _simulated_call("local-llama", 3.0, prompt)


# ---------------------------------------------------------------------------
# 4. Resiliencia: timeout de 2 s con captura de TimeoutError
# ---------------------------------------------------------------------------

async def with_timeout(name: str, coro, timeout: float = TOTAL_TIMEOUT) -> str | None:
    try:
        async with asyncio.timeout(timeout):
            return await coro
    except TimeoutError:
        log.error("✗ %-12s superó el timeout de %.1fs; se continúa sin ella", name, timeout)
        return None


# ---------------------------------------------------------------------------
# 3. Orquestación: las tres llamadas en paralelo con asyncio.gather
# ---------------------------------------------------------------------------

async def query_all_models(prompt: str) -> dict[str, str | None]:
    log.info("=== Orquestación: 3 modelos en paralelo (timeout total %.1fs) ===", TOTAL_TIMEOUT)
    calls = {
        "gpt-4": gpt_4_call(prompt),
        "claude-3": claude_3_call(prompt),
        "local-llama": local_llama_call(prompt),
    }
    start = time.perf_counter()
    results = await asyncio.gather(*(with_timeout(n, c) for n, c in calls.items()))
    log.info("Orquestación terminada en %.2fs", time.perf_counter() - start)
    return dict(zip(calls, results))


async def query_all_models_global_timeout(prompt: str) -> None:
    log.info("=== Variante: un único timeout global sobre el gather ===")
    try:
        async with asyncio.timeout(TOTAL_TIMEOUT):
            await asyncio.gather(gpt_4_call(prompt), claude_3_call(prompt), local_llama_call(prompt))
    except TimeoutError:
        log.error("✗ La ejecución total superó %.1fs; llamadas pendientes canceladas", TOTAL_TIMEOUT)


# ---------------------------------------------------------------------------
# 5. Control de flujo: 10 simulaciones, máximo 2 simultáneas (Semaphore)
# ---------------------------------------------------------------------------

async def throttled_simulations() -> None:
    log.info("=== Control de flujo: %d llamadas, máx. %d simultáneas ===",
             NUM_SIMULATIONS, MAX_CONCURRENT)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    running = 0
    peak = 0
    rng = random.Random(42)

    async def limited_call(i: int) -> str:
        nonlocal running, peak
        log.info("  tarea %02d creada, esperando turno", i)
        async with semaphore:
            running += 1
            peak = max(peak, running)
            log.info("  tarea %02d EJECUTANDO (en curso: %d)", i, running)
            try:
                await asyncio.sleep(rng.uniform(0.3, 0.7))
                return f"resultado-{i}"
            finally:
                running -= 1
                log.info("  tarea %02d termina", i)

    start = time.perf_counter()
    results = await asyncio.gather(*(limited_call(i) for i in range(1, NUM_SIMULATIONS + 1)))
    log.info("%d resultados en %.2fs; concurrencia máxima observada: %d",
             len(results), time.perf_counter() - start, peak)
    assert peak <= MAX_CONCURRENT


async def main() -> None:
    results = await query_all_models("¿Qué es asyncio?")
    for model, answer in results.items():
        log.info("  %-12s → %s", model, answer or "sin respuesta (timeout)")

    await query_all_models_global_timeout("¿Qué es asyncio?")
    await throttled_simulations()
    log.info("Programa finalizado correctamente")


if __name__ == "__main__":
    asyncio.run(main())
