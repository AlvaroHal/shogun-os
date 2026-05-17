"""Configuracao centralizada do Shogun - Single Source of Truth.

Substitui todas as constantes hardcoded espalhadas em run.py.
Carrega de variaveis de ambiente (.env) com fallback para defaults.

Baseado no codigo real de run.py (877 linhas, 2026-05-17).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ShogunConfig:
    """Configuracao global do projeto Shogun.

    Centraliza TODAS as constantes que estavam hardcoded em run.py.
    Carregadas do .env ou com defaults seguros.
    """

    # ---- Caminhos Base ----
    base_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent
    )
    arcana_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
    )
    armazen_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "armazen"
    )

    # ---- Arquivos de Dados (paths reais do run.py) ----
    brain_file: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
        / "armazen"
        / "brain.json"
    )
    memoria_file: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
        / "armazen"
        / "memoria.json"
    )
    search_memory_file: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
        / "armazen"
        / "pesquisa_memoria.json"
    )
    persona_file: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
        / "armazen"
        / "persona.txt"
    )

    # ---- Groq Cloud (provedor LLM real, NAO Ollama) ----
    groq_api_key_llm: str = field(
        default_factory=lambda: os.getenv("GROQ_API_KEY_LLM", "")
    )
    groq_api_key_vision: str = field(
        default_factory=lambda: os.getenv("GROQ_API_KEY_VISION", "")
    )
    groq_model_main: str = field(
        default_factory=lambda: os.getenv("GROQ_MODEL_MAIN", "llama-3.3-70b-versatile")
    )
    groq_model_fast: str = field(
        default_factory=lambda: os.getenv(
            "GROQ_MODEL_FAST", "llama-3.1-8b-instant"
        )
    )
    groq_model_vision: str = field(
        default_factory=lambda: os.getenv(
            "GROQ_MODEL_VISION", "meta-llama/llama-4-scout-17b-16e-instruct"
        )
    )
    groq_whisper_model: str = field(
        default_factory=lambda: os.getenv(
            "GROQ_WHISPER_MODEL", "whisper-large-v3-turbo"
        )
    )
    groq_temperature: float = field(
        default_factory=lambda: float(os.getenv("GROQ_TEMPERATURE", "0.7"))
    )
    groq_max_tokens: int = field(
        default_factory=lambda: int(os.getenv("GROQ_MAX_TOKENS", "4096"))
    )

    # ---- ElevenLabs TTS (voz principal) ----
    elevenlabs_api_key: str = field(
        default_factory=lambda: os.getenv("ELEVENLABS_API_KEY", "")
    )
    elevenlabs_voice_id: str = field(
        default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", "")
    )
    elevenlabs_model: str = field(
        default_factory=lambda: os.getenv(
            "ELEVENLABS_MODEL", "eleven_multilingual_v2"
        )
    )

    # ---- Microsoft Edge TTS (voz fallback) ----
    edge_tts_voice: str = field(
        default_factory=lambda: os.getenv("EDGE_TTS_VOICE", "pt-BR-FranciscaNeural")
    )
    tts_output_file: str = field(
        default_factory=lambda: os.getenv("TTS_OUTPUT_FILE", "vocal_.mp3")
    )

    # ---- Audio / Microfone ----
    audio_sample_rate: int = 16000
    audio_chunk_size: int = 512
    audio_format: int = 8  # pyaudio.paInt16
    audio_channels: int = 1
    silero_vad_threshold: float = 0.75
    silence_frames_threshold: int = 35

    # ---- Discord ----
    discord_token: str = field(
        default_factory=lambda: os.getenv("DISCORD_TOKEN", "")
    )
    discord_prefix: str = field(
        default_factory=lambda: os.getenv("DISCORD_PREFIX", "!")
    )

    # ---- VTuber Overlay ----
    vtuber_emotion_url: str = field(
        default_factory=lambda: os.getenv(
            "VTUBER_EMOTION_URL", "http://127.0.0.1:8765/emotion"
        )
    )
    vtuber_overlay_script: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
        / "Net"
        / "vtuber_overlay.py"
    )

    # ---- ChromaDB / Memoria Vetorial ----
    chroma_persist_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent
        / "Memoria_Vectorial"
    )
    chroma_collection_name: str = field(
        default_factory=lambda: os.getenv("CHROMA_COLLECTION", "memoria_rem")
    )

    # ---- Audio Calls ----
    audio_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent
        / "discord_call_audio"
    )

    # ---- GUI ----
    gui_title: str = field(
        default_factory=lambda: os.getenv("GUI_TITLE", "Shogun - Arcana Rem")
    )
    gui_geometry: str = field(
        default_factory=lambda: os.getenv("GUI_GEOMETRY", "800x600")
    )

    # ---- Logging ----
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )

    # ---- Cache ----
    cache_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "#cache"
    )

    # ---- Screenshot / Visao ----
    screenshot_max_size: tuple[int, int] = (1024, 1024)
    screenshot_quality: int = 70
    screenshot_format: str = "JPEG"

    def __post_init__(self):
        """Garante que diretorios essenciais existam."""
        for dir_path in (self.armazen_dir, self.cache_dir, self.audio_dir):
            dir_path.mkdir(parents=True, exist_ok=True)

    @property
    def has_elevenlabs(self) -> bool:
        """Verifica se as credenciais ElevenLabs estao configuradas."""
        return bool(self.elevenlabs_api_key and self.elevenlabs_voice_id)

    @property
    def has_groq(self) -> bool:
        """Verifica se as credenciais Groq estao configuradas."""
        return bool(self.groq_api_key_llm and self.groq_api_key_vision)

    @property
    def persona_text(self) -> str:
        """Le o arquivo de persona sob demanda."""
        if self.persona_file.exists():
            return self.persona_file.read_text(encoding="utf-8")
        return ""


# Singleton global
_config_instance: Optional[ShogunConfig] = None


def get_config() -> ShogunConfig:
    """Retorna a instancia unica de config (singleton)."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ShogunConfig()
    return _config_instance


def reset_config() -> None:
    """Reseta o singleton de config (util para testes)."""
    global _config_instance
    _config_instance = None
