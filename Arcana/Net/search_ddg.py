# Arcana/Net/search_ddg.py (VERSÃO 2025 ASSÍNCRONA)
import asyncio
import json
import os
from ddgs import DDGS  # Novo pacote!

# 🔥 Alterado de #armazen para #cache
HISTORY_PATH = os.path.join("Arcana", "#cache", "pesquisa_ddg.json")
LINKS_PATH = os.path.join("Arcana", "#cache", "pesquisa_links.json")

# ==========================================
# 🧹 SISTEMA DE AUTO-LIMPEZA
# ==========================================
def limpar_cache_de_pesquisa():
    """Deleta os arquivos de cache toda vez que a IA é reiniciada."""
    for path in [HISTORY_PATH, LINKS_PATH]:
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"[SISTEMA] 🗑️ Cache de pesquisa deletado: {os.path.basename(path)}")
            except Exception as e:
                print(f"[SISTEMA] ⚠️ Erro ao deletar cache {path}: {e}")

# Executa a limpeza automaticamente quando o módulo é importado pelo run.py
limpar_cache_de_pesquisa()
# ==========================================

# ==========================================
# 🔧 FUNÇÕES ASSÍNCRONAS DE I/O (INTERNAS)
# ==========================================

async def _load_history_async():
    """Carrega o histórico de pesquisas sem bloquear o event loop."""
    def _sync_load():
        if os.path.exists(HISTORY_PATH):
            try:
                with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}
    return await asyncio.to_thread(_sync_load)


async def _save_history_async(data):
    """Salva o histórico de pesquisas sem bloquear o event loop."""
    def _sync_save():
        os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    await asyncio.to_thread(_sync_save)


async def _save_links_async(query, links):
    """Salva os links de uma pesquisa sem bloquear o event loop."""
    def _sync_save():
        os.makedirs(os.path.dirname(LINKS_PATH), exist_ok=True)
        all_links = {}
        if os.path.exists(LINKS_PATH):
            try:
                with open(LINKS_PATH, "r", encoding="utf-8") as f:
                    all_links = json.load(f)
            except:
                pass
        all_links[query] = links
        with open(LINKS_PATH, "w", encoding="utf-8") as f:
            json.dump(all_links, f, indent=2, ensure_ascii=False)
    await asyncio.to_thread(_sync_save)

# ==========================================
# 📡 FUNÇÃO PRINCIPAL ASSÍNCRONA
# ==========================================

async def pesquisar_web(query):
    """
    Pesquisa assíncrona na web usando DuckDuckGo.
    
    - Verifica o cache em disco primeiro (via asyncio.to_thread).
    - Se não encontrado, executa a busca no DDGS em thread separada
      para não congelar o event loop principal do bot.
    
    Args:
        query (str): Termo de pesquisa.
    
    Returns:
        str: Resultados formatados ou mensagem de erro/fallback.
    """
    history = await _load_history_async()
    if query in history:
        print(f"(Cache) Usando resultado salvo: {query}")
        return history[query]

    print(f"(Web) Pesquisando: {query}")
    try:
        # 🔥 Envolve a chamada bloqueante do DDGS em asyncio.to_thread
        def _sync_search():
            with DDGS() as ddgs:
                # Backend padrão + região BR + max 5 resultados
                return list(ddgs.text(query, region="br-pt", max_results=5))

        results = await asyncio.to_thread(_sync_search)

        if not results:
            return "Não achei nada útil... Tenta reformular?"

        formatted = []
        links = []
        for r in results:
            title = r.get("title", "").strip()
            body = r.get("body", "").strip()
            href = r.get("href", "")
            if title and body:  # Filtra vazios
                formatted.append(f"• {title}: {body[:200]}...")  # Limita pra não poluir
            if href:
                links.append(href)

        answer = "\n".join(formatted)
        await _save_links_async(query, links)
        history[query] = answer
        await _save_history_async(history)
        print(f"📄 Resultados salvos: {len(formatted)} itens")
        return answer

    except Exception as e:
        print(f"❌ Erro DDG: {e}")
        return "Busca falhou – internet zuada ou query esquisita. Tenta de novo?"

# ==========================================
# 🔁 WRAPPERS SÍNCRONOS (COMPATIBILIDADE)
# ==========================================

def load_history():
    """
    Wrapper síncrono legado.
    Prefira usar 'await _load_history_async()' em código assíncrono.
    """
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_history(data):
    """
    Wrapper síncrono legado.
    Prefira usar 'await _save_history_async(data)' em código assíncrono.
    """
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_links(query, links):
    """
    Wrapper síncrono legado.
    Prefira usar 'await _save_links_async(query, links)' em código assíncrono.
    """
    os.makedirs(os.path.dirname(LINKS_PATH), exist_ok=True)
    all_links = {}
    if os.path.exists(LINKS_PATH):
        try:
            with open(LINKS_PATH, "r", encoding="utf-8") as f:
                all_links = json.load(f)
        except:
            pass
    all_links[query] = links
    with open(LINKS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_links, f, indent=2, ensure_ascii=False)


def search_ddg(query):
    """
    Wrapper síncrono legado para compatibilidade com código existente.
    
    Chama internamente 'pesquisar_web()' via asyncio.run().
    Em código assíncrono, prefira usar 'await pesquisar_web(query)'.
    """
    return asyncio.run(pesquisar_web(query))
