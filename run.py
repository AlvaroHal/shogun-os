"""
Shogun - Ponto de Entrada Principal (Fase 3 - Integração - Corrigido)
Inicializa os serviços globais e injeta dependências no Discord e demais módulos.
"""

import asyncio
import threading
import sys
import subprocess

import keyboard
from dotenv import load_dotenv

# ─── Core Global Services ───────────────────────────────────────────
from Arcana.Core.config import get_config
from Arcana.Core.event_bus import EventBus
from Arcana.Core.llm_client import LLMClient

# ─── Network & Automation ───────────────────────────────────────────
from Arcana.Net.memory_Rem import ShogunMemoria
from Arcana.Net.os_Rem import AsyncOSAutomation
from Arcana.Net.discord_Rem import setup_discord_bot

# ─── Application Layer ──────────────────────────────────────────────
from Arcana.Aura.voice_listener import LocalVoiceListener
from Arcana.Apps.gui_handler import RemGUI


# ══════════════════════════════════════════════════════════════════════
# Hotkey Handlers (mantidos aqui por serem bindings de sistema)
# ══════════════════════════════════════════════════════════════════════

def _toggle_visao(event_bus: EventBus, loop: asyncio.AbstractEventLoop):
    """Atalho F2: alterna visão computacional via EventBus."""
    asyncio.run_coroutine_threadsafe(
        event_bus.publish("toggle_visao", {"status": "toggle"}),
        loop,
    )


def _toggle_gatilho(event_bus: EventBus, loop: asyncio.AbstractEventLoop):
    """Atalho F3: alterna gatilho de voz via EventBus."""
    asyncio.run_coroutine_threadsafe(
        event_bus.publish("toggle_gatilho", {"status": "toggle"}),
        loop,
    )


def _toggle_gui():
    """Atalho F4: exibe/esconde a interface gráfica."""
    RemGUI.toggle()


# ══════════════════════════════════════════════════════════════════════
# Main Async Entry Point
# ══════════════════════════════════════════════════════════════════════

async def main():
    # ── 1. Carregar ambiente ────────────────────────────────────────
    load_dotenv()

    # ── 2. Instanciar serviços globais (ordem de dependência) ───────
    config        = get_config()
    event_bus    = EventBus()
    llm_client   = LLMClient()
    memoria      = ShogunMemoria()
    os_automation = AsyncOSAutomation(event_bus=event_bus)
    voice_listener = LocalVoiceListener(event_bus=event_bus, llm_client=llm_client)

    # ── 3. Iniciar GUI em thread separada ───────────────────────────
    # 🔥 Captura o loop assíncrono que está rodando o main agora
    loop_atual = asyncio.get_running_loop()

    gui_thread = threading.Thread(
        target=RemGUI.iniciar_gui_loop,
        args=(config.gui_title, event_bus, loop_atual), # 👈 Passando o loop como 3º argumento!
        daemon=True,
    )
    gui_thread.start()

    # ── 4. Registrar hotkeys globais ────────────────────────────────
    keyboard.add_hotkey('f4', _toggle_gui)
    keyboard.on_press_key('f2', lambda e: _toggle_visao(event_bus, loop_atual))
    keyboard.on_press_key('f3', lambda e: _toggle_gatilho(event_bus, loop_atual))

    # ── 5. Inicializar módulo VTuber Overlay (se ativo) ─────────────
    if config.vtuber_overlay_script.exists():
        print("🎭 Iniciando módulo VTuber Overlay...")
        try:
            subprocess.Popen(
                [sys.executable, str(config.vtuber_overlay_script)],
                
            )
        except Exception as e:
            print(f"❌ Erro ao iniciar VTuber: {e}")

    # ── 6. Iniciar Discord Bot com as dependências corretas ─────────
    print("🌐 Conectando Shogun ao Discord...")
    await setup_discord_bot(
        llm_client=llm_client,
        memoria=memoria,
        os_automation=os_automation,
        event_bus=event_bus,
    )

    # ── 7. Loop de manutenção (mantém o processo vivo) ─────────────
    while True:
        await asyncio.sleep(3600)


# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    asyncio.run(main())
