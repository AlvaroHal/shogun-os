# ============//======================//================
#region 📚 CHAMADAS E MODOS
# ======================================================
import asyncio
import json
import re
import io
import wave
import torch
import numpy as np
import pyaudio
import requests
import edge_tts
import random
import pygame
import keyboard
import threading
import os
import base64
import tkinter as tk
import subprocess
import sys
from tkinter import ttk
from PIL import ImageGrab
from datetime import datetime
from groq import Groq
from openai import OpenAI
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# 🔥 IMPORTAÇÃO DA INTERFACE GRÁFICA ATUALIZADA
from Arcana.Apps.gui_handler import RemGUI

# 🔥 IMPORTAÇÃO DO SEU MÓDULO DE PESQUISA
import Arcana.Net.search_ddg as search_ddg

# 🔥 IMPORTAÇÃO DO MÓDULO DE AUTOMAÇÃO DE APPS
from Arcana.Aura.app_launcher import AppLauncher 

# 🔥 IMPORTAÇÃO DO MÓDULO DO DISCORD
from Arcana.Net.discord_Rem import run_discord_thread

# --- CARREGAMENTO DAS CHAVES ---
load_dotenv()

# Pegando as chaves do .env
GROQ_API_KEY_LLM = os.getenv("GROQ_API_KEY_LLM")
GROQ_API_KEY_VISION = os.getenv("GROQ_API_KEY_VISION")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

# 🔥 AS NOVAS CHAVES DA SHOGUN
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

# DEBUG: Agora vai funcionar porque as variáveis acima já foram criadas
print(f"DEBUG: API KEY carregada? {'Sim' if ELEVENLABS_API_KEY else 'Não'}")
print(f"DEBUG: VOICE ID carregado? {'Sim' if ELEVENLABS_VOICE_ID else 'Não'}")

# Inicializa o cliente (SÓ SE A CHAVE EXISTIR)
if ELEVENLABS_API_KEY:
    el_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
else:
    print("⚠️ AVISO: ELEVENLABS_API_KEY não encontrada no seu .env")
#endregion
# ======================================================
#region 🧠 VARIÁVEIS GLOBAIS E PAINEL
# ======================================================
# Cria a pasta automaticamente se ela não existir
os.makedirs("Arcana/armazen", exist_ok=True)

# 🔥 ARQUIVOS FIXOS
BRAIN_FILE = "Arcana/armazen/brain.json"
MEMORIA_FILE = "Arcana/armazen/memoria.json"
SEARCH_MEMORY_FILE = "Arcana/armazen/pesquisa_memoria.json" 

VISAO_HABILITADA = False # Controlo global do F2
CONTADOR_VISAO = 0       # Contador para limpar a memória visual

# Fila para não travar o console de chat
chat_terminal_queue = []

def thread_leitor_terminal():
    """Lê o terminal em segundo plano para o Modo Chat não travar o loop visual"""
    while True:
        try:
            msg = input("")
            if msg.strip():
                chat_terminal_queue.append(msg.strip())
        except:
            pass

# Leitor do Estado da Interface (UI)
def ler_estado_ui():
    try:
        with open(BRAIN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

#endregion
# ======================================================
#region 👁️ VISÃO COMPUTACIONAL E INJETORES
# ======================================================
def toggle_visao(e=None):
    global VISAO_HABILITADA
    VISAO_HABILITADA = not VISAO_HABILITADA
    play_beep("inicio" if VISAO_HABILITADA else "fim")
    print(f"\n[SISTEMA] 👁️ Permissão de Visão (Atalho F2): {'LIGADA' if VISAO_HABILITADA else 'DESLIGADA'}")
    
    # Atualiza o JSON para o painel refletir a mudança do teclado
    try:
        estado = ler_estado_ui()
        estado["visao_computacional_ativa"] = VISAO_HABILITADA
        with open(BRAIN_FILE, 'w', encoding='utf-8') as f: json.dump(estado, f, indent=4)
    except: pass

def toggle_gatilho(e):
    if os.path.exists(BRAIN_FILE):
        try:
            with open(BRAIN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            novo_estado = not data.get("trigger_active", False)
            data["trigger_active"] = novo_estado
            with open(BRAIN_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            play_beep("inicio" if novo_estado else "fim")
            print(f"\n[SISTEMA] 🎤 Gatilho de Voz (F3): {'LIGADO' if novo_estado else 'DESLIGADO'}")
        except Exception as ex:
            pass

def requer_visao(texto):
    texto_min = texto.lower()
    padrao_palavras = r"\b(olha|veja|tela|imagem|foto|analisa|analise|lê|leia|vendo)\b"
    frases_exatas = ["o que é isso", "o que e isso", "o que tem na tela"]
    if re.search(padrao_palavras, texto_min): return True
    if any(frase in texto_min for frase in frases_exatas): return True
    return False

def requer_despertar(texto, nome_ai):
    texto_min = texto.lower()
    padrao_gatilhos = rf"\b({nome_ai.lower()}|ei|acorda|ouve|escuta)\b"
    return bool(re.search(padrao_gatilhos, texto_min))

def detectar_comando_musica(texto):
    t = texto.lower().strip()
    if re.search(r'\b(pausar|pausa|despausa|resume)\b', t): return "PAUSE"
    if re.search(r'\b(para a música|para tudo|stop|desliga a música|calar a boca)\b', t): return "STOP"
    if re.search(r'\b(pula|próxima|skip|pular|passa)\b', t): return "SKIP"
    
    padrao_tocar = r'\b(toca|tocar|coloca|colocar|põe|bota)\b.*?(música|músicas|som|playlist|rock|kpop|pop|lofi|clássica|jazz|rap|funk|metal|eletrônica|abertura|encerramento)'
    if re.search(padrao_tocar, t):
        query = re.sub(r'\b(toca|tocar|coloca|colocar|põe|bota|a|o|um|umas|uma|alguma|algumas|música|músicas|som|playlist|ai|aí|pra|mim)\b', '', t).strip()
        query = re.sub(r'[^a-zA-Z0-9\s\-\u00C0-\u00FF]', '', query).strip()
        return f"PLAY:{query}" if query else "PLAY:uma música aleatória"
    
    if len(t.split()) <= 6 and re.match(r'^(toca|coloca|põe|bota)\b', t):
        query = re.sub(r'^(toca|coloca|põe|bota|a|o|um|uma|umas|alguma)\b', '', t).strip()
        return f"PLAY:{query}" if query else "PLAY:uma recomendação aleatória"
        
    return None

def capturar_tela_b64():
    try:
        img = ImageGrab.grab()
        img.thumbnail((1024, 1024))
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=70)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        print(f" Erro ao capturar ecrã: {e}")
        return None
#endregion
# ======================================================
#region 🧠 BRAIN E PERSISTÊNCIA
# ======================================================
def carregar_brain():
    if not os.path.exists(BRAIN_FILE):    
        return {}, "Sistema Padrão", "Assistente", False, False, {"local": "nvidia"}, False 
    
    with open(BRAIN_FILE, 'r', encoding='utf-8') as f:
        brain = json.load(f)
        
    p = brain.get('personality', {'name': 'Assistente', 'role': 'Assistente de IA'})
    nome_ai = p.get('name', 'Assistente')
    traits = "\n- ".join(p.get('traits', []))
    
    r = "\n- ".join(brain.get('rules', {}).get('response_style', []))
    s = brain.get('emotional_analysis', {}).get('sentiment', 'Neutral')
    trigger = brain.get("trigger_active", False)
    discord_active = brain.get("discord_active", False) 
    modelos = brain.get("modelos_ativos", {"local": "nvidia", "discord": "groq"})
    vtuber_ativo = brain.get("vtuber_overlay_ativo", False)
    
    relacionamentos = brain.get('relationships', {})
    nome_user = list(relacionamentos.keys())[0] if relacionamentos else "Mestre"
    user_data = relacionamentos.get(nome_user, {})
    relacao = f"Nome do Usuário com quem você está falando: {nome_user}\nRelação: {user_data.get('relationship', 'Mestre')}\nComportamento com ele: {user_data.get('behavior', '')}"
    
    vocab_dict = brain.get('vocabulário', {})
    vocabulario = "\n- ".join([f"{k}: {v}" for k, v in vocab_dict.items()])

    tela_atual = brain.get('visual_context', {}).get('screen_content', '')

    prompt = (
        f"Nome: {nome_ai}\n"
        f"Papel: {p.get('role', 'Assistente')}\n\n"
        f"Traços de Personalidade:\n- {traits}\n\n"
        f"Sobre o Usuário:\n{relacao}\n\n"
        f"Estado Emocional: {s}\n\n"
        f"Diretrizes de Conversa (Incorpore de forma fluida e natural, varie as estruturas das frases):\n- {r}\n\n"
        f"Vocabulário Contextual (Use estas palavras/gírias de forma esporádica e APENAS se encaixar perfeitamente no assunto):\n- {vocabulario}"
    )
    
    if tela_atual:
        prompt += f"\n\n[CONTEXTO VISUAL ATUAL DA TELA]:\n- {tela_atual}"
    
    return brain, prompt, nome_ai, trigger, discord_active, modelos, vtuber_ativo

def salvar_gatilho_brain(estado):
    if os.path.exists(BRAIN_FILE):
        with open(BRAIN_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
        data["trigger_active"] = estado
        with open(BRAIN_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)

def salvar_discord_brain(estado):
    if os.path.exists(BRAIN_FILE):
        with open(BRAIN_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
        data["discord_active"] = estado
        with open(BRAIN_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)

def salvar_visao_brain(descricao):
    if os.path.exists(BRAIN_FILE):
        with open(BRAIN_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if "visual_context" not in data: data["visual_context"] = {}
        data["visual_context"]["screen_content"] = descricao
        with open(BRAIN_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
#endregion
# ======================================================
#region 📚 GERENCIADOR DE MEMÓRIA
# ======================================================
def carregar_memoria():
    if not os.path.exists(MEMORIA_FILE): return {"master_summary": "", "recent_summaries": [], "mensagens": []}
    try:
        with open(MEMORIA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {"master_summary": "", "recent_summaries": [], "mensagens": []}

def salvar_memoria(memoria):
    with open(MEMORIA_FILE, 'w', encoding='utf-8') as f:
        json.dump(memoria, f, indent=4, ensure_ascii=False)

def carregar_memoria_pesquisa():
    if not os.path.exists(SEARCH_MEMORY_FILE): return {"master_search_summary": "", "recent_searches": []}
    try:
        with open(SEARCH_MEMORY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {"master_search_summary": "", "recent_searches": []}

async def gerenciar_memoria_pesquisa(client_llm, query, resultados):
    memoria = carregar_memoria_pesquisa()
    memoria["recent_searches"].append({"query": query, "resultados": resultados[:400]})

    if len(memoria["recent_searches"]) >= 5:
        print("\n [SISTEMA] Otimizando banco de dados de Pesquisas (Resumindo web)...")
        textos_resumo = [f"Busca: '{m['query']}' | Resultado: {m['resultados']}" for m in memoria["recent_searches"]]
        if memoria["master_search_summary"]: textos_resumo.insert(0, f"Conhecimento Web Anterior: {memoria['master_search_summary']}")
        master_resumo = await resumir_com_ia(client_llm, textos_resumo, "Você é um bibliotecário digital. Faça um resumo direto e conciso de todo o conhecimento e fatos adquiridos nestas pesquisas web. Descarte informações irrelevantes e foque apenas nos fatos úteis que podem servir de contexto no futuro.")
        if master_resumo:
            memoria["master_search_summary"] = master_resumo
            memoria["recent_searches"] = [] 

    with open(SEARCH_MEMORY_FILE, 'w', encoding='utf-8') as f: json.dump(memoria, f, indent=4, ensure_ascii=False)
    return memoria

async def resumir_com_ia(client_llm, textos, comando):
    texto_junto = "\n".join(textos)
    try:
        res = await asyncio.to_thread(lambda: client_llm.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct", 
            messages=[{"role": "system", "content": comando}, {"role": "user", "content": texto_junto}],
            temperature=0.3
        ))
        return res.choices[0].message.content
    except Exception as e:
        print(f" Erro ao resumir memória: {e}")
        return ""

async def gerenciar_e_salvar_memoria(client_llm, sender, message):
    memoria = carregar_memoria()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    memoria["mensagens"].append({"timestamp": agora, "sender": sender, "message": message})

    if len(memoria["mensagens"]) >= 15:
        print("\n [SISTEMA] Otimizando memória (Resumindo conversas antigas)...")
        msgs_para_resumir = memoria["mensagens"][:10]
        textos_resumo = [f"[{m['timestamp']}] {m['sender']}: {m['message']}" for m in msgs_para_resumir]
        
        novo_resumo = await resumir_com_ia(client_llm, textos_resumo, "Faça um resumo direto e curto sobre o que foi conversado nessas mensagens.")
        if novo_resumo:
            memoria["recent_summaries"].append(novo_resumo)
            memoria["mensagens"] = memoria["mensagens"][10:] 

        if len(memoria["recent_summaries"]) >= 5:
            print(" [SISTEMA] Consolidando Resumo Mestre...")
            textos_master = memoria["recent_summaries"].copy()
            if memoria["master_summary"]: textos_master.insert(0, f"Resumo Histórico: {memoria['master_summary']}")
            master_resumo = await resumir_com_ia(client_llm, textos_master, "Integre todos esses resumos em um único 'Resumo Mestre' detalhando tudo o que já aconteceu com o usuário.")
            if master_resumo:
                memoria["master_summary"] = master_resumo
                memoria["recent_summaries"] = [] 

    salvar_memoria(memoria)
    return memoria

def construir_historico_para_api(sys_prompt, memoria, nome_ai, launcher=None):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    prompt_completo = sys_prompt + f"\n\n[SISTEMA DE CAPACIDADES MÁXIMAS]:"
    prompt_completo += "\n1. CONTROLO DE MÚSICA: Você É o bot de música. Use a tag <PLAY:pedido> APENAS e EXCLUSIVAMENTE quando o usuário pedir explicitamente para tocar uma música. NUNCA envie tags de música do nada."
    prompt_completo += "\n2. CONTROLO DO PC: Você tem acesso total ao PC do Alvaro. Use <APP:abrir:alvo> ou <APP:fechar:alvo> para comandar o computador. Não invente que é apenas uma IA de texto."
    prompt_completo += "\n3. BUSCA WEB: Use [PESQUISAR: termo] para ler notícias e dados atuais. Você é conectada à internet."
    prompt_completo += "\n4. ACESSO LIVRE AO WINDOWS: Se o usuário pedir para abrir uma pasta, arquivo ou programa genérico que NÃO está na sua lista de Aplicativos Instalados, use a tag <CMD: comando_windows>. Exemplos: <CMD: documents>, <CMD: downloads>, <CMD: calc.exe>, <CMD: notepad.exe>, <CMD: spotify>."
    
    prompt_completo += f"\n\n[SISTEMA DE TEMPO]\nO momento atual exato é: {agora}.\nVocê recebe o horário para entender o ritmo da conversa."
    
    prompt_completo += "\n\n[REGRAS ESTRITAS DE RESPOSTA]:"
    prompt_completo += "\n- ZERO ROLEPLAY: Proibido narrar ações físicas, usar itálicos ou asteriscos (ex: *sorri*). Fale como uma pessoa real."
    prompt_completo += "\n- ZERO TAGS FALSAS: Nunca invente tags como <ignore> ou <pensamento>. Use apenas as oficiais ensinadas aqui."
    prompt_completo += "\n- SEJA CURTA E GROSSA: Responda em 1 ou 2 frases curtas. Você odeia textões e explicações desnecessárias."
    
    if launcher and hasattr(launcher, 'obter_nomes_dos_apps'):
        nomes_apps = launcher.obter_nomes_dos_apps()
        prompt_completo += f"\n\n[INTEGRAÇÃO COM O COMPUTADOR]:"
        prompt_completo += f"\n📂 APLICATIVOS INSTALADOS: {nomes_apps}."
        prompt_completo += "\nPara abrir ou pesquisar no navegador/youtube, use: <APP:abrir:alvo:termo_de_busca>."
        
        prompt_completo += "\n\n[MANUAL DO PLAYER DE MÚSICA]:"
        prompt_completo += "\n- TOCAR: <PLAY:nome_da_musica>"
        prompt_completo += "\n- PULAR: <SKIP>"
        prompt_completo += "\n- PAUSAR: <PAUSE>"
        prompt_completo += "\n- PARAR: <STOP>"
        prompt_completo += "\n🚨 REGRA DE OURO DA MÚSICA:"
        prompt_completo += "\n1. É OBRIGATÓRIO escrever uma frase sua (entre 1 e 7 palavras) ANTES de colocar a tag. NUNCA envie apenas a tag! (Ex: 'Aqui está a sua música. <PLAY:rock>')."
        prompt_completo += "\n2. NUNCA tente adivinhar nomes de músicas de animes ou séries. O sistema usa o YouTube, por isso gere a tag EXATAMENTE com as palavras que o usuário usou."
        prompt_completo += "\n3. É ESTRITAMENTE PROIBIDO tocar música do nada. NUNCA use a tag <PLAY> se o usuário não lhe deu uma ordem clara para tocar algo."
    
    memoria_pesquisa = carregar_memoria_pesquisa()
    if memoria_pesquisa.get("master_search_summary"):
        prompt_completo += f"\n\n[CONHECIMENTO WEB ADQUIRIDO]:\n{memoria_pesquisa['master_search_summary']}"

    if memoria["master_summary"]:
        prompt_completo += f"\n\n[MEMÓRIA DE LONGO PRAZO]:\n{memoria['master_summary']}"
        
    if memoria["recent_summaries"]:
        prompt_completo += f"\n\n[ACONTECIMENTOS RECENTES]:\n" + "\n".join(memoria["recent_summaries"])

    historico = [{"role": "system", "content": prompt_completo}]
    
    for m in memoria["mensagens"]:
        role = "assistant" if m["sender"] == nome_ai else "user"
        if role == "user":
            historico.append({"role": role, "content": f"[Enviado em {m['timestamp']}] {m['message']}"})
        else:
            msg_limpa = m['message'].split("] ", 1)[-1] if m['message'].startswith("[2026") else m['message']
            msg_limpa = re.sub(rf"^{nome_ai} disse:\s*", "", msg_limpa, flags=re.IGNORECASE)
            msg_limpa = re.sub(rf"^{nome_ai}:\s*", "", msg_limpa, flags=re.IGNORECASE)
            historico.append({"role": role, "content": msg_limpa.strip()})
            
    return historico
#endregion
# ======================================================
#region 🎵 FEEDBACKS SONOROS E ÁUDIO
# ======================================================
def play_beep(tipo="inicio"):
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2)
        duration = 0.1
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        freq = 800 if tipo == "inicio" else 400
        t = np.linspace(0, duration, n_samples, False)
        signal = np.sin(2 * np.pi * freq * t) * 0.3
        sound_array = (signal * 32767).astype(np.int16)
        stereo_array = np.column_stack((sound_array, sound_array))
        sound = pygame.sndarray.make_sound(stereo_array)
        sound.play()
    except Exception as e:
        pass

class LocalVoiceFilter:
    def __init__(self):
        self.model, _ = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False)
    
    def is_human_voice(self, audio_data, rate=16000):
        audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
        if np.max(np.abs(audio_int16)) < 300: return False
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        tensor = torch.from_numpy(audio_float32)
        with torch.no_grad():
            confidence = self.model(tensor, rate).item()
        return confidence > 0.75

# 🔥 VOZ 1: MICROSOFT (ECONÔMICA/GRÁTIS)
async def microsoft_speak(text): 
    if not text: return
    VOICE = "pt-BR-FranciscaNeural" 
    output_file = "vocal_.mp3"
    
    text_limpo_voz = re.sub(r'<[^>]+>', '', text).strip()
    text_limpo_voz = re.sub(r'\[.*?\]', '', text_limpo_voz).strip()
    text_limpo_voz = text_limpo_voz.replace('*', '') 
    
    communicate = edge_tts.Communicate(text_limpo_voz, VOICE)
    await communicate.save(output_file)
    
    pygame.mixer.init()
    try:
        pygame.mixer.music.load(output_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): await asyncio.sleep(0.1)
        pygame.mixer.music.unload() 
    except: pass
    finally: pygame.mixer.quit()

# 🔥 VOZ 2: ELEVENLABS (PROFISSIONAL/CLONADA)
async def elevenlabs_speak(text): 
    if not text: return
    output_file = "vocal_.mp3"
    
    # Sua lógica de limpeza (mantida 100%)
    text_limpo_voz = re.sub(r'<[^>]+>', '', text).strip()
    text_limpo_voz = re.sub(r'\[.*?\]', '', text_limpo_voz).strip()
    text_limpo_voz = re.sub(r'(?<=\d)\s*\*\s*(?=\d)', ' vezes ', text_limpo_voz)
    text_limpo_voz = text_limpo_voz.replace('*', '') 
    
    if not text_limpo_voz: text_limpo_voz = "Comando executado."
        
    try:
        # 🎙️ O método oficial da versão nova
        audio_generator = el_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=text_limpo_voz,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        
        # Salva o áudio (escrevendo os pedaços que chegam da API)
        with open(output_file, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)

        # 🔊 Toca o áudio com seu mixer do Pygame
        pygame.mixer.init()
        pygame.mixer.music.load(output_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): 
            await asyncio.sleep(0.1)
        pygame.mixer.music.unload() 
    except Exception as e:
        print(f"⚠️ Erro na voz ElevenLabs: {e}")
    finally:
        pygame.mixer.quit()

async def whisper_transcription(audio_frames, api_key):
    audio_data = b''.join(audio_frames)
    with io.BytesIO() as wb:
        with wave.open(wb, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
            wf.writeframes(audio_data)
        wb.seek(0)
        final_wav = wb.read()
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    head = {"Authorization": f"Bearer {api_key}"}
    files = {"file": ("input.wav", final_wav, "audio/wav"), "model": (None, "whisper-large-v3-turbo"), "language": (None, "pt")}
    resp = await asyncio.to_thread(requests.post, url, headers=head, files=files)
    return resp.json().get("text", "") if resp.status_code == 200 else None
#endregion
# ======================================================
#region 🕹️ CÉREBRO DA IA (PROCESSAMENTO INTEGRADO)
# ======================================================
async def processar_ia(client_nvidia, client_llm, client_vision, sys_prompt, texto, nome_ai, usuario_nome, launcher, modo_chat=False):
    if not modo_chat:
        print(f"{usuario_nome}: {texto}")
        
    await gerenciar_e_salvar_memoria(client_llm, usuario_nome, texto)
    memoria_atual = carregar_memoria()
    
    historico_api = construir_historico_para_api(sys_prompt, memoria_atual, nome_ai, launcher)
    
    comando_musica = detectar_comando_musica(texto)
    if comando_musica:
        alerta = f"\n\n[ALERTA DE SISTEMA DO CÉREBRO]: Você OBRIGATORIAMENTE deve incluir a tag <{comando_musica}> no final da sua próxima fala para a música obedecer ao usuário. Sem a tag, a música não mudará!"
        historico_api[-1]["content"] += alerta
    
    if VISAO_HABILITADA and requer_visao(texto):
        print(" [SISTEMA] Intenção visual detetada! A analisar o ecrã com o Scout...")
        b64_img = capturar_tela_b64()
        if b64_img:
            prompt_vision = f"Descreva a imagem. Identifique contexto, textos, ações e detalhes.\nO usuário pediu: '{texto}'. Foque nisso."
            try:
                res_vision = await asyncio.to_thread(lambda: client_vision.chat.completions.create(
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_vision},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                        ]
                    }],
                    max_tokens=1024,
                    temperature=0.1
                ))
                descricao_imagem = res_vision.choices[0].message.content
                print(f" [ANÁLISE SCOUT CONCLUÍDA]")
                
                salvar_visao_brain(descricao_imagem)
                _, sys_prompt_atualizado, _, _, _, _, *_ = carregar_brain()
                historico_api = construir_historico_para_api(sys_prompt_atualizado, memoria_atual, nome_ai, launcher)
                historico_api[-1]["content"] += "\n\n[SISTEMA: Acabei de analisar o ecrã a teu pedido. O contexto visual atualizado já se encontra na tua mente.]"
                
            except Exception as e:
                print(f" Erro na API de Visão (Scout): {e}")

    _, _, _, _, _, modelos_config, *_ = carregar_brain()
    provedor_local = modelos_config.get("local", "nvidia")
    
    if provedor_local == "nvidia":
        cliente_ativo = client_nvidia
        id_modelo = "moonshotai/kimi-k2.5"
        extra = {"chat_template_kwargs": {"thinking": False}}
    else:
        cliente_ativo = client_llm
        id_modelo = "meta-llama/llama-4-scout-17b-16e-instruct"
        extra = None

    try:
        kwargs_initial = {
            "model": id_modelo,
            "messages": historico_api,
            "temperature": 0.7
        }
        if extra: kwargs_initial["extra_body"] = extra

        res = await asyncio.to_thread(lambda: cliente_ativo.chat.completions.create(**kwargs_initial))
        resposta_inicial = res.choices[0].message.content
        resposta_inicial = re.sub(r'<think>.*?</think>', '', resposta_inicial, flags=re.IGNORECASE | re.DOTALL).strip()
        
        resposta_final = resposta_inicial
        precisa_nova_resposta = False

        match_musica = re.search(r'<(PLAY:[^>]+|SKIP|PAUSE|STOP|RESUME)[^>]*>', resposta_inicial, re.IGNORECASE)
        if match_musica:
            tag_bruta = match_musica.group(1)
            if tag_bruta.upper().startswith("PLAY:"):
                tag_musica = "PLAY:" + tag_bruta[5:] 
            else:
                tag_musica = tag_bruta.upper() 
                
            tag_completa = match_musica.group(0)
            resposta_inicial = resposta_inicial.replace(tag_completa, "").strip()
            resposta_final = resposta_inicial 

            try:
                if os.path.exists(BRAIN_FILE):
                    with open(BRAIN_FILE, "r+", encoding="utf-8") as f:
                        brain_data = json.load(f)
                        brain_data["pending_music"] = f"<{tag_musica}>"
                        f.seek(0)
                        json.dump(brain_data, f, indent=4, ensure_ascii=False)
                        f.truncate()
                print(f"🎵 [SISTEMA] Comando de música enviado ao Discord: <{tag_musica}>")
            except Exception as e:
                print(f"❌ Erro ao enviar comando remoto para o Discord: {e}")

        if "<APP:" in resposta_inicial:
            resultado_app = launcher.process_llm_tag(resposta_inicial)
            if resultado_app:
                historico_api.append({"role": "assistant", "content": resposta_inicial})
                historico_api.append({"role": "user", "content": f"[SISTEMA DE AUTOMAÇÃO]: {resultado_app}"})
                precisa_nova_resposta = True

        if "PESQUISAR:" in resposta_inicial.upper():
            match = re.search(r"[\[<]PESQUISAR:\s*(.*?)[\]>]", resposta_inicial, re.IGNORECASE)
            if match:
                termo = match.group(1).strip()
                print(f" [SISTEMA] IA ativou busca autônoma para: '{termo}'")
                
                resultados_web = search_ddg.search_ddg(termo)
                await gerenciar_memoria_pesquisa(client_llm, termo, resultados_web)
                
                if not precisa_nova_resposta:
                    msg_limpa = re.sub(r"[\[<]PESQUISAR:.*?[\]>]", "", resposta_inicial, flags=re.IGNORECASE).strip()
                    if msg_limpa:
                        historico_api.append({"role": "assistant", "content": msg_limpa})
                
                historico_api.append({"role": "user", "content": f"[SISTEMA DE BUSCA]: Resultados encontrados para '{termo}':\n{resultados_web}"})
                precisa_nova_resposta = True

        if precisa_nova_resposta:
            historico_api.append({"role": "user", "content": "Agora dê a sua resposta definitiva ao usuário incorporando o que aconteceu. REGRA ABSOLUTA: Fale com a sua personalidade de forma fluida. É PROIBIDO FAZER ROLEPLAY DE AÇÕES (NUNCA use asteriscos). NUNCA use a palavra 'pesquisa', não diga que buscou na web, e não mencione tags ou comandos. Aja simplesmente como se você tivesse lembrado dessa informação de cabeça."})
            
            kwargs_final = {
                "model": id_modelo,
                "messages": historico_api,
                "temperature": 0.7
            } 
            if extra: kwargs_final["extra_body"] = extra
            
            res_final = await asyncio.to_thread(lambda: cliente_ativo.chat.completions.create(**kwargs_final))
            resposta_final = res_final.choices[0].message.content
            resposta_final = re.sub(r'<think>.*?</think>', '', resposta_final, flags=re.IGNORECASE | re.DOTALL).strip()

       # 🔥 CAÇADOR DE EMOÇÕES ALINHADO 🔥
        emocao_match = re.search(r"\[(NORMAL|RIR|RAIVA|TRISTE|SURPRESA)\]", resposta_final)
        if emocao_match:
            emocao_tag = emocao_match.group(1)
            try:
                requests.post(f"http://127.0.0.1:8765/emotion/{emocao_tag}", timeout=0.5)
                print(f"🎭 [SISTEMA] Emoção {emocao_tag} ativada no VTube Studio!")
            except requests.exceptions.RequestException:
                pass
            resposta_final = re.sub(r"\[(NORMAL|RIR|RAIVA|TRISTE|SURPRESA)\]", "", resposta_final).strip()

        # 🧹 LIMPEZA FINAL
        resposta_final = re.sub(r'<[^>]+>', '', resposta_final).strip()

        # FALLBACK PARA RESPOSTAS VAZIAS
        if not resposta_final:
            historico_fallback = [{"role": "system", "content": f"Aja como {nome_ai}, usando a sua personalidade sarcástica. Fale uma frase curta confirmando que executou o comando. Não use tags."}]
            try:
                res_fall = await asyncio.to_thread(lambda: cliente_ativo.chat.completions.create(
                    model=id_modelo, messages=historico_fallback, temperature=0.9, extra_body=extra
                ))
                resposta_final = res_fall.choices[0].message.content
                resposta_final = re.sub(r'<think>.*?</think>', '', resposta_final, flags=re.IGNORECASE | re.DOTALL)
                resposta_final = re.sub(r'<[^>]+>', '', resposta_final).strip()
            except:
                resposta_final = "Feito."

        print(f"{nome_ai}: {resposta_final}")
        await gerenciar_e_salvar_memoria(client_llm, nome_ai, resposta_final)
        # --- LÓGICA DE SELEÇÃO DE VOZ VIA PAINEL ---
        estado_ui = ler_estado_ui() # Lê o brain.json atualizado pelo painel
        
        # Verifica se você escolheu 'Microsoft' ou 'ElevenLabs' no painel
        # (Se não houver escolha, ele usa ElevenLabs por padrão)
        provedor_voz = estado_ui.get("modelos_ativos", {}).get("tts", "ElevenLabs")

        # --- LÓGICA DE SELEÇÃO DE VOZ VIA PAINEL ---
        estado_ui = ler_estado_ui() 
        provedor_voz = estado_ui.get("modelos_ativos", {}).get("tts", "ElevenLabs")

        if provedor_voz == "Microsoft":
            await microsoft_speak(resposta_final)
        else:
            if ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID:
                await elevenlabs_speak(resposta_final)
            else:
                print("❌ Falha na voz: Chaves faltando no .env. Usando Microsoft como reserva...")
                await microsoft_speak(resposta_final)

        return resposta_final 
        
    except Exception as e:
        print(f" Erro na API LLM ({provedor_local}): {e}")
        return "Deu erro no meu cérebro. Olha o terminal."
#endregion
# ======================================================
# region 🎤 MODOS DE OPERAÇÃO
# ======================================================
async def run_modo_continuo(client_nvidia, client_llm, client_vision, sys_prompt, voice_filter, api_key_whisper, nome_ai, usuario_nome, launcher):
    print("\n[SISTEMA] 🎙️ MODO CONTÍNUO INICIADO - Escutando...")
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=512)
    frames, is_recording, silence_timer = [], False, 0

    while True:
        # LÓGICA DO MOTOR SPA: Se o usuário clicar "Parar de Ouvir" no painel, ele sai do loop instantaneamente!
        estado_ui = ler_estado_ui()
        if not estado_ui.get("microfone_aberto", False) or estado_ui.get("modo_operacao_atual") != "Contínuo":
            print("\n[SISTEMA] ⏹️ MODO CONTÍNUO INTERROMPIDO PELO PAINEL.")
            break

        data = stream.read(512, exception_on_overflow=False)
        if voice_filter.is_human_voice(data):
            if not is_recording: is_recording = True
            frames.append(data); silence_timer = 0
        elif is_recording:
            silence_timer += 1
            if silence_timer > 35: 
                is_recording = False
                texto = await whisper_transcription(frames, api_key_whisper)
                frames = []
                if texto: 
                    texto_limpo = texto.strip().lower()
                    alucinacoes = ["sônia ruberti", "sonia ruberti", "legendas", "obrigado por assistir", "inscreva-se no canal", "amara.org", "obrigado.", "obrigada", "obrigado"]
                    
                    if len(texto_limpo) <= 2 or any(fantasma in texto_limpo for fantasma in alucinacoes):
                        continue 
                    
                    _, _, _, trigger_ativo, _, _, *_ = carregar_brain()
                    if trigger_ativo:
                        if requer_despertar(texto, nome_ai): 
                            await processar_ia(client_nvidia, client_llm, client_vision, sys_prompt, texto, nome_ai, usuario_nome, launcher, modo_chat=False)
                    else:
                        await processar_ia(client_nvidia, client_llm, client_vision, sys_prompt, texto, nome_ai, usuario_nome, launcher, modo_chat=False)
        await asyncio.sleep(0.01)
    
    stream.stop_stream(); stream.close(); p.terminate()

async def run_modo_click(client_nvidia, client_llm, client_vision, sys_prompt, api_key_whisper, nome_ai, usuario_nome, launcher):
    print("\n[SISTEMA] ⌨️ MODO PRESS TO TALK INICIADO - Pressione R-SHIFT para falar.")
    RATE = 16000
    CHUNK = 1024

    while True:
        estado_ui = ler_estado_ui()
        if not estado_ui.get("microfone_aberto", False) or estado_ui.get("modo_operacao_atual") != "Press to Talk":
            print("\n[SISTEMA] ⏹️ MODO PRESS TO TALK INTERROMPIDO PELO PAINEL.")
            break

        if keyboard.is_pressed('right shift'):
            play_beep("inicio")
            while keyboard.is_pressed('right shift'): await asyncio.sleep(0.01)

            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
            frames = []
            
            print(" A gravar... (Clica R-SHIFT para enviar)")
            while True:
                estado_ui_mid = ler_estado_ui()
                if not estado_ui_mid.get("microfone_aberto", False): break

                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                
                if keyboard.is_pressed('right shift'):
                    play_beep("fim")
                    break
                await asyncio.sleep(0.001)
                
            stream.stop_stream(); stream.close(); p.terminate()
            print(" A enviar para a IA...")
            while keyboard.is_pressed('right shift'): await asyncio.sleep(0.01)

            texto = await whisper_transcription(frames, api_key_whisper)
            if texto: 
                texto_limpo = texto.strip().lower()
                alucinacoes = ["sônia ruberti", "sonia ruberti", "legendas", "obrigado por assistir", "inscreva-se no canal", "amara.org", "obrigado.", "obrigada", "obrigado"]
                
                if len(texto_limpo) <= 2 or any(fantasma in texto_limpo for fantasma in alucinacoes):
                    continue 
                
                _, _, _, trigger_ativo, _, _, *_ = carregar_brain()
                if trigger_ativo:
                    if nome_ai.lower() in texto.lower(): 
                        await processar_ia(client_nvidia, client_llm, client_vision, sys_prompt, texto, nome_ai, usuario_nome, launcher, modo_chat=False)
                else:
                    await processar_ia(client_nvidia, client_llm, client_vision, sys_prompt, texto, nome_ai, usuario_nome, launcher, modo_chat=False)

        await asyncio.sleep(0.05)

async def run_modo_chamada(client_nvidia, client_llm, client_vision, sys_prompt, voice_filter, api_key_whisper, nome_ai, usuario_nome, launcher):
    print("\n[SISTEMA] 🛎️ MODO CHAMADA INICIADO - Responderei apenas se disser meu nome.")
    # Salva temporariamente o status do gatilho para forçar ativação local
    salvar_gatilho_brain(True) 
    
    # Roda idêntico ao contínuo, mas o gatilho está forçado como True
    await run_modo_continuo(client_nvidia, client_llm, client_vision, sys_prompt, voice_filter, api_key_whisper, nome_ai, usuario_nome, launcher)

#endregion
# ======================================================
#region 🚀 MAIN AUTOMÁTICO (O MOTOR SPA DO RUN.PY)
# ======================================================
async def main():
    global VISAO_HABILITADA
    brain_raw, sys_prompt, nome_ai, trigger, discord_active, modelos, vtuber_ativo = carregar_brain()

    print(f"🎨 Iniciando Interface Arcana SPA em segundo plano...")
    gui_thread = threading.Thread(target=RemGUI.iniciar_gui_loop, args=(nome_ai,), daemon=True)
    gui_thread.start()

    keyboard.add_hotkey('f4', RemGUI.toggle)
    keyboard.on_press_key('f2', toggle_visao)
    keyboard.on_press_key('f3', toggle_gatilho) 

    # Inicia leitor de terminal em background para o "Modo Chat" não travar o sistema
    terminal_thread = threading.Thread(target=thread_leitor_terminal, daemon=True)
    terminal_thread.start()

    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    GROQ_API_KEY_LLM = os.getenv("GROQ_API_KEY_LLM")
    GROQ_API_KEY_VISION = os.getenv("GROQ_API_KEY_VISION")

    if not GROQ_API_KEY_LLM or not GROQ_API_KEY_VISION or not NVIDIA_API_KEY:
        print(" ERRO FATAL: Chaves da Groq ou NVIDIA não encontradas.")
        return
    
    if vtuber_ativo:
        print("🎭 Iniciando módulo VTuber Overlay...")
        try:
            subprocess.Popen([sys.executable, "Arcana/Net/vtuber_overlay.py"])
        except Exception as e:
            print(f"❌ Erro ao iniciar VTuber: {e}")

    client_nvidia = OpenAI(api_key=NVIDIA_API_KEY, base_url="https://integrate.api.nvidia.com/v1")
    client_llm = Groq(api_key=GROQ_API_KEY_LLM)
    client_vision = Groq(api_key=GROQ_API_KEY_VISION)
    
    voice_filter = LocalVoiceFilter()
    relacionamentos_main = brain_raw.get('relationships', {})
    usuario_nome = list(relacionamentos_main.keys())[0] if relacionamentos_main else "Usuário"
    
    launcher = AppLauncher()
    carregar_memoria()

    discord_thread = None
    if discord_active:
        print("\n🌐 Integrando Shogun ao Discord...")
        discord_thread = threading.Thread(
            target=run_discord_thread, 
            args=(client_nvidia, client_llm, client_vision, sys_prompt, nome_ai, usuario_nome, launcher, processar_ia), 
            daemon=True
        )
        discord_thread.start()

    print(f"\n✅ [SISTEMA] Motor Principal Conectado à Interface Arcana!")
    print("O controle agora é totalmente via Painel. (Para modo chat, basta digitar aqui no terminal e dar Enter)\n")

    # 🔥 O NOVO LOOP PRINCIPAL: OTIMIZADO E SEM CONFLITO
    while True:
        await asyncio.sleep(0.3) # Respiro para o processador
        estado_ui = ler_estado_ui()
        modo_atual = estado_ui.get("modo_operacao_atual", "Chat")
        mic_aberto = estado_ui.get("microfone_aberto", False)
        
        VISAO_HABILITADA = estado_ui.get("visao_computacional_ativa", False)

        if mic_aberto:
            # BLOQUEIO DE CONFLITO: Só entra no modo se não houver erro de nome
            if modo_atual == "Contínuo":
                await run_modo_continuo(client_nvidia, client_llm, client_vision, sys_prompt, voice_filter, GROQ_API_KEY_LLM, nome_ai, usuario_nome, launcher)
            elif modo_atual == "Press to Talk":
                await run_modo_click(client_nvidia, client_llm, client_vision, sys_prompt, GROQ_API_KEY_LLM, nome_ai, usuario_nome, launcher)
            elif modo_atual == "Responder Quando Chamada":
                await run_modo_chamada(client_nvidia, client_llm, client_vision, sys_prompt, voice_filter, GROQ_API_KEY_LLM, nome_ai, usuario_nome, launcher)
            
            # Após sair de um modo de áudio, desliga o mic no cérebro para não reentrar em loop
            try:
                estado_ui["microfone_aberto"] = False
                with open(BRAIN_FILE, 'w', encoding='utf-8') as f: json.dump(estado_ui, f, indent=4)
            except: pass

        else:
            if chat_terminal_queue:
                msg_chat = chat_terminal_queue.pop(0)
                await processar_ia(client_nvidia, client_llm, client_vision, sys_prompt, msg_chat, nome_ai, usuario_nome, launcher, modo_chat=True)

            # Verifica o Discord
            discord_painel = estado_ui.get("discord_active", False)
            if discord_painel and (discord_thread is None or not discord_thread.is_alive()):
                discord_thread = threading.Thread(
                    target=run_discord_thread, 
                    args=(client_nvidia, client_llm, client_vision, sys_prompt, nome_ai, usuario_nome, launcher, processar_ia), 
                    daemon=True
                )
                discord_thread.start()

            await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
#endregion
# ============//======================//================