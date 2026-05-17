"""
Shogun - Serviço de Voz Local Assíncrono
Escuta o microfone físico, processa via Groq e executa a fala local.
"""

import asyncio
import os
import re
import subprocess
import pyaudio
import requests
from typing import Dict, Any

from Arcana.Core.config import get_config
from Arcana.Core.event_bus import EventBus
from Arcana.Core.llm_client import LLMClient

class LocalVoiceListener:
    def __init__(self, event_bus: EventBus, llm_client: LLMClient):
        self.config = get_config()
        self.event_bus = event_bus
        self.llm_client = llm_client
        self.pyaudio_ctx = pyaudio.PyAudio()
        self.is_listening = False
        self.task: asyncio.Task | None = None
        
        # Se inscreve no barramento para ouvir os comandos da interface gráfica e hotkeys
        self.event_bus.subscribe("toggle_gatilho", self._on_toggle_trigger)
        print("🎙️ [VOZ LOCAL] Serviço de escuta do Microfone integrado ao EventBus.")

    async def _on_toggle_trigger(self, data: Dict[str, Any]) -> None:
        """Callback acionado quando a GUI ou Hotkey altera o estado do microfone."""
        active = data.get("active", not self.is_listening)
        
        if active and not self.is_listening:
            self.is_listening = True
            self.task = asyncio.create_task(self._recording_loop())
            print("🎙️ [VOZ LOCAL] Captura do Microfone Físico ATIVADA.")
        elif not active and self.is_listening:
            self.is_listening = False
            if self.task:
                self.task.cancel()
                self.task = None
            print("🔇 [VOZ LOCAL] Captura do Microfone Físico DESATIVADA.")

    async def _recording_loop(self):
        """Loop assíncrono de gravação que monitora o áudio do microfone."""
        loop = asyncio.get_running_loop()
        
        try:
            stream = await loop.run_in_executor(
                None,
                lambda: self.pyaudio_ctx.open(
                    format=pyaudio.paInt16,
                    channels=self.config.audio_channels,
                    rate=self.config.audio_sample_rate,
                    input=True,
                    frames_per_buffer=self.config.audio_chunk_size
                )
            )
        except Exception as e:
            print(f"❌ [VOZ LOCAL] Erro ao abrir hardware de áudio: {e}")
            self.is_listening = False
            return

        audio_buffer = bytearray()
        silence_frames = 0
        falando = False

        print("🎙️ [VOZ LOCAL] Shogun está te ouvindo na vida real... Pode falar!")

        try:
            while self.is_listening:
                data = await asyncio.to_thread(stream.read, self.config.audio_chunk_size, exception_on_overflow=False)
                
                if not data:
                    await asyncio.sleep(0.01)
                    continue

                import audioop
                rms = audioop.rms(data, 2)
                
                # Detecção de atividade de voz simples baseada em volume (RMS)
                if rms > 500: 
                    if not falando:
                        falando = True
                        print("🎚️ [VOZ LOCAL] Capturando fala...")
                    audio_buffer.extend(data)
                    silence_frames = 0
                else:
                    if falando:
                        audio_buffer.extend(data)
                        silence_frames += 1
                        
                        if silence_frames > self.config.silence_frames_threshold:
                            print("🧠 [VOZ LOCAL] Fim de fala detectado. Processando...")
                            asyncio.create_task(self._processar_audio_local(bytes(audio_buffer)))
                            audio_buffer = bytearray()
                            silence_frames = 0
                            falando = False
                            
                await asyncio.sleep(0.001)
                
        except asyncio.CancelledError:
            pass
        finally:
            if stream:
                await asyncio.to_thread(stream.stop_stream)
                await asyncio.to_thread(stream.close)

    async def _processar_audio_local(self, audio_bytes: bytes):
        """Envia os bytes para a Groq, pega o chat e dispara o TTS local."""
        try:
            texto_usuario = await self.llm_client.transcribe(
                audio_bytes=audio_bytes,
                model=self.config.groq_whisper_model,
                language="pt"
            )
            
            if not texto_usuario or len(texto_usuario.strip()) < 2:
                return
                
            print(f"🗣️ [VOCAL REAL] Você disse: {texto_usuario}")
            
            messages = [
                {"role": "system", "content": self.config.persona_text},
                {"role": "user", "content": f"O Mestre falou com você por voz no mundo real: {texto_usuario}"}
            ]
            
            resposta_ia = await self.llm_client.chat(messages=messages, model=self.config.groq_model_main)
            
            if resposta_ia:
                resposta_limpa = re.sub(r"<[^>]+>", "", resposta_ia).strip()
                print(f"🤖 [VOCAL REAL] Shogun respondeu: {resposta_limpa}")
                await self._gerar_fala_local(resposta_limpa)
                
        except Exception as e:
            print(f"❌ [VOZ LOCAL] Erro ao processar fluxo de voz: {e}")

    async def _gerar_fala_local(self, texto: str):
        """Gera o arquivo mp3 exclusivo e executa a reprodução local invisível."""
        # 🔥 ALTERAÇÃO CRÍTICA: Usa um arquivo separado para nunca travar a call do Discord!
        output_file = "local_vocal.mp3"
        
        try:
            # 🔥 FILTRO ANTI-PSICOPATA: Arranca as tags da mente dela antes de ir pra voz
            import re
            texto_limpo = re.sub(r'\[.*?\]', '', texto)  
            texto_limpo = re.sub(r'<.*?>', '', texto_limpo)    
            texto_limpo = re.sub(r'MUSICA:.*', '', texto_limpo, flags=re.IGNORECASE)
            texto_limpo = texto_limpo.strip()

            # 🔥 DESTRAVA O ARQUIVO DE ÁUDIO NO WINDOWS ANTES DE GERAR UM NOVO
            try:
                import ctypes
                import os
                ctypes.windll.winmm.mciSendStringW('close shogun_local_fala', None, 0, 0)
                if os.path.exists(output_file):
                    os.remove(output_file)
            except Exception:
                pass

            if self.config.has_elevenlabs:
                print("🗣️ [TTS] Gerando voz via ElevenLabs de Elite...")
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.config.elevenlabs_voice_id}"
                headers = {"xi-api-key": self.config.elevenlabs_api_key, "Content-Type": "application/json"}
                # 👇 Agora usamos a variável limpa aqui:
                payload = {"text": texto_limpo, "model_id": self.config.elevenlabs_model, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
                
                resp = await asyncio.to_thread(requests.post, url, json=payload, headers=headers)
                if resp.status_code == 200:
                    with open(output_file, "wb") as f:
                        f.write(resp.content)
                else:
                    raise RuntimeError(f"Erro ElevenLabs: {resp.status_code}")
            else:
                print("🗣️ [TTS] Chave ElevenLabs ausente. Usando Microsoft Fallback...")
                import edge_tts
                # 👇 E usamos a variável limpa aqui também no Fallback:
                communicate = edge_tts.Communicate(texto_limpo, self.config.edge_tts_voice)
                await communicate.save(output_file)

            # 🔊 REPRODUÇÃO FANTASMA VIA WIN32 API
            if os.path.exists(output_file):
                import ctypes
                
                def _play():
                    caminho_abs = os.path.abspath(output_file)
                    ctypes.windll.winmm.mciSendStringW(f'open "{caminho_abs}" type mpegvideo alias shogun_local_fala', None, 0, 0)
                    ctypes.windll.winmm.mciSendStringW('play shogun_local_fala wait', None, 0, 0)
                    ctypes.windll.winmm.mciSendStringW('close shogun_local_fala', None, 0, 0)

                await asyncio.to_thread(_play)
                
        except Exception as e:
            print(f"❌ [TTS LOCAL] Erro ao reproduzir ou gerar áudio: {e}")