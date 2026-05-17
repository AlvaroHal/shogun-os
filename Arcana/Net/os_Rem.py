"""
Módulo de Rede e Sistema Operacional - Arcana
Fornece classes assíncronas para Discord, Memória, Sistema e Automação de Interface.
Refatorado na Fase 1: AsyncOSAutomation extraída do run.py com asyncio.to_thread.
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import pyautogui
import pygetwindow as gw
from PIL import Image

# Tentativa de importar o EventBus (Fase 0)
try:
    from Arcana.Core.event_bus import EventBus
except ImportError:
    EventBus = None
    print("[os_Rem] EventBus nao encontrado, operando sem eventos.")


# =============================================================================
# 1. AUTOMACAO DE SISTEMA OPERACIONAL (NOVA - Extraida do run.py)
# =============================================================================

class AsyncOSAutomation:
    """
    Classe para automação de interface do sistema operacional.
    Encapsula operações com pyautogui, pygetwindow e pynput
    usando asyncio.to_thread() para não travar o event loop.
    
    Extraída da classe 'DemonHands' e métodos relacionados do run.py.
    """

    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        self._teclado_controller = None  # lazy init para pynput
        print("[AsyncOSAutomation] Inicializada - Automacao de SO assincrona pronta.")

    # ------------------------------------------------------------
    # Helpers de teclado (lazy import pynput para nao travar)
    # ------------------------------------------------------------
    def _get_teclado(self):
        if self._teclado_controller is None:
            from pynput.keyboard import Controller as KeyboardController
            self._teclado_controller = KeyboardController()
        return self._teclado_controller

    def _get_key_obj(self, tecla: str):
        """Converte string para objeto Key do pynput."""
        from pynput.keyboard import Key
        tecla_map = {
            'enter': Key.enter,
            'tab': Key.tab,
            'esc': Key.esc,
            'escape': Key.esc,
            'space': Key.space,
            'backspace': Key.backspace,
            'delete': Key.delete,
            'shift': Key.shift,
            'ctrl': Key.ctrl,
            'alt': Key.alt,
            'cmd': Key.cmd,
            'win': Key.cmd,
            'up': Key.up,
            'down': Key.down,
            'left': Key.left,
            'right': Key.right,
            'home': Key.home,
            'end': Key.end,
            'pageup': Key.page_up,
            'pagedown': Key.page_down,
            'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
            'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
            'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
            'printscreen': Key.print_screen,
            'capslock': Key.caps_lock,
        }
        return tecla_map.get(tecla.lower(), tecla)

    # ------------------------------------------------------------
    # Métodos síncronos (executados via to_thread)
    # ------------------------------------------------------------

    def _mover_mouse_sync(self, x: int, y: int, duracao: float = 0.2):
        """Move o mouse para coordenadas (x, y)."""
        pyautogui.moveTo(x, y, duration=duracao)
        return {"status": "ok", "x": x, "y": y}

    def _arrastar_mouse_sync(self, x: int, y: int, duracao: float = 0.3):
        """Arrasta o mouse ate (x, y)."""
        pyautogui.dragTo(x, y, duration=duracao)
        return {"status": "ok", "x": x, "y": y}

    def _clicar_sync(self, x: Optional[int] = None, y: Optional[int] = None,
                     botao: str = 'left', cliques: int = 1):
        """Clica com o mouse."""
        if x is not None and y is not None:
            pyautogui.click(x, y, clicks=cliques, button=botao)
        else:
            pyautogui.click(clicks=cliques, button=botao)
        pos = pyautogui.position()
        return {"status": "ok", "x": pos.x, "y": pos.y, "botao": botao}

    def _duplo_clique_sync(self, x: Optional[int] = None, y: Optional[int] = None):
        """Duplo clique com o mouse."""
        return self._clicar_sync(x, y, botao='left', cliques=2)

    def _clique_direito_sync(self, x: Optional[int] = None, y: Optional[int] = None):
        """Clique direito com o mouse."""
        return self._clicar_sync(x, y, botao='right', cliques=1)

    def _digitar_sync(self, texto: str, intervalo: float = 0.05):
        """Digita texto via teclado."""
        pyautogui.write(texto, interval=intervalo)
        return {"status": "ok", "texto": texto}

    def _pressionar_tecla_sync(self, tecla: str):
        """Pressiona uma tecla especifica."""
        pyautogui.press(tecla)
        return {"status": "ok", "tecla": tecla}

    def _atalho_sync(self, *teclas):
        """Executa um atalho de teclado (ex: 'ctrl', 'c')."""
        pyautogui.hotkey(*teclas)
        return {"status": "ok", "atalho": '+'.join(teclas)}

    def _rolar_scroll_sync(self, direcao: str, quantidade: int = 3):
        """Rola o scroll do mouse. direcao: 'cima'/'baixo'."""
        valor = quantidade if direcao.lower() in ['cima', 'up'] else -quantidade
        pyautogui.scroll(valor)
        return {"status": "ok", "direcao": direcao, "quantidade": quantidade}

    def _screenshot_sync(self, nome_arquivo: Optional[str] = None,
                         regiao: Optional[Tuple[int, int, int, int]] = None):
        """Captura screenshot da tela."""
        if nome_arquivo is None:
            nome_arquivo = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        if regiao:
            screenshot = pyautogui.screenshot(region=regiao)
        else:
            screenshot = pyautogui.screenshot()
        screenshot.save(nome_arquivo)
        return {"status": "ok", "arquivo": nome_arquivo}

    def _localizar_imagem_sync(self, imagem: str, confianca: float = 0.8):
        """Localiza uma imagem na tela."""
        try:
            localizacao = pyautogui.locateOnScreen(imagem, confidence=confianca)
            if localizacao:
                centro = pyautogui.center(localizacao)
                return {"status": "ok", "x": centro.x, "y": centro.y,
                        "regiao": (localizacao.left, localizacao.top,
                                   localizacao.width, localizacao.height)}
            return {"status": "nao_encontrado", "imagem": imagem}
        except Exception as e:
            return {"status": "erro", "erro": str(e)}

    def _aguardar_imagem_sync(self, imagem: str, timeout: int = 10, confianca: float = 0.8):
        """Aguarda uma imagem aparecer na tela."""
        try:
            localizacao = pyautogui.locateOnScreen(imagem, confidence=confianca,
                                                   minSearchTime=timeout)
            # Fallback manual com loop
            inicio = time.time()
            while time.time() - inicio < timeout:
                localizacao = pyautogui.locateOnScreen(imagem, confidence=confianca)
                if localizacao:
                    centro = pyautogui.center(localizacao)
                    return {"status": "ok", "x": centro.x, "y": centro.y}
                time.sleep(0.5)
            return {"status": "timeout", "imagem": imagem}
        except Exception as e:
            return {"status": "erro", "erro": str(e)}

    def _posicao_mouse_sync(self):
        """Retorna a posicao atual do mouse."""
        pos = pyautogui.position()
        return {"status": "ok", "x": pos.x, "y": pos.y}

    def _tamanho_tela_sync(self):
        """Retorna o tamanho da tela."""
        tamanho = pyautogui.size()
        return {"status": "ok", "largura": tamanho.width, "altura": tamanho.height}

    def _gerenciar_janela_sync(self, ordem: str):
        """
        Gerencia janelas do sistema.
        Ordens suportadas:
          - 'minimizar_tudo' / 'min_all': minimiza todas as janelas
          - 'mostrar_area_trabalho' / 'show_desktop': mostra area de trabalho
          - 'lista_janelas' / 'list_windows': lista janelas abertas
          - 'focar:<titulo_parcial>': foca uma janela pelo titulo
          - 'minimizar:<titulo_parcial>': minimiza janela especifica
          - 'maximizar:<titulo_parcial>': maximiza janela especifica
          - 'fechar:<titulo_parcial>': fecha janela especifica
        """
        ordem_lower = ordem.lower().strip()

        if ordem_lower in ['minimizar_tudo', 'min_all']:
            pyautogui.hotkey('win', 'd')
            return {"status": "ok", "acao": "minimizar_tudo"}

        elif ordem_lower in ['mostrar_area_trabalho', 'show_desktop']:
            pyautogui.hotkey('win', 'd')
            return {"status": "ok", "acao": "mostrar_area_trabalho"}

        elif ordem_lower in ['lista_janelas', 'list_windows']:
            try:
                janelas = gw.getAllWindows()
                lista = []
                for j in janelas:
                    if j.title and j.title.strip():
                        lista.append({
                            "titulo": j.title,
                            "visivel": j.visible,
                            "minimizado": j.isMinimized,
                            "posicao": {"x": j.left, "y": j.top,
                                        "largura": j.width, "altura": j.height}
                        })
                return {"status": "ok", "janelas": lista[:20]}  # limita a 20
            except Exception as e:
                return {"status": "erro", "erro": str(e)}

        elif ordem_lower.startswith('focar:') or ordem_lower.startswith('focus:'):
            titulo = ordem.split(':', 1)[1].strip()
            try:
                janelas = gw.getWindowsWithTitle(titulo)
                if janelas:
                    janela = janelas[0]
                    if janela.isMinimized:
                        janela.restore()
                    janela.activate()
                    janela.moveTo(janela.left, janela.top)  # garante visibilidade
                    return {"status": "ok", "acao": "focar", "titulo": janela.title}
                return {"status": "nao_encontrado", "titulo": titulo}
            except Exception as e:
                return {"status": "erro", "erro": str(e)}

        elif ordem_lower.startswith('minimizar:') or ordem_lower.startswith('minimize:'):
            titulo = ordem.split(':', 1)[1].strip()
            try:
                janelas = gw.getWindowsWithTitle(titulo)
                if janelas:
                    janelas[0].minimize()
                    return {"status": "ok", "acao": "minimizar", "titulo": janelas[0].title}
                return {"status": "nao_encontrado", "titulo": titulo}
            except Exception as e:
                return {"status": "erro", "erro": str(e)}

        elif ordem_lower.startswith('maximizar:') or ordem_lower.startswith('maximize:'):
            titulo = ordem.split(':', 1)[1].strip()
            try:
                janelas = gw.getWindowsWithTitle(titulo)
                if janelas:
                    janelas[0].maximize()
                    return {"status": "ok", "acao": "maximizar", "titulo": janelas[0].title}
                return {"status": "nao_encontrado", "titulo": titulo}
            except Exception as e:
                return {"status": "erro", "erro": str(e)}

        elif ordem_lower.startswith('fechar:') or ordem_lower.startswith('close:'):
            titulo = ordem.split(':', 1)[1].strip()
            try:
                janelas = gw.getWindowsWithTitle(titulo)
                if janelas:
                    janelas[0].close()
                    return {"status": "ok", "acao": "fechar", "titulo": janelas[0].title}
                return {"status": "nao_encontrado", "titulo": titulo}
            except Exception as e:
                return {"status": "erro", "erro": str(e)}

        elif ordem_lower.startswith('mover:') or ordem_lower.startswith('move:'):
            # Formato: mover:<titulo>:x:y:largura:altura
            partes = ordem.split(':')
            if len(partes) >= 5:
                titulo = partes[1].strip()
                try:
                    x = int(partes[2])
                    y = int(partes[3])
                    w = int(partes[4])
                    h = int(partes[5]) if len(partes) > 5 else None
                    janelas = gw.getWindowsWithTitle(titulo)
                    if janelas:
                        if h:
                            janelas[0].moveTo(x, y)
                            janelas[0].resizeTo(w, h)
                        else:
                            janelas[0].moveTo(x, y)
                        return {"status": "ok", "acao": "mover",
                                "titulo": janelas[0].title,
                                "posicao": {"x": x, "y": y, "largura": w,
                                            "altura": h or janelas[0].height}}
                    return {"status": "nao_encontrado", "titulo": titulo}
                except Exception as e:
                    return {"status": "erro", "erro": str(e)}

        return {"status": "erro", "erro": f"Ordem '{ordem}' nao reconhecida"}

    # ------------------------------------------------------------
    # Métodos assíncronos (interface pública)
    # ------------------------------------------------------------

    async def mover_mouse(self, x: int, y: int, duracao: float = 0.2) -> Dict:
        """Move o mouse assincronamente."""
        return await asyncio.to_thread(self._mover_mouse_sync, x, y, duracao)

    async def arrastar_mouse(self, x: int, y: int, duracao: float = 0.3) -> Dict:
        """Arrasta o mouse assincronamente."""
        return await asyncio.to_thread(self._arrastar_mouse_sync, x, y, duracao)

    async def clicar(self, x: Optional[int] = None, y: Optional[int] = None,
                     botao: str = 'left', cliques: int = 1) -> Dict:
        """Clica com o mouse assincronamente."""
        return await asyncio.to_thread(self._clicar_sync, x, y, botao, cliques)

    async def duplo_clique(self, x: Optional[int] = None,
                           y: Optional[int] = None) -> Dict:
        """Duplo clique assincrono."""
        return await asyncio.to_thread(self._duplo_clique_sync, x, y)

    async def clique_direito(self, x: Optional[int] = None,
                             y: Optional[int] = None) -> Dict:
        """Clique direito assincrono."""
        return await asyncio.to_thread(self._clique_direito_sync, x, y)

    async def digitar(self, texto: str, intervalo: float = 0.05) -> Dict:
        """Digita texto assincronamente."""
        return await asyncio.to_thread(self._digitar_sync, texto, intervalo)

    async def pressionar_tecla(self, tecla: str) -> Dict:
        """Pressiona uma tecla assincronamente."""
        return await asyncio.to_thread(self._pressionar_tecla_sync, tecla)

    async def atalho(self, *teclas) -> Dict:
        """Executa atalho de teclado assincronamente."""
        return await asyncio.to_thread(self._atalho_sync, *teclas)

    async def rolar_scroll(self, direcao: str, quantidade: int = 3) -> Dict:
        """Rola o scroll do mouse assincronamente."""
        return await asyncio.to_thread(self._rolar_scroll_sync, direcao, quantidade)

    async def screenshot(self, nome_arquivo: Optional[str] = None,
                         regiao: Optional[Tuple[int, int, int, int]] = None) -> Dict:
        """Captura screenshot da tela assincronamente."""
        return await asyncio.to_thread(self._screenshot_sync, nome_arquivo, regiao)

    async def localizar_imagem(self, imagem: str, confianca: float = 0.8) -> Dict:
        """Localiza uma imagem na tela assincronamente."""
        return await asyncio.to_thread(self._localizar_imagem_sync, imagem, confianca)

    async def aguardar_imagem(self, imagem: str, timeout: int = 10,
                              confianca: float = 0.8) -> Dict:
        """Aguarda uma imagem aparecer na tela."""
        return await asyncio.to_thread(self._aguardar_imagem_sync, imagem,
                                       timeout, confianca)

    async def posicao_mouse(self) -> Dict:
        """Retorna a posicao atual do mouse."""
        return await asyncio.to_thread(self._posicao_mouse_sync)

    async def tamanho_tela(self) -> Dict:
        """Retorna o tamanho da tela."""
        return await asyncio.to_thread(self._tamanho_tela_sync)

    async def gerenciar_janela(self, ordem: str) -> Dict:
        """Gerencia janelas do sistema assincronamente."""
        return await asyncio.to_thread(self._gerenciar_janela_sync, ordem)

    # ------------------------------------------------------------
    # Métodos de conveniência com validação
    # ------------------------------------------------------------

    async def abrir_aplicativo(self, nome_app: str) -> Dict:
        """Abre um aplicativo pelo nome (Windows)."""
        async def _abrir():
            try:
                # Tenta abrir via comando start do Windows
                subprocess.Popen(['start', nome_app], shell=True)
                await asyncio.sleep(1.0)
                return {"status": "ok", "aplicativo": nome_app}
            except Exception as e:
                return {"status": "erro", "erro": str(e)}
        return await _abrir()

    async def digitar_com_enter(self, texto: str) -> Dict:
        """Digita texto e pressiona Enter."""
        await self.digitar(texto)
        return await self.pressionar_tecla('enter')

    async def copiar(self) -> Dict:
        """Copia o texto selecionado (Ctrl+C)."""
        return await self.atalho('ctrl', 'c')

    async def colar(self) -> Dict:
        """Cola o texto (Ctrl+V)."""
        return await self.atalho('ctrl', 'v')

    async def selecionar_tudo(self) -> Dict:
        """Seleciona tudo (Ctrl+A)."""
        return await self.atalho('ctrl', 'a')

    async def desfazer(self) -> Dict:
        """Desfaz ultima acao (Ctrl+Z)."""
        return await self.atalho('ctrl', 'z')

    async def salvar(self) -> Dict:
        """Salva (Ctrl+S)."""
        return await self.atalho('ctrl', 's')

    async def alternar_janela(self) -> Dict:
        """Alterna entre janelas (Alt+Tab)."""
        return await self.atalho('alt', 'tab')

    async def abrir_menu_iniciar(self) -> Dict:
        """Abre o menu iniciar (Win)."""
        return await self.pressionar_tecla('win')

    async def bloquear_tela(self) -> Dict:
        """Bloqueia a tela (Win+L)."""
        return await self.atalho('win', 'l')


# =============================================================================
# 2. DISCORD ASYNC WRAPPER
# =============================================================================

class AsyncDiscordRem:
    """Wrapper assincrono para o bot do Discord."""

    def __init__(self, discord_bot=None):
        self.bot = discord_bot

    async def enviar_mensagem(self, canal_id: int, conteudo: str) -> Dict:
        """Envia uma mensagem para um canal do Discord."""
        if self.bot is None:
            return {"status": "erro", "erro": "Bot Discord nao inicializado"}
        try:
            canal = self.bot.get_channel(canal_id)
            if canal:
                msg = await canal.send(conteudo)
                return {"status": "ok", "id_mensagem": msg.id}
            return {"status": "erro", "erro": f"Canal {canal_id} nao encontrado"}
        except Exception as e:
            return {"status": "erro", "erro": str(e)}

    async def enviar_embed(self, canal_id: int, titulo: str,
                           descricao: str, cor: int = 0x00ff00) -> Dict:
        """Envia uma mensagem embed para um canal do Discord."""
        if self.bot is None:
            return {"status": "erro", "erro": "Bot Discord nao inicializado"}
        try:
            import discord
            canal = self.bot.get_channel(canal_id)
            if canal:
                embed = discord.Embed(title=titulo, description=descricao, color=cor)
                msg = await canal.send(embed=embed)
                return {"status": "ok", "id_mensagem": msg.id}
            return {"status": "erro", "erro": f"Canal {canal_id} nao encontrado"}
        except Exception as e:
            return {"status": "erro", "erro": str(e)}


# =============================================================================
# 3. MEMORY ASYNC WRAPPER
# =============================================================================

class AsyncMemoryRem:
    """Wrapper assincrono para memoria vetorial."""

    def __init__(self, collection=None):
        self.collection = collection

    async def adicionar(self, texto: str, metadata: dict = None) -> Dict:
        """Adiciona um texto a memoria vetorial."""
        if self.collection is None:
            return {"status": "erro", "erro": "Colecao de memoria nao inicializada"}
        try:
            import uuid
            doc_id = str(uuid.uuid4())
            self.collection.add(documents=[texto], metadatas=[metadata or {}], ids=[doc_id])
            return {"status": "ok", "id": doc_id}
        except Exception as e:
            return {"status": "erro", "erro": str(e)}

    async def buscar(self, consulta: str, n_resultados: int = 5) -> Dict:
        """Busca na memoria vetorial."""
        if self.collection is None:
            return {"status": "erro", "erro": "Colecao de memoria nao inicializada"}
        try:
            resultados = self.collection.query(query_texts=[consulta], n_results=n_resultados)
            docs = []
            if resultados and resultados.get('documents'):
                for i, doc in enumerate(resultados['documents'][0]):
                    docs.append({
                        "texto": doc,
                        "metadata": resultados['metadatas'][0][i] if resultados.get('metadatas') else {},
                        "distancia": resultados['distances'][0][i] if resultados.get('distances') else None
                    })
            return {"status": "ok", "resultados": docs}
        except Exception as e:
            return {"status": "erro", "erro": str(e)}


# =============================================================================
# 4. SYSTEM ASYNC WRAPPER
# =============================================================================

class AsyncSystemRem:
    """Wrapper assincrono para comandos do sistema operacional."""

    def __init__(self):
        pass

    async def executar_comando(self, comando: str, timeout: int = 30) -> Dict:
        """Executa um comando no terminal e retorna o resultado."""
        try:
            processo = await asyncio.create_subprocess_shell(
                comando,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                processo.communicate(), timeout=timeout
            )
            return {
                "status": "ok",
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "codigo": processo.returncode
            }
        except asyncio.TimeoutError:
            return {"status": "erro", "erro": f"Timeout ({timeout}s)"}
        except Exception as e:
            return {"status": "erro", "erro": str(e)}

    async def info_sistema(self) -> Dict:
        """Retorna informacoes do sistema."""
        import platform
        return {
            "status": "ok",
            "sistema": platform.system(),
            "versao": platform.version(),
            "arquitetura": platform.architecture()[0],
            "hostname": platform.node(),
            "python": sys.version
        }

    async def abrir_arquivo(self, caminho: str) -> Dict:
        """Abre um arquivo com o programa padrao."""
        try:
            os.startfile(caminho)
            return {"status": "ok", "arquivo": caminho}
        except Exception as e:
            return {"status": "erro", "erro": str(e)}

    async def listar_diretorio(self, caminho: str = ".") -> Dict:
        """Lista conteudo de um diretorio."""
        try:
            p = Path(caminho)
            if not p.exists():
                return {"status": "erro", "erro": f"Diretorio '{caminho}' nao encontrado"}
            arquivos = []
            for item in p.iterdir():
                arquivos.append({
                    "nome": item.name,
                    "tipo": "diretorio" if item.is_dir() else "arquivo",
                    "tamanho": item.stat().st_size if item.is_file() else None
                })
            return {"status": "ok", "caminho": str(p.absolute()), "itens": arquivos}
        except Exception as e:
            return {"status": "erro", "erro": str(e)}


# =============================================================================
# 5. SEARCH ASYNC WRAPPER
# =============================================================================

class AsyncSearchRem:
    """Wrapper assincrono para buscas web via DuckDuckGo."""

    def __init__(self):
        pass

    async def buscar_web(self, consulta: str, max_resultados: int = 5) -> Dict:
        """Realiza uma busca na web via DuckDuckGo."""
        try:
            from duckduckgo_search import DDGS

            def _buscar():
                with DDGS() as ddgs:
                    resultados = list(ddgs.text(consulta, max_results=max_resultados))
                    return [
                        {
                            "titulo": r.get('title', ''),
                            "url": r.get('href', ''),
                            "descricao": r.get('body', '')
                        }
                        for r in resultados
                    ]

            resultados = await asyncio.to_thread(_buscar)
            return {"status": "ok", "resultados": resultados}
        except ImportError:
            return {"status": "erro", "erro": "Biblioteca duckduckgo-search nao instalada"}
        except Exception as e:
            return {"status": "erro", "erro": str(e)}


# =============================================================================
# 6. FACTORY PARA INICIALIZACAO RAPIDA
# =============================================================================

def create_os_automation(event_bus=None) -> AsyncOSAutomation:
    """Factory para criar AsyncOSAutomation."""
    return AsyncOSAutomation(event_bus=event_bus)


def create_system_rem() -> AsyncSystemRem:
    """Factory para criar AsyncSystemRem."""
    return AsyncSystemRem()


def create_search_rem() -> AsyncSearchRem:
    """Factory para criar AsyncSearchRem."""
    return AsyncSearchRem()
