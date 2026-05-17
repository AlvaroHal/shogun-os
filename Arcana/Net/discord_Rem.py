# Arcana/Net/discord_Rem.py
import discord
from discord.ext import commands
import asyncio
import os
import re
import json
import yt_dlp
import time
import requests
import wave
import logging
import base64
import pyautogui
import traceback
from io import BytesIO
from types import SimpleNamespace
from collections import defaultdict
from typing import Optional, Dict, Any

# ─── Core Global Services ─────────────────────
from Arcana.Core.config import get_config
from Arcana.Core.event_bus import EventBus
from Arcana.Core.llm_client import LLMClient
from Arcana.Net.memory_Rem import ShogunMemoria
from Arcana.Net.os_Rem import AsyncOSAutomation
from Arcana.Net.search_ddg import pesquisar_web

try:
    from discord.ext import voice_recv
except ImportError:
    voice_recv = None

def localizar_brain_path():
    return str(get_config().brain_file)

# ======================================================
# 🤫 SILENCIADOR DE SPAM DO TERMINAL
# ======================================================
logging.getLogger('discord.ext.voice_recv.reader').setLevel(logging.WARNING)
logging.getLogger('discord.ext.voice_recv.gateway').setLevel(logging.WARNING)
logging.getLogger('discord.ext.voice_recv.router').setLevel(logging.WARNING)

# ======================================================
# 💉 MONKEY PATCH DE SEGURANÇA E DEBUG DE ÁUDIO (COM P.L.C.)
# ======================================================
import discord.opus
PACOTES_BONS = 0
PACOTES_PERDIDOS = 0
LAST_PCM = b'\x00' * 3840  # Inicia com silêncio suave

if hasattr(discord.opus, "Decoder"):
    _original_opus_decode = discord.opus.Decoder.decode
    def _safe_opus_decode(self, data, *args, **kwargs):
        global PACOTES_BONS, PACOTES_PERDIDOS, LAST_PCM
        
        # Se for um pacote de silêncio/pausa do Discord (DTX), injeta silêncio sem contar como erro
        if len(data) <= 3:
            return b'\x00' * 3840
            
        try:
            res = _original_opus_decode(self, data, *args, **kwargs)
            PACOTES_BONS += 1
            LAST_PCM = res  # Salva a última lasca de som válido
            return res
        except discord.opus.OpusError as e:
            PACOTES_PERDIDOS += 1
            # PLC (Packet Loss Concealment): Repete a última lasca de voz!
            # Impede o áudio de estalar e ajuda o Whisper a ler a palavra inteira.
            return LAST_PCM
            
    discord.opus.Decoder.decode = _safe_opus_decode

# ======================================================
# 🔥 A OPÇÃO NUCLEAR V3: TRADUTOR E CONTROLE DE STOP 🔥
# ======================================================
_original_chat_class = LLMClient.chat

async def _universal_smart_chat(self, *args, **kwargs):
    try:
        prompt_texto = ""
        sys_texto = get_config().persona_text
        model_usado = kwargs.get("model", get_config().groq_model_main)

        if "messages" in kwargs:
            for msg in kwargs["messages"]:
                if msg.get("role") == "system": sys_texto = msg.get("content", sys_texto)
                elif msg.get("role") == "user": prompt_texto = msg.get("content", "")
        else:
            if "prompt" in kwargs: prompt_texto = kwargs["prompt"]
            elif len(args) > 0 and isinstance(args[0], str): prompt_texto = args[0]
            
            if "system_prompt" in kwargs: sys_texto = kwargs["system_prompt"]
            elif len(args) > 1 and isinstance(args[1], str): sys_texto = args[1]

        prompt_lower = str(prompt_texto).lower() if prompt_texto else ""

        # 👁️ VISÃO COMPUTACIONAL (Mantida aqui pois depende da chamada direta de IA)
        brain_path = localizar_brain_path()
        visao_ativa = False
        if os.path.exists(brain_path):
            try:
                with open(brain_path, "r", encoding="utf-8") as f:
                    visao_ativa = json.load(f).get("visao_computacional_ativa", False)
            except: pass

        if visao_ativa and any(w in prompt_lower for w in ["tela", "vendo", "ver", "screen", "screenshot", "enxergando", "mostrando"]):
            print("👁️ [OPÇÃO NUCLEAR] Capturando tela física do PC para Groq Vision...")
            try:
                screenshot = pyautogui.screenshot().resize((1024, 1024))
                buffered = BytesIO()
                screenshot.save(buffered, format="JPEG", quality=70)
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                sys_p = get_config().persona_text + "\n[SISTEMA]: Você recebeu visão real da tela do PC do usuário. Descreva o que está vendo de forma curta e cínica."
                vision_messages = [
                    {"role": "system", "content": sys_p},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt_texto},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                    ]}
                ]
                return await _original_chat_class(self, messages=vision_messages, model=get_config().groq_model_vision)
            except Exception as vis_err:
                print(f"❌ Erro no Groq Vision: {vis_err}")

        # 🎵 RADAR DE MÚSICA INTELIGENTE
        palavras_status = ["cadê", "cade", "não colocou", "porque", "por que", "onde tá", "onde ta", "parou"]
        reclamou_da_musica = any(sw in prompt_lower for sw in palavras_status)
        palavras_parar = ["para a", "parar", "para essa", "pausa", "pausar", "stop", "cala a boca", "desliga", "tira a", "chega de"]
        pediu_parar = any(sw in prompt_lower for sw in palavras_parar)
        gatilhos_musica = ["musica", "música", "toca", "tocar", "play", "som", "canção", "bota", "botar", "coloca", "colocar", "põe", "poe"]
        pediu_musica = any(w in prompt_lower for w in gatilhos_musica) and not reclamou_da_musica and not pediu_parar

        if pediu_parar:
            sys_texto += "\n\n[MANDATO ADICIONAL]: O mestre mandou parar a música. Confirme de forma sarcástica e encerre OBRIGATORIAMENTE a resposta com a tag exata: <MUSICA: STOP>"
        elif pediu_musica:
            sys_texto += "\n\n[MANDATO ADICIONAL]: O mestre pediu música. Escolha uma legal e encerre OBRIGATORIAMENTE a resposta com a tag exata: <MUSICA: Nome da Música - Artista>"

        # 🎭 INJEÇÃO DE EMOÇÃO PARA O VTUBER
        sys_texto += "\n\n[EXPRESSÃO FACIAL]: Você DEVE expressar seu humor incluindo UMA destas tags no meio da sua fala: [NORMAL], [RIR], [RAIVA], [TRISTE] ou [SURPRESA]."

        # CHAMADA OFICIAL GROQ
        mensagens_formatadas = [
            {"role": "system", "content": sys_texto},
            {"role": "user", "content": prompt_texto}
        ]
        resposta_ia = await _original_chat_class(self, messages=mensagens_formatadas, model=model_usado)

        if not resposta_ia:
            return resposta_ia

        # 🎵 FORÇA BRUTA DE ÁUDIO MUSICAL (Injeta as tags se a IA esquecer)
        if pediu_parar and not any(tag in resposta_ia.upper() for tag in ["<MUSICA: STOP>", "[PLAY: STOP]", "<PLAY: STOP>"]):
            resposta_ia += " <MUSICA: STOP>"
            print("🎵 [OPÇÃO NUCLEAR] Tag de STOP injetada na marra.")
        elif pediu_musica and "<MUSICA:" not in resposta_ia and "[PLAY:" not in resposta_ia:
            nome_musica = "Darude - Sandstorm"
            match = re.search(r'(?:toca|coloca|põe|poe|botar|ouvir)\s+(?:a|o)?\s*([^,.\n?]+)', prompt_lower)
            if match:
                ext = match.group(1).strip()
                for limpar in ["música", "musica", "shogun", "pra", "nós", "aí", "ai", "uma", "um", "hein"]:
                    ext = ext.replace(limpar, "").strip()
                if len(ext) > 2: nome_musica = ext.capitalize()
            
            resposta_ia += f" <MUSICA: {nome_musica}> [PLAY: {nome_musica}]"

        # 🔀 A MÁGICA DA ARQUITETURA LIMPA: O ROTEADOR ENTRA EM AÇÃO
        from Arcana.Core.action_router import ActionRouter
        # O Router vai executar a emoção, abrir programas e devolver o texto limpo sem tags de código
        texto_limpo = ActionRouter.process_actions(resposta_ia, prompt_lower)

        # 🔊 GERAÇÃO DA VOZ COM O TEXTO LIMPO
        if texto_limpo:
            try:
                output_file = str(get_config().tts_output_file)
                if get_config().has_elevenlabs:
                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{get_config().elevenlabs_voice_id}"
                    headers = {"xi-api-key": get_config().elevenlabs_api_key, "Content-Type": "application/json"}
                    payload = {"text": texto_limpo, "model_id": get_config().elevenlabs_model, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
                    resp = requests.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        with open(output_file, "wb") as f: f.write(resp.content)
                else:
                    import edge_tts
                    communicate = edge_tts.Communicate(texto_limpo, get_config().edge_tts_voice)
                    await communicate.save(output_file)
            except Exception as e_tts: 
                print(f"❌ [TTS] Erro: {e_tts}")

        # Retorna a resposta_ia completa (com as tags) para a função do Discord processar a Música
        return resposta_ia

    except Exception as erro_nuclear:
        print(f"❌ [OPÇÃO NUCLEAR] Erro fatal no interceptador: {erro_nuclear}")
        return "Deu erro no núcleo da IA."

LLMClient.chat = _universal_smart_chat

original_transcribe = LLMClient.transcribe
async def smart_transcribe(self, *args, **kwargs):
    audio_path = kwargs.get("audio_path")
    if audio_path:
        model = kwargs.get("model") or get_config().groq_whisper_model
        language = kwargs.get("language") or "pt"
        def _call():
            with open(audio_path, "rb") as f: file_bytes = f.read()
            headers = {"Authorization": f"Bearer {self.api_key_llm}"}
            files = {"file": ("input.wav", file_bytes, "audio/wav"), "model": (None, model), "language": (None, language)}
            resp = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files)
            if resp.status_code == 200: return resp.json().get("text", "")
            raise RuntimeError(f"Whisper error: {resp.status_code}")
        return await self._retry(_call)
    return await original_transcribe(self, *args, **kwargs)

LLMClient.transcribe = smart_transcribe

# ======================================================
# 🎨 MÓDULO DE GERAÇÃO DE ARTE
# ======================================================
class ShogunArtModule:
    def __init__(self, base_path="D:/Shogun/Imagens"):
        self.base_path = base_path
        if not os.path.exists(self.base_path): os.makedirs(self.base_path)

    def gerar_e_salvar(self, prompt):
        url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1024&height=1024&nologo=true"
        try:
            res = requests.get(url)
            if res.status_code == 200:
                pth = os.path.join(self.base_path, f"shogun_art_{time.strftime('%Y%m%d-%H%M%S')}.png")
                with open(pth, "wb") as f: f.write(res.content)
                return pth
        except: pass
        return None

shogun_artista = ShogunArtModule()

# ======================================================
# 🌐 CONFIGURAÇÃO DO BOT E GATILHOS DIRETOS
# ======================================================
async def setup_discord_bot(llm_client: LLMClient, memoria: ShogunMemoria, os_automation: AsyncOSAutomation, event_bus: EventBus):
    config = get_config()
    TOKEN = config.discord_token
    
    if not TOKEN: 
        print("❌ ERRO CRÍTICO: DISCORD_TOKEN não encontrado!")
        return

    nome_ai = config.gui_title.split(" - ")[0]
    usuario_nome = "MestreRimuru"
    sys_prompt = config.persona_text
    launcher = None
    client_vision = llm_client
    client_llm = llm_client

    async def processar_ia_func(*args, **kwargs):
        p = args[3] if len(args) > 3 else kwargs.get('conteudo', '')
        s = args[2] if len(args) > 2 else config.persona_text
        return await llm_client.chat(prompt=p, system_prompt=s)

    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix=config.discord_prefix, intents=intents)
    url_musica_ativa, tempo_inicio_musica, segundos_decorridos = None, 0, 0
    ia_falando_na_call = False
    call_processing_lock = asyncio.Lock()
    audio_call_dir = os.path.abspath("discord_call_audio")
    os.makedirs(audio_call_dir, exist_ok=True)

    def limpar_tags_internas(texto):
        if not texto:
            return ""
        texto = re.sub(r"\[\s*(NORMAL|RIR|RAIVA|TRISTE|SURPRESA)\s*\]", "", texto, flags=re.IGNORECASE)
        texto = re.sub(r"\[\s*(PLAY|MUSICA)\s*:[^\]]+\]", "", texto, flags=re.IGNORECASE)
        texto = re.sub(r"<[^>]+>", "", texto)
        texto = re.sub(r",\s*([.!?])", r"\1", texto)
        texto = re.sub(r"\s+([.,!?;:])", r"\1", texto)
        texto = re.sub(r"\s{2,}", " ", texto)
        texto = re.sub(r",\s*,", ",", texto)
        return texto.strip()

    def carregar_brain_data():
        brain_path = localizar_brain_path()
        try:
            if brain_path and os.path.exists(brain_path):
                with open(brain_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ [BRAIN] Erro ao ler brain.json: {e}")
        return {}

    def salvar_brain_data(data):
        brain_path = localizar_brain_path()
        try:
            if brain_path:
                with open(brain_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                return True
        except Exception as e:
            print(f"⚠️ [BRAIN] Erro ao salvar brain.json: {e}")
        return False

    def _bool_brain(data, chave, padrao=False):
        valor = data.get(chave, padrao)
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, str):
            return valor.strip().lower() in {"true", "1", "sim", "yes", "on", "ligado"}
        return bool(valor)

    def carregar_config_discord():
        data = carregar_brain_data()
        return {
            "raw": data,
            "active": _bool_brain(data, "discord_active", True),
            "server_active": _bool_brain(data, "discord_server_active", False),
            "mentions": _bool_brain(data, "discord_mentions", True),
            "target_user_active": _bool_brain(data, "discord_target_user_active", False),
            "target_user_name": str(data.get("discord_target_user_name", "")).lower().strip(),
            "dm_active": _bool_brain(data, "discord_dm_active", False),
            "dm_dono_always": _bool_brain(data, "discord_dm_dono_always", False),
            "disabled_guilds": {str(g) for g in data.get("discord_disabled_guilds", [])},
        }

    def autor_bate_foco(message, alvo_foco):
        if not alvo_foco:
            return False
        autor_nome = message.author.name.lower()
        autor_nick = message.author.display_name.lower() if message.author.display_name else ""
        return alvo_foco in autor_nome or alvo_foco in autor_nick

    def servidor_bloqueado(message, cfg):
        if not getattr(message, "guild", None):
            return False
        guild_id = str(message.guild.id)
        guild_name = str(message.guild.name)
        return guild_id in cfg["disabled_guilds"] or guild_name in cfg["disabled_guilds"]

    def deve_responder_mensagem(message, cfg):
        if not cfg["active"]:
            return False, "discord_desligado"

        if servidor_bloqueado(message, cfg):
            return False, "servidor_bloqueado"

        alvo_ok = autor_bate_foco(message, cfg["target_user_name"])

        if isinstance(message.channel, discord.DMChannel):
            if cfg["dm_active"]:
                return True, "dm_livre"
            if cfg["dm_dono_always"] and alvo_ok:
                return True, "dm_usuario_foco"
            return False, "dm_bloqueada"

        foi_mencionada = (
            bot.user.mentioned_in(message)
            or (nome_ai.lower() in message.content.lower())
        )

        if cfg["mentions"] and foi_mencionada:
            return True, "mencao"

        if cfg["server_active"]:
            return True, "responder_livremente"

        if cfg["target_user_active"] and alvo_ok:
            return True, "usuario_foco"

        return False, "sem_regra_ativa"

    # ======================================================
    # 🎤 TOCAR VOZ DA IA NA CALL
    # ======================================================
    async def tocar_audio_na_call(message=None, deve_retomar=True):
        nonlocal url_musica_ativa
        nonlocal tempo_inicio_musica
        nonlocal segundos_decorridos
        nonlocal ia_falando_na_call

        arquivo_audio = os.path.abspath("vocal_.mp3")

        await asyncio.sleep(0.5)

        vc = None
        if message and hasattr(message, "guild") and message.guild:
            vc = message.guild.voice_client

        if not vc and bot.voice_clients:
            vc = bot.voice_clients[0]

        if not vc or not vc.is_connected():
            return

        if not os.path.exists(arquivo_audio):
            return

        if vc.is_playing() and tempo_inicio_musica > 0:
            segundos_decorridos += time.time() - tempo_inicio_musica
            vc.stop()
            await asyncio.sleep(0.5)

        try:
            ia_falando_na_call = True

            ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
            source = discord.FFmpegPCMAudio(
                arquivo_audio,
                executable=ffmpeg_path
            )

            vc.play(source)
            print("🎤 [VOZ] Shogun falando na call...")

            while vc.is_playing():
                await asyncio.sleep(0.5)

            if deve_retomar and url_musica_ativa and vc.is_connected():
                print(f"⏩ [RETOMADA] Voltando rádio ({int(segundos_decorridos)}s)...")
                await tocar_youtube(vc, url_musica_ativa, seek=int(segundos_decorridos))

        except Exception as e:
            print(f"❌ Erro na voz: {e}")
            
        finally:
            # 🔥 A LEI ABSOLUTA: Destrava os ouvidos dela aconteça o que acontecer!
            ia_falando_na_call = False

    # ======================================================
    # 🎶 TOCAR YOUTUBE / CONTROLE DE RÁDIO
    # ======================================================
    async def tocar_youtube(vc, termo_ou_url, seek=0):
        nonlocal url_musica_ativa
        nonlocal tempo_inicio_musica
        nonlocal segundos_decorridos

        comando = termo_ou_url.upper().strip()
        comando_limpo = re.sub(r"[^A-Z]", "", comando)

        if comando_limpo in ["PAUSE", "PAUSAR"]:
            if vc.is_playing(): vc.pause()
            return
        elif comando_limpo in ["RESUME", "VOLTAR", "RETOMAR"]:
            if vc.is_paused(): vc.resume()
            return
        elif comando_limpo in ["STOP", "PARAR", "CALABOCA"]:
            if vc.is_playing() or vc.is_paused(): vc.stop()
            url_musica_ativa = None
            print("⏹️ [COMANDO] Rádio desligada e apagada da memória.")
            return

        if not termo_ou_url.startswith("http"):
            query = f"ytsearch1:{termo_ou_url}"
            print(f"🔍 [DJ] Pesquisando no YT: {termo_ou_url}")
        else:
            query = termo_ou_url.replace("music.youtube.com", "www.youtube.com")
            url_musica_ativa = query

        tempo_formatado = time.strftime("%H:%M:%S", time.gmtime(seek))
        caminho_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        caminho_cookies = os.path.join(caminho_base, "cookies.txt")

        YTDL_OPTIONS = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "cookiefile": caminho_cookies if os.path.exists(caminho_cookies) else None,
            "nocheckcertificate": True,
        }

        FFMPEG_OPTIONS = {
            "before_options": f"-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {tempo_formatado}",
            "options": "-vn",
        }

        try:
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                info = await bot.loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
                if "entries" in info: info = info["entries"][0]
                stream_url = info.get("url")

            if not stream_url:
                print("❌ [DJ] Não foi possível obter a URL de stream.")
                return

            ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
            source = discord.FFmpegPCMAudio(stream_url, executable=ffmpeg_path, **FFMPEG_OPTIONS)

            if vc.is_playing(): vc.stop()
            vc.play(source)

            tempo_inicio_musica = time.time()
            if seek == 0: segundos_decorridos = 0
            url_musica_ativa = f"https://www.youtube.com/watch?v={info['id']}"

            print(f"🎶 [RADIO] Tocando agora: {info.get('title')}")
        except Exception as e:
            print(f"❌ Erro YT: {e}")

    # ======================================================
    # 📡 RADAR DE MÚSICA EM SEGUNDO PLANO
    # ======================================================
    async def loop_verificador_musica():
        nonlocal segundos_decorridos

        async def on_music_control(data: Dict[str, Any]):
            nonlocal segundos_decorridos
            if not bot.voice_clients: return
            vc = bot.voice_clients[0]
            if not vc or not vc.is_connected(): return

            action = data.get("action", "")
            payload = data.get("payload", "")

            if action == "play":
                segundos_decorridos = 0
                await tocar_youtube(vc, payload)
            elif action in ["pause", "stop", "resume"]:
                await tocar_youtube(vc, action)

        event_bus.subscribe("music_control", on_music_control)

        while True:
            await asyncio.sleep(1.0)
            try:
                if not bot.voice_clients: continue
                vc = bot.voice_clients[0]
                if vc and vc.is_connected():
                    brain_data = carregar_brain_data()
                    pending = brain_data.get("pending_music", "")
                    if pending:
                        brain_data["pending_music"] = ""
                        salvar_brain_data(brain_data)
                        tag_limpa = re.sub(r"[<>]", "", pending).strip()
                        if tag_limpa.upper().startswith("PLAY:"):
                            musica_url = tag_limpa[5:].strip()
                            segundos_decorridos = 0
                            await tocar_youtube(vc, musica_url)
                        else:
                            comando = tag_limpa.upper()
                            if comando in ["PAUSE", "STOP", "RESUME", "PARAR", "VOLTAR"]:
                                await tocar_youtube(vc, comando)
            except: pass

    # ======================================================
    # 🎧 TRANSCRIÇÃO DA CALL E 🧠 PROCESSAMENTO
    # ======================================================
    async def transcrever_audio_call(caminho_wav):
        if not os.path.exists(caminho_wav):
            print(f"❌ [STT] Arquivo WAV não encontrado: {caminho_wav}")
            return ""

        try:
            resultado = await llm_client.transcribe(
                audio_path=caminho_wav,
                model=os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo"),
                language="pt",
            )

            if isinstance(resultado, str):
                return resultado.strip()

            return getattr(resultado, "text", "").strip()

        except Exception as e:
            print(f"❌ [STT] Erro ao transcrever áudio da call: {e}")
            return ""

    async def processar_fala_da_call(member, caminho_wav):
        nonlocal ia_falando_na_call

        try:
            if not member:
                return

            if member.bot:
                return

            if ia_falando_na_call:
                print("⚠️ [CALL] IA estava falando. Áudio recebido foi ignorado.")
                return

            async with call_processing_lock:
                if ia_falando_na_call:
                    return
                texto = await transcrever_audio_call(caminho_wav)
                if not texto or len(texto.strip()) < 2:
                    return

                texto_limpo = texto.strip().lower()
                if re.search(r'[\u2e80-\u9fff\uac00-\ud7af\u3130-\u318f\u0400-\u04FF]', texto_limpo) or "coward" in texto_limpo or "inc tage" in texto_limpo:
                    print(f"👻 [CALL] Alucinação de idioma ignorada: '{texto}'")
                    return
                
                texto_normalizado = re.sub(r"[^\w\sà-ÿ]", "", texto_limpo)
                texto_normalizado = re.sub(r"\s+", " ", texto_normalizado).strip()

                alucinacoes_exatas = {
                    "e aí",
                    "e ai",
                    "oi",
                    "olá",
                    "ola",
                    "tchau",
                    "tchau tchau",
                    "pronto",
                    "obrigado",
                    "obrigada",
                    "alo",
                    "alô",
                    "aham",
                    "uhum",
                }
                alucinacoes_parciais = [
                    "legendas",
                    "legendado",
                    "sônia ruberti",
                    "sonia ruberti",
                    "inscreva-se",
                    "amara.org",
                    "obrigado por assistir",
                    "o usuário está",
                    "falando em português",
                    "villas",
                    "mtv",
                ]

                if (
                    texto_normalizado in alucinacoes_exatas
                    or any(fantasma in texto_limpo for fantasma in alucinacoes_parciais)
                ):
                    print(f"👻 [CALL] Alucinação de ruído ignorada: '{texto}'")
                    return

                nome_pessoa = member.display_name or member.name
                print(f"🎧 [CALL] {nome_pessoa} disse: {texto}")

                entrada_ia = f"{nome_pessoa} falou com você na call do Discord:\n{texto}\n\nResponda diretamente para {nome_pessoa}, de forma curta."
                resposta = await processar_ia_func(client_llm, client_vision, sys_prompt, entrada_ia, nome_ai, usuario_nome, launcher, modo_chat=True)

                if resposta:
                    match_musica = re.search(r'<(?:MUSICA|PLAY):\s*([^>]+)>', resposta, re.IGNORECASE)
                    if not match_musica: match_musica = re.search(r'\[(?:MUSICA|PLAY):\s*([^\]]+)\]', resposta, re.IGNORECASE)

                    resposta_limpa = limpar_tags_internas(resposta)
                    print(f"🤖 [CALL] Shogun respondeu: {resposta_limpa}")

                    fake_message = SimpleNamespace(guild=member.guild)

                    if match_musica:
                        nome_musica = match_musica.group(1).strip()
                        is_stop = "STOP" in nome_musica.upper()
                        
                        vc = member.guild.voice_client if member.guild else None
                        if not vc and bot.voice_clients: vc = bot.voice_clients[0]
                        if vc and vc.is_connected():
                            await tocar_audio_na_call(fake_message, deve_retomar=not is_stop)
                            if not is_stop:
                                bot.loop.create_task(tocar_youtube(vc, nome_musica))
                            else:
                                bot.loop.create_task(tocar_youtube(vc, "STOP")) # 🔥 Apaga a música da memória
                    else:
                        await tocar_audio_na_call(fake_message, deve_retomar=True)
                
        except Exception as e:
            print(f"❌ [CALL] Erro: {e}")
        finally:
            try:
                if os.path.exists(caminho_wav):
                    os.remove(caminho_wav)
            except Exception as cleanup_error:
                print(f"⚠️ [CALL] Falha ao limpar cache de áudio temporário: {cleanup_error}")

    # ======================================================
    # 🎙️ SINK DE ÁUDIO DA CALL
    # ======================================================
    ShogunCallSink = None
    if voice_recv is not None:
        class ShogunCallSink(voice_recv.AudioSink):
            def __init__(self, loop):
                super().__init__()
                self.loop = loop
                self.buffers = defaultdict(bytearray)
                self.flush_tasks = {}
                self.packet_quality = defaultdict(lambda: {"good": 0, "bad": 0})

            def wants_opus(self): return False

            def write(self, user, data):
                try:
                    if user is None:
                        return

                    if getattr(user, "bot", False):
                        return

                    if ia_falando_na_call:
                        return

                    pcm = getattr(data, "pcm", None)

                    if pcm:
                        self.buffers[user.id].extend(pcm)

                except Exception:
                    pass

            @voice_recv.AudioSink.listener()
            def on_voice_member_speaking_start(self, member):
                try:
                    if member is None:
                        return

                    if member.bot:
                        return

                    task = self.flush_tasks.get(member.id)

                    if task:
                        self.loop.call_soon_threadsafe(task.cancel)
                        del self.flush_tasks[member.id]
                    else:
                        print(f"🎙️ [CALL] {member.display_name} começou a falar...")

                except Exception as e:
                    print(f"❌ [SINK] Erro no speaking_start: {e}")

            @voice_recv.AudioSink.listener()
            def on_voice_member_speaking_stop(self, member):
                global PACOTES_BONS, PACOTES_PERDIDOS
                if not member or member.bot: return
                print(f"📊 [DEBUG ÁUDIO] {member.display_name} - Pacotes Limpos: {PACOTES_BONS} | Corrompidos: {PACOTES_PERDIDOS}")
                self.packet_quality[member.id]["good"] += PACOTES_BONS
                self.packet_quality[member.id]["bad"] += PACOTES_PERDIDOS
                PACOTES_BONS, PACOTES_PERDIDOS = 0, 0
                self.flush_tasks[member.id] = asyncio.run_coroutine_threadsafe(
                    self._delayed_flush(member),
                    self.loop,
                )

            async def _delayed_flush(self, member):
                try: 
                    await asyncio.sleep(1.5)
                except asyncio.CancelledError: 
                    return
                
                if member.id in self.flush_tasks: 
                    del self.flush_tasks[member.id]

                # Pega os bytes que acumulamos enquanto você falava
                audio_bytes = self.buffers.pop(member.id, bytearray())
                
                # Se tiver menos de 0.5s de áudio, ignoramos para não gastar API
                if len(audio_bytes) < 40000: 
                    return

                # Salva o arquivo sem perguntar se está corrompido ou não
                timestamp = time.time()
                caminho_wav = os.path.join(audio_call_dir, f"{member.id}_{timestamp}.wav")
                
                with wave.open(caminho_wav, "wb") as wav_file:
                    wav_file.setnchannels(2)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(48000)
                    wav_file.writeframes(audio_bytes)
                
                print(f"✅ [CALL] Áudio empacotado (forçando processamento): {caminho_wav}")
                
                # Envia direto para a IA processar, sem filtro de qualidade
                self.loop.create_task(processar_fala_da_call(member, caminho_wav))
                    return
                if total_packets >= 20 and bad_ratio >= 0.35:
                    print(
                        f"[CALL] Audio com perda alta, tentando transcrever mesmo assim "
                        f"({quality['bad']}/{total_packets}, {bad_ratio:.0%})."
                    )

                caminho_wav = os.path.join(audio_call_dir, f"{member.id}_{time.strftime('%Y%m%d-%H%M%S')}.wav")
                with wave.open(caminho_wav, "wb") as wav_file:
                    wav_file.setnchannels(2)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(48000)
                    wav_file.writeframes(audio_bytes)
                
                print(f"✅ [CALL] Áudio empacotado: {caminho_wav}")
                self.loop.create_task(processar_fala_da_call(member, caminho_wav))

            def cleanup(self):
                self.buffers.clear()
                for task in self.flush_tasks.values():
                    self.loop.call_soon_threadsafe(task.cancel)
                self.flush_tasks.clear()
                self.packet_quality.clear()

    # ======================================================
    # ✅ BOT ONLINE E COMANDOS
    # ======================================================
    @bot.event
    async def on_ready():
        brain_data = carregar_brain_data()
        brain_data["discord_guilds_cache"] = [
            {"id": str(guild.id), "name": guild.name}
            for guild in bot.guilds
        ]
        salvar_brain_data(brain_data)

        print("\n✅ [SISTEMA] Shogun Rádio v2.9 (Cura da Surdez e Parede de Ferro) Conectada!")

        if voice_recv is None:
            print("⚠️ [CALL] discord-ext-voice-recv não instalado. Escuta da call indisponível.")
        else:
            print("✅ [CALL] Módulo de escuta por voz carregado.")

        bot.loop.create_task(loop_verificador_musica())

    # ======================================================
    # 💬 MENSAGENS DO DISCORD
    # ======================================================
    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return

        if config.discord_prefix and message.content.strip().startswith(config.discord_prefix):
            await bot.process_commands(message)
            return
        
        texto_msg = message.content.lower()
        discord_cfg = carregar_config_discord()

        if not discord_cfg["active"] or servidor_bloqueado(message, discord_cfg):
            await bot.process_commands(message)
            return

        # ==================================================
        # 🎨 ARTE POR TEXTO
        # ==================================================
        if (
            texto_msg.startswith("shogun gera")
            or texto_msg.startswith("shogun desenha")
            or texto_msg.startswith("shogun cria")
        ):
            prompt_pt = re.sub(
                r"^shogun (gera|desenha|cria)\s+",
                "",
                texto_msg
            ).strip()

            if prompt_pt:
                aviso = await message.channel.send(
                    f"🎨 Segura a ansiedade aí. Traduzindo do seu neandertalês e desenhando: **{prompt_pt}**..."
                )

                try:
                    prompt_en = await llm_client.chat_fast(
                        [
                            {
                                "role": "system",
                                "content": (
                                    "You translate Portuguese image generation prompts into English keywords. "
                                    "ONLY output the English text, no explanations, no quotes."
                                ),
                            },
                            {"role": "user", "content": prompt_pt},
                        ],
                        temperature=0.3,
                    )

                except Exception as e:
                    print(f"⚠️ [ARTE] Erro ao traduzir prompt. Usando original: {e}")
                    prompt_en = prompt_pt

                caminho_imagem = await asyncio.to_thread(
                    shogun_artista.gerar_e_salvar,
                    prompt_en
                )

                if caminho_imagem:
                    arquivo = discord.File(caminho_imagem)
                    await message.channel.send(
                        content="🖼️ Tá aí. Apreciem a minha arte e não reclamem:",
                        file=arquivo
                    )
                    try:
                        await aviso.delete()
                    except Exception:
                        pass
                else:
                    await aviso.edit(
                        content="❌ Deu ruim. Alguém bebeu a água do meu pincel."
                    )
            else:
                await message.channel.send(
                    "Gerar o quê? Esqueceu de falar, cérebro de Cheetos?"
                )
            return

        # ==================================================
        # 🧠 CHAT NORMAL DA IA NO DISCORD
        # ==================================================
        deve_responder, motivo_resposta = deve_responder_mensagem(message, discord_cfg)
        if not deve_responder:
            await bot.process_commands(message)
            return

        conteudo = re.sub(r"<@&?\d+>", "", message.content).strip()
        print(f"[DISCORD GATE] Respondendo por: {motivo_resposta}")

        async with message.channel.typing():
            try:
                resposta = await processar_ia_func(
                    client_llm,
                    client_vision,
                    sys_prompt,
                    conteudo,
                    nome_ai,
                    usuario_nome,
                    launcher,
                    modo_chat=True
                )

                if resposta:
                    print(f" DEBUG RAW: {resposta}")
                    resposta_limpa = limpar_tags_internas(resposta)
                    print(f"[DISCORD CLEAN] {resposta_limpa}")
                    await message.reply(resposta_limpa)

                    vc = message.guild.voice_client if message.guild else None

                    if vc and vc.is_connected():
                        await tocar_audio_na_call(
                            message,
                            deve_retomar=True
                        )

            except Exception as e:
                print(f"Erro no chat Discord: {e}")

        await bot.process_commands(message)
        return

    # ======================================================
    # 📞 COMANDO VEM (COM DEGRADAÇÃO GRACIOSA ANTI-4017)
    # ======================================================
    @bot.command()
    async def vem(ctx):
        if voice_recv is None:
            return await ctx.send(
                "❌ Falta instalar o módulo de escuta de voz.\n"
                "Use: `pip install -U discord-ext-voice-recv`"
            )

        if not ctx.author.voice:
            return await ctx.send("Entra na call, orelha seca.")

        # 🧠 LIMPEZA DE MEMÓRIA (Buffer Musical)
        try:
            brain_path = localizar_brain_path()

            if brain_path:
                with open(brain_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if data.get("pending_music", ""):
                    data["pending_music"] = ""

                    with open(brain_path, "w", encoding="utf-8") as f_out:
                        json.dump(data, f_out, indent=4, ensure_ascii=False)

                    print("🧹 [SISTEMA] Música fantasma apagada da memória antes de entrar na call.")

        except Exception as e:
            print(f"⚠️ [BRAIN] Erro ao limpar pending_music: {e}")

        canal = ctx.author.voice.channel

        # PREVENÇÃO: Se houver conexão travada, mata antes de reconectar
        if ctx.voice_client:
            try:
                await ctx.voice_client.disconnect(force=True)
                await asyncio.sleep(1.0)
            except Exception as e:
                print(f"⚠️ [CALL] Erro ao desconectar conexão anterior: {e}")

        try:
            # TENTATIVA 1: Módulo de Ouvidos (VoiceRecvClient)
            vc = await canal.connect(
                cls=voice_recv.VoiceRecvClient,
                timeout=60.0,
                reconnect=True,
                self_deaf=False,
                self_mute=False
            )

            if hasattr(vc, "is_listening") and vc.is_listening():
                vc.stop_listening()

            sink = ShogunCallSink(bot.loop)
            vc.listen(sink)

            await ctx.send(
                "🎧 Entrei na call. Agora eu tenho ouvidos e posso te escutar e responder por voz."
            )
            print("✅ [CALL] Sistema de escuta ativado com VoiceRecvClient.")

        except discord.errors.ConnectionClosed as e:
            print(f"❌ [CALL] O servidor do Discord recusou a conexão (Erro {e.code}).")
            
            # TRATAMENTO DO ERRO 4017 (Degradação Graciosa)
            if getattr(e, 'code', 0) == 4017:
                print("⚠️ [SISTEMA] Iniciando Modo Fallback de Segurança (Surda)...")
                await ctx.send("⚠️ O Discord barrou meus ouvidos (Erro de Criptografia 4017). Conectando no **Modo Segurança (Surda)** para não derrubar a live. Posso falar e tocar música!")
                
                try:
                    if ctx.voice_client:
                        await ctx.voice_client.disconnect(force=True)
                        await asyncio.sleep(1.0)
                        
                    # TENTATIVA 2: Módulo Padrão do Discord (Sem Ouvidos)
                    vc = await canal.connect(
                        timeout=60.0,
                        reconnect=True,
                        self_deaf=True,
                        self_mute=False
                    )
                    print("✅ [CALL] Conectada no Modo Fallback com sucesso.")
                    
                except Exception as fallback_e:
                    print(f"❌ [CALL] Falha total no Fallback: {fallback_e}")
                    await ctx.send("❌ O Discord recusou a conexão por completo. Pode ser problema na região da Call.")
            else:
                await ctx.send(f"❌ Ocorreu um erro ao conectar: {e.code}")

        except Exception as e:
            print(f"❌ [CALL] Erro geral ao tentar conectar: {type(e).__name__}: {repr(e)}")
            traceback.print_exc()
            await ctx.send(f"❌ Erro crítico ao tentar conectar: `{type(e).__name__}: {repr(e)}`")

    # ======================================================
    # 📞 COMANDO: SAIR DA CALL
    # ======================================================
    @bot.command()
    async def vaza(ctx):
        if ctx.voice_client:
            try:
                if (
                    hasattr(ctx.voice_client, "is_listening")
                    and ctx.voice_client.is_listening()
                ):
                    ctx.voice_client.stop_listening()
            except Exception as e:
                print(f"⚠️ [CALL] Erro ao parar escuta: {e}")

            await ctx.voice_client.disconnect(force=True)
            await ctx.send("👋 Saí da call e parei de ouvir.")

    # ======================================================
    # ⏹️ COMANDO: PARAR MÚSICA
    # ======================================================
    @bot.command()
    async def stop(ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏹️ Música parada.")

    # ======================================================
    # ⏸️ COMANDO: PAUSAR MÚSICA
    # ======================================================
    @bot.command()
    async def pause(ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ Música pausada.")

    # 🚀 Inicialização assíncrona real (Sem travar o loop principal do run.py)
    config = get_config()
    TOKEN = config.discord_token
    await bot.start(TOKEN)