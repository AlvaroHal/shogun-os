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

# ======================================================
# 🎨 MÓDULO DE GERAÇÃO DE ARTE (POLLINATIONS + TRADUTOR GROQ)
# ======================================================
class ShogunArtModule:
    def __init__(self, base_path="D:/Shogun/Imagens"):
        self.base_path = base_path
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)
            print(f"🎨 Pasta de artes criada: {self.base_path}")

    def gerar_e_salvar(self, prompt):
        print(f"🎨 Shogun (Motor Pollinations em Inglês) está pintando: {prompt}...")
        url_segura = prompt.replace(' ', '%20')
        url = f"https://image.pollinations.ai/prompt/{url_segura}?width=1024&height=1024&nologo=true"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                nome_arquivo = f"shogun_art_{timestamp}.png"
                caminho_completo = os.path.join(self.base_path, nome_arquivo)
                
                with open(caminho_completo, "wb") as f:
                    f.write(response.content)
                return caminho_completo
        except Exception as e:
            print(f"❌ Erro ao pintar: {e}")
        return None

shogun_artista = ShogunArtModule()

# ======================================================
# 🌐 CONFIGURAÇÃO DO BOT
# ======================================================
def setup_discord_bot(client_nvidia, client_llm, client_vision, sys_prompt, nome_ai, usuario_nome, launcher, processar_ia_func):
    
    # 🔥 ESCUDO ATIVADO: CHAVE ESCONDIDA AQUI 🔥
    TOKEN = os.getenv("DISCORD_TOKEN") 
    
    if not TOKEN:
        print("❌ ERRO CRÍTICO: DISCORD_TOKEN não encontrado no arquivo .env!")
        return

    intents = discord.Intents.all() 
    bot = commands.Bot(command_prefix='!', intents=intents)

    url_musica_ativa = None
    tempo_inicio_musica = 0
    segundos_decorridos = 0

    async def tocar_audio_na_call(message, deve_retomar=True):
        nonlocal url_musica_ativa, tempo_inicio_musica, segundos_decorridos
        arquivo_audio = os.path.abspath("vocal_.mp3")
        await asyncio.sleep(1.0) 

        vc = message.guild.voice_client
        if not vc or not vc.is_connected(): return

        if os.path.exists(arquivo_audio):
            if vc.is_playing() and tempo_inicio_musica > 0:
                segundos_decorridos += (time.time() - tempo_inicio_musica)
                vc.stop()

            try:
                ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
                source = discord.FFmpegPCMAudio(arquivo_audio, executable=ffmpeg_path)
                vc.play(source)
                print(f"🎤 [VOZ] Shogun falando...")

                while vc.is_playing(): await asyncio.sleep(0.5)
                
                if deve_retomar and url_musica_ativa and vc.is_connected():
                    print(f"⏩ [RETOMADA] Voltando rádio ({int(segundos_decorridos)}s)...")
                    await tocar_youtube(vc, url_musica_ativa, seek=int(segundos_decorridos))
            except Exception as e:
                print(f"❌ Erro na voz: {e}")

    async def tocar_youtube(vc, termo_ou_url, seek=0):
        nonlocal url_musica_ativa, tempo_inicio_musica, segundos_decorridos
        
        # 🔥 CORREÇÃO PRINCIPAL: TRATAMENTO ABSOLUTO DOS COMANDOS
        comando = termo_ou_url.upper().strip()
        # Limpa caracteres extras que possam ter vindo junto (ex: <STOP)
        comando = re.sub(r'[^A-Z]', '', comando) 

        if comando in ["PAUSE", "PAUSAR"]:
            if vc.is_playing():
                vc.pause()
                print(f"⏸️ [COMANDO] Rádio pausada via IA.")
            return # Aborta a função, não vai pesquisar no YouTube!
            
        elif comando in ["RESUME", "VOLTAR", "RETOMAR"]:
            if vc.is_paused():
                vc.resume()
                print(f"▶️ [COMANDO] Rádio retomada via IA.")
            return

        elif comando in ["STOP", "PARAR", "CALABOCA"]:
            if vc.is_playing() or vc.is_paused():
                vc.stop()
                url_musica_ativa = None # Limpa a memória para não voltar a tocar
                print(f"⏹️ [COMANDO] Rádio desligada via IA.")
            return # Aborta a função!

        # 🔎 LOGICA DE BUSCA NORMAL
        if not termo_ou_url.startswith("http"):
            query = f"ytsearch1:{termo_ou_url}"
            print(f"🔍 [DJ] Pesquisando: {termo_ou_url}")
        else:
            query = termo_ou_url.replace("music.youtube.com", "www.youtube.com")
            url_musica_ativa = query
        
        tempo_formatado = time.strftime('%H:%M:%S', time.gmtime(seek))
        caminho_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        caminho_cookies = os.path.join(caminho_base, "cookies.txt")

        YTDL_OPTIONS = {
            'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'no_warnings': True,
            'cookiefile': caminho_cookies if os.path.exists(caminho_cookies) else None,
            'nocheckcertificate': True,
        }
        
        FFMPEG_OPTIONS = {
            'before_options': f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {tempo_formatado}',
            'options': '-vn'
        }

        try:
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                info = await bot.loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
                if 'entries' in info: info = info['entries'][0]
                stream_url = info.get('url')

            if not stream_url: return

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

    @bot.event
    async def on_ready():
        print(f'\n✅ [SISTEMA] Shogun Rádio v1.8 ')

    @bot.event
    async def on_message(message):
        if message.author == bot.user: return
        
        # ======================================================
        # 🔥 GATILHO DA SHOGUN PINTORA (COM TRADUTOR AUTOMÁTICO)
        # ======================================================
        texto_msg = message.content.lower()
        if texto_msg.startswith("shogun gera") or texto_msg.startswith("shogun desenha") or texto_msg.startswith("shogun cria"):
            prompt_pt = re.sub(r'^shogun (gera|desenha|cria)\s+', '', texto_msg).strip()
            
            if prompt_pt:
                aviso = await message.channel.send(f"🎨 Segura a ansiedade aí. Traduzindo do seu neandertalês e desenhando: **{prompt_pt}**...")
                
                # 🧠 Tradutor Ninja usando o motor Groq que já está conectado
                try:
                    res_traducao = await asyncio.to_thread(
                        lambda: client_llm.chat.completions.create(
                            model="llama-3.1-8b-instant", # Modelo hiper leve e rápido
                            messages=[
                                {"role": "system", "content": "You translate Portuguese image generation prompts into English keywords. ONLY output the English text, no explanations, no quotes."},
                                {"role": "user", "content": prompt_pt}
                            ],
                            temperature=0.3
                        )
                    )
                    prompt_en = res_traducao.choices[0].message.content.strip()
                    print(f"🔤 [TRADUÇÃO DA ARTE] {prompt_pt} -> {prompt_en}")
                except Exception as e:
                    print(f"❌ Falha no tradutor: {e}")
                    prompt_en = prompt_pt # Fallback: se a API falhar, vai em PT mesmo
                
                # Chama o gerador em background para não congelar a Shogun
                caminho_imagem = await asyncio.to_thread(shogun_artista.gerar_e_salvar, prompt_en)
                
                if caminho_imagem:
                    arquivo = discord.File(caminho_imagem)
                    await message.channel.send(content="🖼️ Tá aí. Apreciem a minha arte e não reclamem:", file=arquivo)
                    await aviso.delete() 
                else:
                    await aviso.edit(content="❌ Deu ruim. Alguém bebeu a água do meu pincel.")
            else:
                await message.channel.send("Gerar o quê? Esqueceu de falar, cérebro de Cheetos?")
                
            return # Interrompe a execução aqui para ela não tentar ler isso como um chat de texto!
        
        # ======================================================
        # CHAT NORMAL DA IA E MÚSICA (CÓDIGO ORIGINAL)
        # ======================================================
        foi_marcada = bot.user.mentioned_in(message) or (nome_ai.lower() in message.content.lower())
        
        if foi_marcada or isinstance(message.channel, discord.DMChannel):
            conteudo = re.sub(r'<@&?\d+>', '', message.content).strip()
            async with message.channel.typing():
                resposta = await processar_ia_func(client_nvidia, client_llm, client_vision, sys_prompt, conteudo, nome_ai, usuario_nome, launcher, modo_chat=True)
                
                if resposta:
                    print(f" DEBUG RAW: {resposta}")
                    await message.reply(re.sub(r'<[^>]+>', '', resposta).strip())
                    
                    vc = message.guild.voice_client
                    if vc and vc.is_connected():
                        # REGEX APRIMORADA PARA PEGAR COMANDOS EXATOS
                        match = re.search(r'<(?:PLAY:)?\s*(.*?)\s*>', resposta, re.IGNORECASE | re.DOTALL)
                        musica_url = match.group(1).strip() if match else None

                        if not musica_url:
                            try:
                                caminho_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                brain_path = next(os.path.join(r, f) for r, d, fs in os.walk(caminho_base) for f in fs if f.lower() == "brain.json")
                                with open(brain_path, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                    pending = data.get("pending_music", "")
                                    if pending:
                                        musica_url = re.sub(r'<PLAY:|>', '', pending).strip()
                                        data["pending_music"] = ""
                                        with open(brain_path, "w", encoding="utf-8") as f_out: json.dump(data, f_out, indent=4)
                            except: pass

                        if musica_url:
                            comando_puro = re.sub(r'[^A-Za-z]', '', musica_url.upper())
                            
                            if comando_puro not in ["PAUSE", "STOP", "RESUME", "PARAR", "VOLTAR"]:
                                nonlocal segundos_decorridos
                                segundos_decorridos = 0 
                                await tocar_audio_na_call(message, deve_retomar=False)
                            else:
                                await tocar_audio_na_call(message, deve_retomar=False)
                            
                            await tocar_youtube(vc, musica_url)
                        else:
                            await tocar_audio_na_call(message, deve_retomar=True)

        await bot.process_commands(message)

    @bot.command()
    async def vem(ctx):
        if not ctx.author.voice: return await ctx.send("Entra na call.")
        canal = ctx.author.voice.channel
        if ctx.voice_client: await ctx.voice_client.move_to(canal)
        else: await canal.connect(timeout=60.0, self_deaf=True)
        await ctx.send("DJ na área.")

    @bot.command()
    async def vaza(ctx):
        if ctx.voice_client: await ctx.voice_client.disconnect()

    @bot.command()
    async def stop(ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏹️ Música parada.")
            
    @bot.command()
    async def pause(ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ Música pausada.")

    bot.run(TOKEN)

def run_discord_thread(*args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    setup_discord_bot(*args)