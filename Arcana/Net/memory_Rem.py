import asyncio
import os

import chromadb


class ShogunMemoria:
    """Memória vetorial do Shogun com wrappers assíncronos sobre ChromaDB.

    Como a biblioteca ChromaDB é nativamente síncrona/bloqueante, todas as
    operações de leitura e escrita no banco são delegadas a
    ``asyncio.to_thread``, evitando que a thread principal do bot congele
    durante consultas de memória da IA.
    """

    def __init__(self, caminho_banco: str = "D:/Shogun/Memoria_Vectorial"):
        self.caminho_banco = caminho_banco
        self.client = None
        self.collection = None
        self.contador_id = 0

    # ------------------------------------------------------------------
    # Inicialização assíncrona
    # ------------------------------------------------------------------

    async def inicializar(self) -> None:
        """Conecta ao ChromaDB em uma thread separada (não bloqueia o event loop)."""
        await asyncio.to_thread(self._inicializar_sync)

    def _inicializar_sync(self) -> None:
        """Lógica síncrona de conexão – executada dentro de to_thread."""
        if not os.path.exists(self.caminho_banco):
            os.makedirs(self.caminho_banco)

        self.client = chromadb.PersistentClient(path=self.caminho_banco)
        self.collection = self.client.get_or_create_collection(name="cerebro_shogun")
        self.contador_id = self.collection.count()

    # ------------------------------------------------------------------
    # Wrappers assíncronos públicos
    # ------------------------------------------------------------------

    async def salvar_memoria(self, texto: str, categoria: str = "tecnica") -> None:
        """Salva uma informação no cérebro vetorial sem bloquear o loop."""
        await asyncio.to_thread(self._guardar_fato_sync, texto, categoria)

    async def buscar_memoria(self, pergunta: str, limite: int = 2) -> str:
        """Busca as memórias mais relevantes para a pergunta, de forma assíncrona."""
        return await asyncio.to_thread(self._buscar_contexto_sync, pergunta, limite)

    # ------------------------------------------------------------------
    # Implementações síncronas internas (chamadas via to_thread)
    # ------------------------------------------------------------------

    def _guardar_fato_sync(self, texto: str, categoria: str) -> None:
        """Operação síncrona de escrita no ChromaDB."""
        self.contador_id += 1
        self.collection.add(
            documents=[texto],
            metadatas=[{"categoria": categoria}],
            ids=[f"memoria_{self.contador_id}"],
        )
        print(f"🧠 [MEMÓRIA] Shogun memorizou para sempre: {texto}")

    def _buscar_contexto_sync(self, pergunta: str, limite: int) -> str:
        """Operação síncrona de consulta no ChromaDB."""
        if self.contador_id == 0:
            return ""

        resultados = self.collection.query(
            query_texts=[pergunta],
            n_results=limite,
        )

        memorias = resultados["documents"][0]
        if memorias:
            contexto = " ".join(memorias)
            return f"\n[Fatos Relevantes da Memória: {contexto}]"
        return ""


# ------------------------------------------------------------------
# Teste de Bancada (assíncrono)
# ------------------------------------------------------------------
async def _teste():
    cerebro = ShogunMemoria()
    await cerebro.inicializar()

    await cerebro.salvar_memoria(
        "O PPA PROG adaptado com Bluetooth só liga com 12v, com 5v ele não liga de jeito nenhum."
    )

    lembranca = await cerebro.buscar_memoria(
        "Shogun, qual é a voltagem certa pra ligar aquele meu projeto do Prog?"
    )
    print(f"Resultado da busca: {lembranca}")


if __name__ == "__main__":
    asyncio.run(_teste())
