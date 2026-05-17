"""Cliente LLM assincrono para Groq Cloud.

Substitui o padrao repetitivo encontrado em run.py:
    res = await asyncio.to_thread(lambda: client.chat.completions.create(...))

Centraliza toda a comunicacao com a Groq em um unico ponto,
com suporte a:
- Chat completions (modelo principal: llama-3.3-70b-versatile)
- Fast completions (modelo rapido: llama-3.1-8b-instant)
- Vision (modelo de visao: llama-3.2-11b-vision-preview)
- Whisper transcription (whisper-large-v3-turbo)
- Retry com backoff exponencial
- Limpeza de <think> tags (DeepSeek-R1)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from groq import Groq

from Arcana.Core.config import get_config

logger = logging.getLogger(__name__)


class LLMClient:
    """Cliente assincrono para Groq Cloud.

    Encapsula o Groq SDK (sincrono) em chamadas via asyncio.to_thread,
    garantindo que nenhuma chamada bloqueie o event loop.

    Uso:
        client = LLMClient()
        resposta = await client.chat([
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
        ])
    """

    def __init__(
        self,
        api_key_llm: Optional[str] = None,
        api_key_vision: Optional[str] = None,
        model_main: Optional[str] = None,
        model_fast: Optional[str] = None,
        model_vision: Optional[str] = None,
        max_retries: int = 3,
    ):
        config = get_config()
        self.api_key_llm = api_key_llm or config.groq_api_key_llm
        self.api_key_vision = api_key_vision or config.groq_api_key_vision
        self.model_main = model_main or config.groq_model_main
        self.model_fast = model_fast or config.groq_model_fast
        self.model_vision = model_vision or config.groq_model_vision
        self.max_retries = max_retries

        # Clientes Groq (leves, podem ser criados diretamente)
        self._client_llm: Optional[Groq] = None
        self._client_vision: Optional[Groq] = None

    @property
    def client_llm(self) -> Groq:
        """Cliente Groq para LLM (lazy init)."""
        if self._client_llm is None:
            if not self.api_key_llm:
                raise ValueError("GROQ_API_KEY_LLM nao configurada")
            self._client_llm = Groq(api_key=self.api_key_llm)
        return self._client_llm

    @property
    def client_vision(self) -> Groq:
        """Cliente Groq para Vision (lazy init)."""
        if self._client_vision is None:
            key = self.api_key_vision or self.api_key_llm
            if not key:
                raise ValueError("GROQ_API_KEY_VISION nao configurada")
            self._client_vision = Groq(api_key=key)
        return self._client_vision

    @staticmethod
    def _clean_response(text: str) -> str:
        """Remove <think> tags do DeepSeek-R1 e outras sujeiras."""
        import re

        text = re.sub(
            r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL
        )
        return text.strip()

    async def _retry(
        self,
        func,
        *args,
        **kwargs,
    ) -> Any:
        """Executa uma funcao com retry e backoff exponencial."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return await asyncio.to_thread(func, *args, **kwargs)
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Tentativa {attempt + 1}/{self.max_retries} falhou: {exc}. "
                        f"Retentando em {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Todas as {self.max_retries} tentativas falharam: {exc}"
                    )
        raise RuntimeError(
            f"Falha na API Groq apos {self.max_retries} tentativas: {last_error}"
        )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Chat completion usando o modelo principal.

        Args:
            messages: Lista de mensagens [{"role": "...", "content": "..."}]
            model: Modelo a usar (default: llama-3.3-70b-versatile)
            temperature: Temperatura (default: config.groq_temperature)
            max_tokens: Max tokens (default: config.groq_max_tokens)

        Returns:
            Conteudo da resposta como string limpa
        """
        config = get_config()
        model = model or self.model_main
        temperature = temperature or config.groq_temperature
        max_tokens = max_tokens or config.groq_max_tokens

        def _call():
            response = self.client_llm.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        result = await self._retry(_call)
        cleaned = self._clean_response(result)
        logger.debug(f"Resposta chat ({len(cleaned)} chars): {cleaned[:100]}...")
        return cleaned

    async def chat_fast(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.3,
    ) -> str:
        """Chat rapido usando modelo leve (llama-3.1-8b-instant).

        Ideal para resumos, classificacoes e tarefas simples.
        """
        return await self.chat(
            messages=messages,
            model=self.model_fast,
            temperature=temperature,
        )

    async def vision(
        self,
        prompt: str,
        image_b64: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        """Analise de imagem via modelo de visao.

        Args:
            prompt: Descricao do que analisar na imagem
            image_b64: Imagem em base64 (sem o prefixo data:image/...)
            model: Modelo (default: llama-3.2-11b-vision-preview)
            temperature: Temperatura (baixa para analise precisa)
            max_tokens: Max tokens

        Returns:
            Descricao da imagem
        """
        model = model or self.model_vision

        def _call():
            response = self.client_vision.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content

        result = await self._retry(_call)
        cleaned = self._clean_response(result)
        logger.debug(f"Resposta vision ({len(cleaned)} chars)")
        return cleaned

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "pt",
        model: Optional[str] = None,
    ) -> str:
        """Transcreve audio via Whisper na Groq.

        Args:
            audio_bytes: Dados WAV do audio
            language: Codigo da lingua (default: pt)
            model: Modelo Whisper (default: whisper-large-v3-turbo)

        Returns:
            Texto transcrito
        """
        import io
        import wave

        config = get_config()
        model = model or config.groq_whisper_model

        # Prepara o arquivo WAV em memoria
        with io.BytesIO() as wb:
            with wave.open(wb, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_bytes)
            wb.seek(0)
            final_wav = wb.read()

        def _call():
            import requests

            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {self.api_key_llm}"}
            files = {
                "file": ("input.wav", final_wav, "audio/wav"),
                "model": (None, model),
                "language": (None, language),
            }
            resp = requests.post(url, headers=headers, files=files)
            if resp.status_code == 200:
                return resp.json().get("text", "")
            raise RuntimeError(f"Whisper API error: {resp.status_code} {resp.text}")

        result = await self._retry(_call)
        logger.debug(f"Transcricao: {result[:100]}...")
        return result

    async def summarize(
        self,
        texts: list[str],
        instruction: str,
    ) -> str:
        """Resume uma lista de textos usando o modelo rapido.

        Args:
            texts: Lista de textos para resumir
            instruction: Instrucao de como resumir

        Returns:
            Resumo consolidado
        """
        texto_junto = "\n".join(texts)
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": texto_junto},
        ]
        return await self.chat_fast(messages)


# Singleton global
_llm_client_instance: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Retorna a instancia unica do LLMClient (singleton)."""
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = LLMClient()
    return _llm_client_instance


def reset_llm_client() -> None:
    """Reseta o singleton do LLMClient (util para testes)."""
    global _llm_client_instance
    _llm_client_instance = None
