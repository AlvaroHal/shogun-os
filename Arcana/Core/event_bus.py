"""
EventBus assíncrono baseado em asyncio.Queue.

Permite que módulos publiquem e assinem eventos de forma desacoplada,
utilizando filas assíncronas por tópico para distribuição de mensagens.
"""

import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List


class EventBus:
    """
    Barramento de eventos assíncrono com suporte a subscribe/publish.

    Cada tópico mantém uma lista de callbacks assíncronos. Quando um evento
    é publicado, todos os callbacks inscritos naquele tópico são invocados.

    Uso:
        bus = EventBus()

        async def handler(event):
            print(f"Recebido: {event}")

        bus.subscribe("audio:transcricao", handler)
        await bus.publish("audio:transcricao", {"texto": "olá"})
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Any], Coroutine[Any, Any, None]]]] = (
            defaultdict(list)
        )
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running: bool = False
        self._worker_task: asyncio.Task | None = None

    def subscribe(
        self, topic: str, callback: Callable[[Any], Coroutine[Any, Any, None]]
    ) -> None:
        """
        Inscreve um callback assíncrono em um tópico.

        Args:
            topic: Nome do tópico (ex: 'audio:transcricao').
            callback: Corrotina que recebe o payload do evento.
        """
        self._subscribers[topic].append(callback)

    def unsubscribe(
        self, topic: str, callback: Callable[[Any], Coroutine[Any, Any, None]]
    ) -> None:
        """
        Remove um callback de um tópico.

        Args:
            topic: Nome do tópico.
            callback: Callback a ser removido.
        """
        if topic in self._subscribers:
            try:
                self._subscribers[topic].remove(callback)
            except ValueError:
                pass

    async def publish(self, topic: str, event: Any) -> None:
        """
        Publica um evento em um tópico, invocando todos os callbacks inscritos.

        Args:
            topic: Nome do tópico.
            event: Payload do evento (qualquer tipo serializável ou objeto).
        """
        callbacks = self._subscribers.get(topic, [])
        if not callbacks:
            return

        # Dispara todos os callbacks em paralelo, coletando exceções
        results = await asyncio.gather(
            *[callback(event) for callback in callbacks],
            return_exceptions=True,
        )

        # Registra exceções sem interromper o fluxo
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Em produção, substituir por logging adequado
                print(
                    f"[EventBus] Erro no callback {callbacks[i].__name__} "
                    f"para tópico '{topic}': {result}"
                )

    # --- Métodos opcionais para uso avançado com fila interna ---

    async def start(self) -> None:
        """Inicia o worker interno que processa a fila de eventos."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        """Para o worker interno de forma graciosa."""
        self._running = False
        await self._queue.put(None)  # Sinal de parada
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def enqueue(self, topic: str, event: Any) -> None:
        """
        Enfileira um evento para processamento assíncrono pelo worker.
        Útil quando se deseja garantir ordem de processamento ou
        backpressure.

        Args:
            topic: Nome do tópico.
            event: Payload do evento.
        """
        await self._queue.put((topic, event))

    async def _worker(self) -> None:
        """Worker que consome a fila interna e faz dispatch dos eventos."""
        while self._running:
            item = await self._queue.get()
            if item is None:
                break
            topic, event = item
            await self.publish(topic, event)
            self._queue.task_done()
