import customtkinter as ctk
import tkinter as tk
import os
import re
import json
import psutil
import subprocess
import urllib.parse
import webbrowser
import random

# ==========================================
# CONFIGURAÇÕES E CORES
# ==========================================
BRAIN_FILE = "Arcana/armazen/brain.json"
ENV_FILE = ".env"

BG_DARK = "#05080E"        
PANEL_BG = "#0B111A"       
SIDEBAR_BG = "#060910"     
ACCENT = "#00D2FF"         
ACCENT_DIM = "#005566"     
TEXT_LIGHT = "#E2E8F0"     
TEXT_DIM = "#64748B"       

# ==========================================
# CÉREBRO LÓGICO: APP LAUNCHER
# ==========================================
class AppLauncher:
    def __init__(self, output_callback=None):
        self.output_callback = output_callback
        self.enabled = True
      
        self.apps = {
            "Minecraft": {
                "target": "minecraft:",
                "aliases": ["jogo do bloco", "jogo quadrado", "farm", "mine"],
                "process_names": ["Minecraft.Windows.exe"],
                "allow_multiple": False
            },
            "Cyberpunk 2077": {
                "target": '"" "D:\\SteamLibrary\\steamapps\\common\\Cyberpunk 2077\\bin\\x64\\Cyberpunk2077.exe"',
                "aliases": ["2077", "cyberpunk", "night city", "dar uns tiros"],
                "process_names": ["Cyberpunk2077.exe"],
                "allow_multiple": False
            },
            "league of legends": {
                "target": "D:/Riot Games/Riot Client/RiotClientServices.exe",
                "aliases": ["lol", "lolzinho", "league", "league of legends"],
                "process_names": ["RiotClientServices.exe", "LeagueClient.exe"],
                "allow_multiple": False
            },
            "bloco de notas": {
                "target": "notepad",
                "aliases": ["anotações", "notas", "editor de texto", "notepad", "escrever"],
                "process_names": ["notepad.exe"],
                "allow_multiple": True
            },
            "youtube": {
                "target": "https://www.youtube.com",
                "aliases": ["vídeos", "ver vídeo", "youtube", "assistir algo"],
                "process_names": [], 
                "allow_multiple": True
            },
            "navegador": {
                "target": "https://www.google.com",
                "aliases": ["google", "pesquisar", "web", "internet", "browser", "chrome"],
                "process_names": ["chrome.exe", "msedge.exe", "firefox.exe"],
                "allow_multiple": True
            }
        }

        # 🔥 LENDO O HD DA ARCANA PARA LEMBRAR DOS APPS 🔥
    # Coloque isso dentro do __init__ da sua classe AppLauncher
    def load_custom_apps(self):
        try:
            with open(BRAIN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                custom_apps = data.get("custom_apps", {})
                self.apps.update(custom_apps)
        except:
            pass

    def log(self, message):
        if self.output_callback:
            self.output_callback(message)
        else:
            print(message)

    def find_app(self, command):
        if not command: return None, None
        command = command.lower().strip()
        for app_name, app_data in self.apps.items():
            if command == app_name.lower() or command in [a.lower() for a in app_data.get('aliases', [])]:
                return app_name, app_data['target']
        return None, None

    def is_app_running(self, app_name):
        if app_name not in self.apps: return False
        process_names = self.apps[app_name].get('process_names', [])
        if not process_names: return False 
        import psutil
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name'].lower()
                for target_name in process_names:
                    if target_name.lower() in proc_name:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def close_app(self, app_name):
        import psutil
        try:
            closed = False
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower()
                    for target_name in self.apps[app_name].get('process_names', []):
                        if target_name.lower() in proc_name:
                            proc.terminate()
                            closed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return closed
        except Exception as e:
            self.log(f"❌ Erro ao fechar {app_name}: {e}")
            return False

    def open_app_cmd(self, app_name, target):
        import os
        import subprocess
        try:
            # Limpeza total de aspas para não bugar o Windows
            target_clean = target.replace('"', '').replace("'", "").strip()
            
            # 🚀 O SEGREDO: os.startfile ignora o CMD e abre caminhos com espaços direto
            if os.path.exists(target_clean):
                os.startfile(target_clean)
                self.log(f"🚀 [os.startfile] Aberto com sucesso: {target_clean}")
                return True
            else:
                # Se não for um caminho (ex: apenas 'notepad'), tenta o comando start padrão
                subprocess.Popen(f'start "" "{target_clean}"', shell=True)
                return True
        except Exception as e:
            self.log(f"❌ Erro REAL ao abrir {app_name}: {str(e)}")
            return False

    def process_llm_tag(self, llm_response):
        if not self.enabled: return None
        import os
        import subprocess
        import re

        resultados = []

        # ⚙️ MÓDULO 1: COMANDOS NATIVOS DO WINDOWS (<CMD:...>)
        cmd_tags = re.findall(r'<CMD:\s*([^>]+)>', llm_response, re.IGNORECASE)
        for cmd in cmd_tags:
            cmd = cmd.strip()
            self.log(f"\n⚙️ Comando Nativo Windows -> Alvo: {cmd}")
            try:
                cmd_clean = cmd.replace('"', '').replace("'", "").strip()
                # Se for um caminho de arquivo com espaço, usamos startfile para não dar erro de "D:\Riot"
                if os.path.exists(cmd_clean):
                    os.startfile(cmd_clean)
                else:
                    subprocess.Popen(f'start "" "{cmd_clean}"', shell=True)
                
                msg = f"✅ Comando executado: {cmd}"
                self.log(msg)
                resultados.append(msg)
            except Exception as e:
                erro = f"❌ Erro ao abrir no Windows: {e}"
                self.log(erro)
                resultados.append(erro)

        # ⚙️ MÓDULO 2: APPS DO PAINEL / DICIONÁRIO (<APP:...>)
        tags_encontradas = re.findall(r'<APP:\s*(abrir|fechar)\s*:\s*([^>:]+)(?::([^>]*))?>', llm_response, re.IGNORECASE)
        for match in tags_encontradas:
            action, app_raw, param = match[0].lower(), match[1].lower(), match[2]
            app_name, target = self.find_app(app_raw)

            if not app_name:
                if action == "abrir": self.open_app_cmd(app_raw, app_raw)
                continue

            if action == "abrir":
                if self.is_app_running(app_name) and not self.apps[app_name].get('allow_multiple', True):
                    resultados.append(f"ℹ️ '{app_name}' já está aberto.")
                else:
                    self.open_app_cmd(app_name, target)
                    resultados.append(f"✅ '{app_name}' aberto.")
            elif action == "fechar":
                self.close_app(app_name)
                resultados.append(f"✅ '{app_name}' fechado.")

        return "\n".join(resultados) if resultados else None

        # ⚙️ MÓDULO 2: APPS DO PAINEL E FALLBACK (<APP:...>)
        tags_encontradas = re.findall(r'<APP:\s*(abrir|fechar)\s*:\s*([^>:]+)(?::([^>]*))?>', llm_response, re.IGNORECASE)
        
        for match in tags_encontradas:
            action = match[0].lower().strip()
            app_raw = match[1].lower().strip()
            param = match[2].strip() if match[2] and match[2].strip() else None

            self.log(f"\n⚙️ Comando IA -> Ação: {action.upper()} | Alvo: {app_raw}")

            app_name, target = self.find_app(app_raw)
            
            # MODO CAÇADORA: Se não achar no dicionário, tenta abrir direto pelo Windows
            if not app_name:
                self.log(f"⚠️ '{app_raw}' não tá no dicionário! Tentando execução direta...")
                if action == "abrir":
                    if self.open_app_cmd(app_raw, app_raw):
                        msg = f"✅ Tentativa de abertura direta enviada: {app_raw}"
                        resultados.append(msg)
                    else:
                        resultados.append(f"❌ Falha na execução direta de '{app_raw}'.")
                continue

            is_running = self.is_app_running(app_name)

            if action == "abrir":
                if app_name.lower() in ["youtube", "navegador"]:
                    import webbrowser, urllib.parse
                    base_url = "https://www.youtube.com/results?search_query=" if app_name == "youtube" else "https://www.google.com/search?q="
                    target_url = f"{base_url}{urllib.parse.quote_plus(param)}" if param else target
                    webbrowser.open(target_url)
                    msg = f"✅ {app_name.capitalize()} aberto."
                    self.log(msg)
                    resultados.append(msg)
                else:
                    if is_running and not self.apps[app_name].get('allow_multiple', True):
                        self.log(f"ℹ️ '{app_name}' já está aberto.")
                        resultados.append(f"ℹ️ '{app_name}' já está aberto.")
                    elif self.open_app_cmd(app_name, target):
                        msg = f"✅ '{app_name}' aberto com sucesso."
                        self.log(msg)
                        resultados.append(msg)
                    else:
                        resultados.append(f"❌ Erro ao abrir '{app_name}'.")

            elif action == "fechar":
                if not is_running:
                    self.log(f"ℹ️ '{app_name}' já está fechado.")
                    resultados.append(f"ℹ️ '{app_name}' já está fechado.")
                elif self.close_app(app_name):
                    msg = f"✅ '{app_name}' encerrado."
                    self.log(msg)
                    resultados.append(msg)
                else:
                    resultados.append(f"❌ Erro ao fechar '{app_name}'.")

        return "\n".join(resultados) if resultados else None

        # ⚙️ MÓDULO 2: APPS DO PAINEL E FALLBACK (<APP:...>)
        tags_encontradas = re.findall(r'<APP:\s*(abrir|fechar)\s*:\s*([^>:]+)(?::([^>]*))?>', llm_response, re.IGNORECASE)
        
        for match in tags_encontradas:
            action = match[0].lower().strip()
            app_raw = match[1].lower().strip()
            param = match[2].strip() if match[2] and match[2].strip() else None

            self.log(f"\n⚙️ Comando IA -> Ação: {action.upper()} | Alvo: {app_raw} | Param: {param}")

            app_name, target = self.find_app(app_raw)
            if not app_name:
                # 🔥 A MÁGICA ACONTECE AQUI: O MODO CAÇADORA 🔥
                self.log(f"⚠️ '{app_raw}' não tá no dicionário! Jogando pro Windows se virar...")
                if action == "abrir":
                    try:
                        subprocess.Popen(f'start "" "{app_raw}"', shell=True)
                        msg = f"✅ Ordem de execução enviada ao Windows: {app_raw}"
                        self.log(msg)
                        resultados.append(msg)
                    except Exception as e:
                        erro_msg = f"❌ O Windows também não achou '{app_raw}'."
                        self.log(erro_msg)
                        resultados.append(erro_msg)
                continue

            is_running = self.is_app_running(app_name)

            if action == "abrir":
                if app_name.lower() in ["youtube", "navegador"]:
                    base_url = "https://www.youtube.com/results?search_query=" if app_name == "youtube" else "https://www.google.com/search?q="
                    target_url = f"{base_url}{urllib.parse.quote_plus(param)}" if param else self.apps[app_name]['target']
                    webbrowser.open(target_url)
                    msg = f"✅ {app_name.capitalize()} aberto."
                    self.log(msg)
                    resultados.append(msg)
                else:
                    if is_running and not self.apps[app_name].get('allow_multiple', True):
                        info_msg = f"ℹ️ '{app_name}' já está aberto."
                        self.log(info_msg)
                        resultados.append(info_msg)
                    elif self.open_app_cmd(app_name, target):
                        msg = f"✅ '{app_name}' aberto."
                        self.log(msg)
                        resultados.append(msg)
                    else:
                        resultados.append(f"❌ Erro ao abrir '{app_name}'.")

            elif action == "fechar":
                if not is_running:
                    msg = f"ℹ️ '{app_name}' já fechado."
                    self.log(msg)
                    resultados.append(msg)
                elif self.close_app(app_name):
                    msg = f"✅ '{app_name}' encerrado."
                    self.log(msg)
                    resultados.append(msg)
                else:
                    resultados.append(f"❌ Erro ao fechar '{app_name}'.")

        return "\n".join(resultados) if resultados else None

# ==========================================
# INTERFACE GRÁFICA: O MOTOR SPA
# ==========================================
class ArcanaDashboard(ctk.CTk):
    def __init__(self, nome_ai="IA"):
        super().__init__()

        # 🔥 CORREÇÃO CRÍTICA: O dicionário deve nascer ANTES de qualquer desenho de tela
        self.bars_refs = {} 

        self.title(f"SISTEMA OPERACIONAL SHOGUN 2026 - {nome_ai}")
        self.geometry("1100x650")
        self.minsize(900, 550)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=BG_DARK)

        self.log_history = [] 
        self.launcher = AppLauncher(output_callback=self.add_to_log)

        # --- CARREGA ESTADOS DO CÉREBRO ---
        try:
            with open(BRAIN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.modo_selecionado = data.get("modo_operacao_atual", "Chat")
                self.visao_ligada = data.get("visao_computacional_ativa", False)
                self.microfone_aberto = data.get("microfone_aberto", False)
        except:
            self.modo_selecionado = "Chat"
            self.visao_ligada = False
            self.microfone_aberto = False

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.menu_btns = {}
        self.menu_indicators = {}
        
        self.create_sidebar()
        
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=25, pady=20)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.create_header()
        
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew")

        # Agora o switch_view chamará o render_aura_panel e encontrará o bars_refs vazio e pronto
        self.switch_view("Modo de Uso")

        # ======================================================
        # 🔥 MOTOR DE MONITORAMENTO REAL-TIME (INÍCIO DA THREAD)
        # ======================================================
        import threading
        threading.Thread(target=self.loop_sistema_realtime, daemon=True).start()

    # ======================================================
    # 🔥 FUNÇÕES DE LÓGICA DO SISTEMA
    # ======================================================
    def loop_sistema_realtime(self):
        """Monitora o hardware (CPU/RAM) e envia para a interface"""
        import psutil
        import time
        while True:
            try:
                # Captura os dados reais do Windows
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                
                # Manda atualizar os widgets na thread principal da GUI
                if self.winfo_exists():
                    self.after(0, lambda c=cpu, r=ram: self.atualizar_visual_recursos(c, r))
                
                time.sleep(1) # Atualiza a cada 1 segundo para ser fluido
            except:
                time.sleep(5)

    def atualizar_visual_recursos(self, cpu_val, ram_val):
        """Atualiza os textos de porcentagem e as alturas das barrinhas"""
        import random
        
        # Atualiza a seção de CPU
        if "CPU USAGE" in self.bars_refs:
            lbl_cpu = self.bars_refs["CPU USAGE"]['label']
            # 🔥 TRAVA DE SEGURANÇA: Só atualiza se o texto ainda existir na tela
            if lbl_cpu.winfo_exists():
                lbl_cpu.configure(text=f"{cpu_val}%")
                for bar in self.bars_refs["CPU USAGE"]['visuals']:
                    if bar.winfo_exists(): # Protege as barrinhas também
                        h = random.randint(3, 18) if cpu_val > 10 else random.randint(2, 6)
                        cor = "#00D2FF" if cpu_val < 70 else "#FF3366"
                        bar.configure(height=h, fg_color=cor)

        # Atualiza a seção de Memória RAM
        if "MEMORY" in self.bars_refs:
            lbl_ram = self.bars_refs["MEMORY"]['label']
            # 🔥 TRAVA DE SEGURANÇA: Só atualiza se o texto ainda existir na tela
            if lbl_ram.winfo_exists():
                lbl_ram.configure(text=f"{ram_val}%")
                for bar in self.bars_refs["MEMORY"]['visuals']:
                    if bar.winfo_exists():
                        h = random.randint(10, 22) if ram_val > 80 else random.randint(5, 14)
                        bar.configure(height=h)
        
        # self.add_to_log("=== SISTEMA ARCANA 2026 INICIADO ===")
        # self.add_to_log("Motor Visual SPA carregado. Aguardando a IA...")

    def atualizar_cerebro(self, chave, valor):
        try:
            with open(BRAIN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
            
        data[chave] = valor
        
        try:
            with open(BRAIN_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log_terminal(f"❌ Erro ao salvar {chave}: {e}")

    def add_to_log(self, message):
        self.log_history.append(message)
        print(message) 
        
        if hasattr(self, 'log_area') and self.log_area.winfo_exists():
            self.log_area.configure(state="normal")
            self.log_area.insert("end", message + "\n")
            self.log_area.see("end")
            self.log_area.configure(state="disabled")

    def toggle_system(self):
        if self.launcher.enabled:
            self.launcher.enabled = False
            self.status_dot.configure(text_color="#FF3366")
            self.status_text.configure(text="OFFLINE", text_color="#FF3366")
            if hasattr(self, 'btn_toggle') and self.btn_toggle.winfo_exists():
                self.btn_toggle.configure(text="ATIVAR AUTOMAÇÃO", border_color=ACCENT, text_color=ACCENT)
            self.add_to_log("\n⚠️ Automação pausada.")
        else:
            self.launcher.enabled = True
            self.status_dot.configure(text_color=ACCENT)
            self.status_text.configure(text="ONLINE", text_color=TEXT_LIGHT)
            if hasattr(self, 'btn_toggle') and self.btn_toggle.winfo_exists():
                self.btn_toggle.configure(text="DESATIVAR AUTOMAÇÃO", border_color="#FF3366", text_color="#FF3366")
            self.add_to_log("\n✅ Automação reativada.")

    def log_terminal(self, message):
        print(message)

    # -----------------------------------
    # MENUS E CABEÇALHO
    # -----------------------------------
    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=SIDEBAR_BG, border_width=1, border_color="#101825")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1) 

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, pady=(30, 40), sticky="ew")
        self.logo_canvas = tk.Canvas(logo_frame, width=50, height=50, bg=SIDEBAR_BG, highlightthickness=0)
        self.logo_canvas.pack()
        self.logo_canvas.create_oval(5, 5, 45, 45, fill="#0F1722", outline=ACCENT_DIM, width=1)
        self.logo_canvas.create_text(25, 25, text="⚡", fill=ACCENT, font=("Segoe UI", 16))

        menus = [
            ("🏠", "Dashboard"),
            ("🎤", "Modo de Uso"),
            ("⚡", "Automações"),
            ("🔑", "Chaves API"), 
            ("⚙️", "Configurações"),
            ("💬", "Discord") 
        ]

        for i, (icon, text) in enumerate(menus):
            frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", corner_radius=0)
            frame.grid(row=i+1, column=0, sticky="ew", pady=5)
            
            indicator = ctk.CTkFrame(frame, width=3, height=30, fg_color="transparent", corner_radius=0)
            indicator.pack(side="left")

            btn = ctk.CTkButton(frame, text=f"  {icon}    {text}", fg_color="transparent", 
                                text_color=TEXT_DIM, hover_color="#111A26", 
                                font=ctk.CTkFont(size=13, weight="normal"), 
                                anchor="w", height=35)
            
            if text == "Discord":
                btn.configure(command=self.abrir_gui_discord)
            else:
                btn.configure(command=lambda v=text: self.switch_view(v))
                
            btn.pack(side="left", fill="x", expand=True, padx=(15, 20))
            
            self.menu_btns[text] = btn
            self.menu_indicators[text] = indicator

    def create_header(self):
        header = ctk.CTkFrame(self.main_container, fg_color="transparent", height=40)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header.grid_columnconfigure(1, weight=1)

        self.lbl_title = ctk.CTkLabel(header, text="A R C A N A", font=ctk.CTkFont(size=20, weight="bold"), text_color=ACCENT)
        self.lbl_title.pack(side="left")

        right_controls = ctk.CTkFrame(header, fg_color="transparent")
        right_controls.pack(side="right")
        self.status_dot = ctk.CTkLabel(right_controls, text="●", text_color=ACCENT, font=ctk.CTkFont(size=16))
        self.status_dot.pack(side="left", padx=(0, 5))
        self.status_text = ctk.CTkLabel(right_controls, text="ONLINE", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_LIGHT)
        self.status_text.pack(side="left")

    # -----------------------------------
    # O MOTOR DE NAVEGAÇÃO
    # -----------------------------------
    def switch_view(self, view_name):
        for name, btn in self.menu_btns.items():
            if name == view_name:
                btn.configure(text_color=ACCENT, font=ctk.CTkFont(size=13, weight="bold"))
                self.menu_indicators[name].configure(fg_color=ACCENT)
            else:
                btn.configure(text_color=TEXT_DIM, font=ctk.CTkFont(size=13, weight="normal"))
                self.menu_indicators[name].configure(fg_color="transparent")
        
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=0) 
            
        if view_name == "Modo de Uso":
            self.lbl_title.configure(text="M O D O   D E   U S O")
            self.content_frame.grid_columnconfigure(1, weight=1) 
            self.render_aura_panel(self.content_frame, 0)
            self.render_modos_panel(self.content_frame, 1)
            
        elif view_name == "Dashboard":
            self.lbl_title.configure(text="D A S H B O A R D   ( C O N S O L E )")
            self.content_frame.grid_columnconfigure(1, weight=1) 
            self.render_aura_panel(self.content_frame, 0)
            self.render_console_panel(self.content_frame, 1)
            
        elif view_name == "Automações":
            self.lbl_title.configure(text="G E R E N C I A D O R   D E   A U T O M A Ç Õ E S")
            self.render_automacoes_panel(self.content_frame)

        elif view_name == "Chaves API":
            self.lbl_title.configure(text="C H A V E S   D E   A P I")
            self.render_api_panel(self.content_frame)

        elif view_name == "Configurações":
            self.lbl_title.configure(text="C O N F I G U R A Ç Õ E S   C O G N I T I V A S")
            self.render_configuracoes_panel(self.content_frame)

    # -----------------------------------
    # AS TELAS (VIEWS)
    # -----------------------------------
    def render_aura_panel(self, parent, col):
        aura_frame = ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=10, border_width=1, border_color="#101825")
        aura_frame.grid(row=0, column=col, sticky="nsew", padx=(0, 10))
        
        core_container = ctk.CTkFrame(aura_frame, fg_color="transparent")
        core_container.pack(pady=(40, 10), fill="x")
        
        canvas = tk.Canvas(core_container, width=200, height=200, bg=PANEL_BG, highlightthickness=0)
        canvas.pack()
        canvas.create_oval(10, 10, 190, 190, outline=TEXT_DIM, width=1, dash=(2, 4))
        canvas.create_oval(30, 30, 170, 170, outline=ACCENT_DIM, width=1)
        canvas.create_oval(50, 50, 150, 150, fill="#0F1A2A", outline="#1D2A3D", width=2)
        canvas.create_text(100, 100, text="I A", fill=TEXT_LIGHT, font=("Segoe UI", 24, "bold"))

        ctk.CTkLabel(aura_frame, text="A U R A   C O R E", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_LIGHT).pack(pady=(5, 0))
        ctk.CTkLabel(aura_frame, text="Aguardando Comando", font=ctk.CTkFont(size=11, weight="bold"), text_color=ACCENT).pack(pady=(0, 20))

        def create_bar(title, value):
            frame = ctk.CTkFrame(aura_frame, fg_color="#0D131C", corner_radius=6, border_width=1, border_color="#16202E")
            frame.pack(fill="x", padx=25, pady=8)
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x", padx=15, pady=(10, 0))
            
            ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_DIM).pack(side="left")
            
            # 1. Damos um nome para a label (lbl_porcentagem) para o motor conseguir trocar o texto
            lbl_porcentagem = ctk.CTkLabel(header, text=value, font=ctk.CTkFont(size=11, weight="bold"), text_color=ACCENT)
            lbl_porcentagem.pack(side="right")
            
            bars_frame = ctk.CTkFrame(frame, fg_color="transparent", height=30)
            bars_frame.pack(fill="x", padx=15, pady=(5, 10))
            bars_frame.pack_propagate(False)
            
            # 2. Criamos uma lista vazia para guardar cada barrinha azul
            barras_visuais = []
            
            for _ in range(12):
                h = random.randint(5, 20)
                bar = ctk.CTkFrame(bars_frame, width=5, height=h, fg_color=ACCENT if h > 15 else ACCENT_DIM, corner_radius=2)
                bar.pack(side="left", padx=3, anchor="s") 
                # 3. Adicionamos a barrinha na nossa lista
                barras_visuais.append(bar)
            
            # 🔥 O PULO DO GATO: Salvamos as referências no dicionário que a Thread lê
            self.bars_refs[title] = {
                'label': lbl_porcentagem,
                'visuals': barras_visuais
            }

        # Mantém as chamadas originais
        create_bar("CPU USAGE", "0%")
        create_bar("MEMORY", "0%")

    def render_modos_panel(self, parent, col):
        right_frame = ctk.CTkFrame(parent, fg_color="transparent")
        right_frame.grid(row=0, column=col, sticky="nsew", padx=(10, 0))
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)

        banner = ctk.CTkFrame(right_frame, fg_color=PANEL_BG, corner_radius=10, border_width=1, border_color="#101825")
        banner.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ctk.CTkLabel(banner, text="M O D O   D E   U S O", font=ctk.CTkFont(size=15, weight="bold"), text_color=ACCENT).pack(anchor="w", padx=25, pady=(20, 5))
        ctk.CTkLabel(banner, text="Escolha como a Shogun vai te ouvir. Depois da escolha, este painel inicial some e\no foco volta para o dashboard.", font=ctk.CTkFont(size=11), text_color=TEXT_LIGHT, justify="left").pack(anchor="w", padx=25, pady=(0, 20))

        modes_panel = ctk.CTkFrame(right_frame, fg_color=PANEL_BG, corner_radius=10, border_width=1, border_color="#101825")
        modes_panel.grid(row=1, column=0, sticky="nsew")
        modes_panel.grid_columnconfigure(0, weight=1)
        modes_panel.grid_columnconfigure(1, weight=1)

        m_header = ctk.CTkFrame(modes_panel, fg_color="transparent")
        m_header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=25, pady=(20, 15))
        
        m_title = ctk.CTkFrame(m_header, fg_color="transparent")
        m_title.pack(side="left")
        ctk.CTkLabel(m_title, text="M O D O   D E   U S O", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_LIGHT).pack(anchor="w")
        ctk.CTkLabel(m_title, text="Selecione o modo de escuta desejado.", font=ctk.CTkFont(size=11), text_color=TEXT_DIM).pack(anchor="w")

        mic_status = ctk.CTkFrame(m_header, fg_color="#151E2B", corner_radius=15, border_width=1, border_color="#2A384A")
        mic_status.pack(side="right")
        
        texto_mic = "MIC GRAVANDO" if self.microfone_aberto else "MIC PARADO"
        cor_mic = "#FF3366" if self.microfone_aberto else TEXT_DIM
        self.lbl_mic_status = ctk.CTkLabel(mic_status, text=texto_mic, font=ctk.CTkFont(size=10, weight="bold"), text_color=cor_mic)
        self.lbl_mic_status.pack(padx=15, pady=5)

        self.cards_modo = {}

        def selecionar_modo(modo):
            self.modo_selecionado = modo
            self.atualizar_cerebro("modo_operacao_atual", modo) 
            self.add_to_log(f"🔄 Modo alterado para: {modo}")
            
            self.microfone_aberto = False
            self.atualizar_cerebro("microfone_aberto", False)
            
            for m, elements in self.cards_modo.items():
                is_active = (m == modo)
                bg = "#0B1525" if is_active else "#0E1520"
                border = "#1A3B5C" if is_active else "#16202E"
                text_col = ACCENT if is_active else TEXT_LIGHT
                elements['frame'].configure(fg_color=bg, border_color=border)
                elements['title'].configure(text_color=text_col)

        def create_card(row, col, title, desc):
            is_active = (title == self.modo_selecionado)
            bg = "#0B1525" if is_active else "#0E1520"
            border = "#1A3B5C" if is_active else "#16202E"
            
            card = ctk.CTkFrame(modes_panel, fg_color=bg, corner_radius=8, border_width=1, border_color=border, cursor="hand2")
            card.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)
            
            lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT if is_active else TEXT_LIGHT)
            lbl_t.pack(anchor="w", padx=20, pady=(20, 5))
            lbl_d = ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=11), text_color=TEXT_DIM, justify="left", wraplength=200)
            lbl_d.pack(anchor="w", padx=20, pady=(0, 20))

            for w in (card, lbl_t, lbl_d):
                w.bind("<Button-1>", lambda e, m=title: selecionar_modo(m))
                
            self.cards_modo[title] = {'frame': card, 'title': lbl_t}

        create_card(1, 0, "Chat", "Interação por texto no console.")
        create_card(1, 1, "Contínuo", "Microfone aberto, responde tudo que ouvir.")
        create_card(2, 0, "Press to Talk", "Escuta somente quando você mandar ouvir manualmente.")
        create_card(2, 1, "Responder Quando Chamada", "Microfone ativo, responde só quando ouvir o nome Shogun.")

        def toggle_visao():
            self.visao_ligada = not self.visao_ligada
            self.atualizar_cerebro("visao_computacional_ativa", self.visao_ligada) 
            if self.visao_ligada:
                self.btn_visao.configure(text="Visão Ligada", fg_color="#1A3B5C", border_color=ACCENT, text_color=ACCENT)
                self.add_to_log("👁️ Sistema de Visão Computacional ATIVADO.")
            else:
                self.btn_visao.configure(text="Visão Desligada", fg_color="#0E1520", border_color="#16202E", text_color=TEXT_LIGHT)
                self.add_to_log("👁️ Sistema de Visão Computacional DESATIVADO.")

        def toggle_ouvir():
            self.microfone_aberto = not self.microfone_aberto
            self.atualizar_cerebro("microfone_aberto", self.microfone_aberto) 
            if self.microfone_aberto:
                self.btn_ouvir.configure(text="Parar de Ouvir", fg_color="#330011", border_color="#FF3366", text_color="#FF3366")
                self.lbl_mic_status.configure(text="MIC GRAVANDO", text_color="#FF3366")
                self.add_to_log("🎙️ Microfone ABERTO. Escutando...")
            else:
                self.btn_ouvir.configure(text="Ouvir Agora", fg_color="#071A20", border_color="#004433", text_color="#00FFaa")
                self.lbl_mic_status.configure(text="MIC PARADO", text_color=TEXT_DIM)
                self.add_to_log("🔇 Microfone FECHADO.")

        btn_frame = ctk.CTkFrame(modes_panel, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(15, 20))
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        
        cor_v_bg = "#1A3B5C" if self.visao_ligada else "#0E1520"
        cor_v_bd = ACCENT if self.visao_ligada else "#16202E"
        cor_v_tx = ACCENT if self.visao_ligada else TEXT_LIGHT
        txt_v = "Visão Ligada" if self.visao_ligada else "Visão Desligada"
        
        self.btn_visao = ctk.CTkButton(btn_frame, text=txt_v, command=toggle_visao, fg_color=cor_v_bg, hover_color="#204060", border_width=1, border_color=cor_v_bd, text_color=cor_v_tx, height=45, font=ctk.CTkFont(size=13, weight="bold"))
        self.btn_visao.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        cor_m_bg = "#330011" if self.microfone_aberto else "#071A20"
        cor_m_bd = "#FF3366" if self.microfone_aberto else "#004433"
        cor_m_tx = "#FF3366" if self.microfone_aberto else "#00FFaa"
        txt_m = "Parar de Ouvir" if self.microfone_aberto else "Ouvir Agora"

        self.btn_ouvir = ctk.CTkButton(btn_frame, text=txt_m, command=toggle_ouvir, fg_color=cor_m_bg, hover_color="#440011", border_width=1, border_color=cor_m_bd, text_color=cor_m_tx, height=45, font=ctk.CTkFont(size=13, weight="bold"))
        self.btn_ouvir.grid(row=0, column=1, sticky="ew", padx=(5, 0))

    def render_console_panel(self, parent, col):
        right_frame = ctk.CTkFrame(parent, fg_color="transparent")
        right_frame.grid(row=0, column=col, sticky="nsew", padx=(10, 0))
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1) 

        console_frame = ctk.CTkFrame(right_frame, fg_color=PANEL_BG, corner_radius=10, border_width=1, border_color="#101825")
        console_frame.grid(row=0, column=0, sticky="nsew")
        console_frame.grid_columnconfigure(0, weight=1)
        console_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(console_frame, text="C O N S O L E   D E   A T I V I D A D E", font=ctk.CTkFont(size=12, weight="bold"), text_color=ACCENT).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))

        self.log_area = ctk.CTkTextbox(console_frame, fg_color="#0D131C", text_color="#A3B4C8", font=ctk.CTkFont(family="Consolas", size=12), corner_radius=8, border_width=1, border_color="#16202E")
        self.log_area.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        self.log_area.insert("end", "\n".join(self.log_history) + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

        btn_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(15, 0))

        color, text = ("#FF3366", "DESATIVAR AUTOMAÇÃO") if self.launcher.enabled else (ACCENT, "ATIVAR AUTOMAÇÃO")
        self.btn_toggle = ctk.CTkButton(btn_frame, text=text, command=self.toggle_system, fg_color="transparent", border_width=1, border_color=color, text_color=color, hover_color="#2D1B22", height=40, font=ctk.CTkFont(size=12, weight="bold"))
        self.btn_toggle.pack(side="right")

    def render_automacoes_panel(self, parent):
        f = ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=10, border_width=1, border_color="#101825")
        f.grid(row=0, column=0, columnspan=2, sticky="nsew")
        
        ctk.CTkLabel(f, text="⚡ APPS E COMANDOS CADASTRADOS", font=ctk.CTkFont(size=16, weight="bold"), text_color=ACCENT).pack(pady=20)

        lista_frame = ctk.CTkScrollableFrame(f, fg_color="#0D131C", border_width=1, border_color="#16202E", height=250)
        lista_frame.pack(fill="x", padx=40, pady=10)

        def atualizar_lista():
            for w in lista_frame.winfo_children(): w.destroy()
            for name, data in self.launcher.apps.items():
                item = ctk.CTkFrame(lista_frame, fg_color="transparent")
                item.pack(fill="x", pady=2)
                ctk.CTkLabel(item, text=f"• {name.upper()}", font=ctk.CTkFont(weight="bold"), text_color=TEXT_LIGHT).pack(side="left", padx=10)
                ctk.CTkLabel(item, text=f"({data['target'][:40]}...)", font=ctk.CTkFont(size=10), text_color=TEXT_DIM).pack(side="left")
                btn_del = ctk.CTkButton(item, text="X", width=20, height=20, fg_color="#331111", hover_color="#551111", text_color="#FF5555", command=lambda n=name: remover_app(n))
                btn_del.pack(side="right", padx=10)

        def remover_app(nome):
            if nome in self.launcher.apps:
                del self.launcher.apps[nome]
                try:
                    with open(BRAIN_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
                    if "custom_apps" in data and nome in data["custom_apps"]:
                        del data["custom_apps"][nome]
                        with open(BRAIN_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
                except: pass
                atualizar_lista()
                self.add_to_log(f"🗑️ App removido permanentemente: {nome}")

        atualizar_lista()

        add_frame = ctk.CTkFrame(f, fg_color="#0F1722", border_width=1, border_color=ACCENT_DIM)
        add_frame.pack(fill="x", padx=40, pady=20)
        
        ctk.CTkLabel(add_frame, text="ADICIONAR NOVO APP", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_LIGHT).pack(pady=10)
        
        entry_nome = ctk.CTkEntry(add_frame, placeholder_text="Nome (Ex: Calculadora)", width=250, fg_color="#05080E")
        entry_nome.pack(side="left", padx=10, pady=10)
        
        entry_path = ctk.CTkEntry(add_frame, placeholder_text="Caminho/Comando (Ex: calc.exe)", width=350, fg_color="#05080E")
        entry_path.pack(side="left", padx=10, pady=10)

        def salvar_novo_app():
            nome = entry_nome.get().strip()
            path = entry_path.get().strip()
            if nome and path:
                novo_app = {"target": path, "process_names": [path.split('\\')[-1] if '\\' in path else path], "allow_multiple": True, "aliases": [nome.lower()]}
                self.launcher.apps[nome] = novo_app
                try:
                    with open(BRAIN_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
                except: data = {}
                if "custom_apps" not in data: data["custom_apps"] = {}
                data["custom_apps"][nome] = novo_app
                with open(BRAIN_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
                atualizar_lista()
                entry_nome.delete(0, 'end'); entry_path.delete(0, 'end')
                self.add_to_log(f"🚀 Novo app mapeado permanentemente: {nome}")

        btn_add = ctk.CTkButton(add_frame, text="+ ADD", width=80, fg_color=ACCENT, text_color="#0B0E14", font=ctk.CTkFont(weight="bold"), command=salvar_novo_app)
        btn_add.pack(side="left", padx=10, pady=10)

    # 🔥 ABA ATUALIZADA: AGORA COM ELEVENLABS 🔥
    def render_api_panel(self, parent):
        f = ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=10, border_width=1, border_color="#101825")
        f.grid(row=0, column=0, columnspan=2, sticky="nsew")
        
        ctk.CTkLabel(f, text="🔑 GESTÃO DE CHAVES API (.env)", font=ctk.CTkFont(size=16, weight="bold"), text_color=ACCENT).pack(pady=20)

        keys = {
            "NVIDIA_API_KEY": "", 
            "GROQ_API_KEY_LLM": "", 
            "GROQ_API_KEY_VISION": "",
            "ELEVENLABS_API_KEY": "",
            "ELEVENLABS_VOICE_ID": "",
            "DISCORD_TOKEN": ""
        }
        
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, 'r') as file:
                for line in file:
                    for k in keys:
                        if line.startswith(k) and "=" in line: 
                            keys[k] = line.split('=', 1)[1].strip()

        scroll_area = ctk.CTkScrollableFrame(f, fg_color="transparent", height=400)
        scroll_area.pack(fill="both", expand=True, padx=20)

        entries = {}
        for k, v in keys.items():
            ctk.CTkLabel(scroll_area, text=k, text_color=TEXT_DIM).pack(anchor="w", padx=30, pady=(5,0))
            e = ctk.CTkEntry(scroll_area, width=600, fg_color="#0D131C", border_color="#16202E")
            e.insert(0, v)
            e.pack(pady=(0, 15), padx=30)
            entries[k] = e

        def salvar_env():
            with open(ENV_FILE, 'w') as file:
                for k, e in entries.items(): 
                    file.write(f"{k}={e.get()}\n")
            self.add_to_log("✅ Arquivo .env atualizado com as chaves do ElevenLabs!")

        ctk.CTkButton(f, text="ATUALIZAR CHAVES NO .ENV", command=salvar_env, fg_color="#A6E3A1", text_color="#0B0E14", font=ctk.CTkFont(weight="bold")).pack(pady=20)

    # 🔥 ABA ATUALIZADA: AGORA COM BOTÕES DO ELEVENLABS 🔥
    def render_configuracoes_panel(self, parent):
        config_frame = ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=10, border_width=1, border_color="#101825")
        config_frame.grid(row=0, column=0, sticky="nsew")
        config_frame.grid_columnconfigure(0, weight=1)
        config_frame.grid_columnconfigure(1, weight=1)
        
        try:
            with open(BRAIN_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
            modelos = data.get("modelos_ativos", {"local": "nvidia", "discord": "groq", "tts": "ElevenLabs"})
            vtuber = data.get("vtuber_overlay_ativo", False)
        except:
            modelos = {"local": "nvidia", "discord": "groq", "tts": "ElevenLabs"}
            vtuber = False

        var_local = ctk.StringVar(value=modelos.get("local", "nvidia").upper())
        var_discord = ctk.StringVar(value=modelos.get("discord", "groq").upper())
        var_tts = ctk.StringVar(value=modelos.get("tts", "ElevenLabs").upper()) 
        var_vtuber = ctk.StringVar(value="LIGADO" if vtuber else "DESLIGADO")

        # COLUNA 0 - LLMs
        ctk.CTkLabel(config_frame, text="🧠 MODELOS DE LINGUAGEM", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT).grid(row=0, column=0, sticky="w", padx=30, pady=(30, 10))
        ctk.CTkLabel(config_frame, text="Processamento Local (PC):", text_color=TEXT_LIGHT).grid(row=1, column=0, sticky="w", padx=30, pady=(10, 5))
        ctk.CTkSegmentedButton(config_frame, values=["NVIDIA", "GROQ"], variable=var_local, selected_color="#FF3366", selected_hover_color="#CC2952", unselected_color="#0D131C", unselected_hover_color="#1A2536", width=250).grid(row=2, column=0, sticky="w", padx=30)
        ctk.CTkLabel(config_frame, text="Processamento Discord:", text_color=TEXT_LIGHT).grid(row=3, column=0, sticky="w", padx=30, pady=(20, 5))
        ctk.CTkSegmentedButton(config_frame, values=["NVIDIA", "GROQ"], variable=var_discord, selected_color=ACCENT, selected_hover_color=ACCENT_DIM, unselected_color="#0D131C", unselected_hover_color="#1A2536", width=250).grid(row=4, column=0, sticky="w", padx=30)

        # COLUNA 1 - VTUBER E VOZ (TTS)
        ctk.CTkLabel(config_frame, text="🎭 AVATAR VIRTUAL", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT).grid(row=0, column=1, sticky="w", padx=30, pady=(30, 10))
        ctk.CTkLabel(config_frame, text="Status do Overlay (VTube Studio):", text_color=TEXT_LIGHT).grid(row=1, column=1, sticky="w", padx=30, pady=(10, 5))
        ctk.CTkSegmentedButton(config_frame, values=["LIGADO", "DESLIGADO"], variable=var_vtuber, selected_color="#A6E3A1", selected_hover_color="#89B4FA", unselected_color="#0D131C", width=250).grid(row=2, column=1, sticky="w", padx=30)

        # NOVOS BOTÕES DE VOZ
        ctk.CTkLabel(config_frame, text="🗣️ SÍNTESE DE VOZ (TTS)", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT).grid(row=3, column=1, sticky="w", padx=30, pady=(20, 10))
        ctk.CTkLabel(config_frame, text="Voz Ativa do Sistema:", text_color=TEXT_LIGHT).grid(row=4, column=1, sticky="w", padx=30, pady=(0, 5))
        ctk.CTkSegmentedButton(config_frame, values=["ELEVENLABS", "MICROSOFT"], variable=var_tts, selected_color="#A6E3A1", selected_hover_color="#89B4FA", unselected_color="#0D131C", width=250).grid(row=5, column=1, sticky="w", padx=30)

        def salvar_config():
            try:
                with open(BRAIN_FILE, 'r', encoding='utf-8') as f: d = json.load(f)
            except: d = {}
            if "modelos_ativos" not in d: d["modelos_ativos"] = {}
            d["modelos_ativos"]["local"] = var_local.get().lower()
            d["modelos_ativos"]["discord"] = var_discord.get().lower()
            
            voz_escolhida = var_tts.get().capitalize()
            if voz_escolhida == "Elevenlabs": voz_escolhida = "ElevenLabs"
            
            d["modelos_ativos"]["tts"] = voz_escolhida
            d["vtuber_overlay_ativo"] = True if var_vtuber.get() == "LIGADO" else False
            with open(BRAIN_FILE, 'w', encoding='utf-8') as f: json.dump(d, f, indent=4, ensure_ascii=False)
            self.add_to_log("💾 Configurações Cognitivas Salvas com Sucesso!")

        ctk.CTkButton(config_frame, text="GUARDAR ALTERAÇÕES", command=salvar_config, fg_color=ACCENT, hover_color=ACCENT_DIM, text_color="#0B0E14", font=ctk.CTkFont(size=14, weight="bold"), height=40).grid(row=6, column=0, columnspan=2, pady=50)

    # ==========================================
    # MODAL: CONFIGURAÇÕES DO DISCORD
    # ==========================================
    def abrir_gui_discord(self):
        janela_discord = ctk.CTkToplevel(self)
        janela_discord.title("ARCANA - Configuração do Discord")
        janela_discord.geometry("900x700") 
        janela_discord.configure(fg_color="#0B0E14")
        
        try:
            with open(BRAIN_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
        except: data = {}

        var_discord_on = tk.BooleanVar(value=data.get("discord_active", False))
        var_music_on = tk.BooleanVar(value=data.get("discord_music_mode", False))
        var_server = tk.BooleanVar(value=data.get("discord_server_active", True))
        var_mentions = tk.BooleanVar(value=data.get("discord_mentions", True))
        var_dinamismo = tk.BooleanVar(value=data.get("discord_dinamismo", True))
        var_autopost = tk.StringVar(value=str(data.get("discord_auto_post", 0)))
        var_unit = tk.StringVar(value=data.get("discord_auto_post_unit", "Minutos"))
        var_target_on = tk.BooleanVar(value=data.get("discord_target_user_active", False))
        var_dm = tk.BooleanVar(value=data.get("discord_dm_active", False))
        var_dm_dono = tk.BooleanVar(value=data.get("discord_dm_dono_always", False))
        target_name = data.get("discord_target_user_name", "")
        
        disabled_guilds = data.get("discord_disabled_guilds", [])
        guilds_list = data.get("discord_guilds_cache", [])

        ctk.CTkLabel(janela_discord, text="CONFIGURAÇÃO DE REDE: DISCORD", font=ctk.CTkFont(size=20, weight="bold"), text_color=ACCENT).pack(pady=(20, 10), padx=30, anchor="w")

        container = ctk.CTkScrollableFrame(janela_discord, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=10)
        
        left_col = ctk.CTkFrame(container, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right_col = ctk.CTkFrame(container, fg_color="transparent")
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))

        def criar_switch(master, texto, variavel, cor=ACCENT):
            return ctk.CTkSwitch(master, text=texto, variable=variavel, progress_color=cor, font=ctk.CTkFont(size=12))

        f_main = ctk.CTkFrame(left_col, fg_color="#1A1F2D", corner_radius=8)
        f_main.pack(fill="x", pady=5)
        ctk.CTkLabel(f_main, text="OPERAÇÃO PRINCIPAL", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_DIM).pack(anchor="w", padx=15, pady=(10, 5))
        criar_switch(f_main, "LIGAR A IA NO DISCORD", var_discord_on, "#FF3366").pack(anchor="w", padx=15, pady=5)
        criar_switch(f_main, "Ativar Modo Música (Desativa Voz)", var_music_on).pack(anchor="w", padx=15, pady=(5, 15))

        f_server = ctk.CTkFrame(left_col, fg_color="#1A1F2D", corner_radius=8)
        f_server.pack(fill="x", pady=5)
        ctk.CTkLabel(f_server, text="REGRAS DE SERVIDOR", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_DIM).pack(anchor="w", padx=15, pady=(10, 5))
        criar_switch(f_server, "Responder livremente", var_server).pack(anchor="w", padx=15, pady=5)
        criar_switch(f_server, "Responder a Menções (@)", var_mentions).pack(anchor="w", padx=15, pady=5)
        criar_switch(f_server, "Ativar Dinamismo (Zoações)", var_dinamismo).pack(anchor="w", padx=15, pady=(5, 15))

        f_tempo = ctk.CTkFrame(left_col, fg_color="#1A1F2D", corner_radius=8)
        f_tempo.pack(fill="x", pady=5)
        ctk.CTkLabel(f_tempo, text="AUTO-POST (0 = DESLIGADO)", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_DIM).pack(anchor="w", padx=15, pady=(10, 5))
        f_t_inner = ctk.CTkFrame(f_tempo, fg_color="transparent")
        f_t_inner.pack(anchor="w", padx=15, pady=(0, 15))
        e_time = ctk.CTkEntry(f_t_inner, textvariable=var_autopost, width=80, fg_color="#0B0E14", border_color="#2A3241")
        e_time.pack(side="left", padx=(0, 10))
        cb_unit = ctk.CTkOptionMenu(f_t_inner, variable=var_unit, values=["Segundos", "Minutos"], fg_color="#0B0E14", button_color="#2A3241")
        cb_unit.pack(side="left")

        f_alvo = ctk.CTkFrame(left_col, fg_color="#1A1F2D", corner_radius=8)
        f_alvo.pack(fill="x", pady=5)
        ctk.CTkLabel(f_alvo, text="FOCO EM USUÁRIO", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_DIM).pack(anchor="w", padx=15, pady=(10, 5))
        criar_switch(f_alvo, "Responder TODAS as mensagens", var_target_on).pack(anchor="w", padx=15, pady=5)
        entry_target = ctk.CTkEntry(f_alvo, placeholder_text="Nome (@ ou Nick)", width=200, fg_color="#0B0E14", border_color="#2A3241")
        entry_target.insert(0, target_name)
        entry_target.pack(fill="x", padx=15, pady=(5, 15))

        ctk.CTkLabel(right_col, text="SERVIDORES ATIVOS", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_DIM).pack(anchor="w", pady=(5, 5))
        
        guild_vars = {}
        def toggle_all(state):
            for v in guild_vars.values(): v.set(state)

        btn_all = ctk.CTkFrame(right_col, fg_color="transparent")
        btn_all.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(btn_all, text="✅ Marcar Todos", command=lambda: toggle_all(True), width=100, fg_color="#2A3241", hover_color="#3A4454").pack(side="left")
        ctk.CTkButton(btn_all, text="❌ Desmarcar", command=lambda: toggle_all(False), width=100, fg_color="#2A3241", hover_color="#3A4454").pack(side="left", padx=10)

        servers_frame = ctk.CTkScrollableFrame(right_col, fg_color="#1A1F2D", corner_radius=8, height=450)
        servers_frame.pack(fill="both", expand=True)

        if not guilds_list:
            ctk.CTkLabel(servers_frame, text="Nenhum servidor no cache.\nLigue o bot primeiro.", text_color="#556070").pack(pady=40)
        else:
            for guild in guilds_list:
                g_id = str(guild['id'])
                is_active = g_id not in disabled_guilds
                var = tk.BooleanVar(value=is_active)
                guild_vars[g_id] = var
                f_g = ctk.CTkFrame(servers_frame, fg_color="#0B0E14", corner_radius=6)
                f_g.pack(fill="x", pady=4, padx=5)
                ctk.CTkSwitch(f_g, text=guild['name'], variable=var, progress_color=ACCENT).pack(anchor="w", padx=15, pady=10)

        def salvar_discord():
            try:
                with open(BRAIN_FILE, 'r', encoding='utf-8') as f: d = json.load(f)
            except: d = {}
            
            new_disabled = [gid for gid, var in guild_vars.items() if not var.get()]
            try: tempo_post = int(var_autopost.get())
            except: tempo_post = 0

            d.update({
                "discord_active": var_discord_on.get(),
                "discord_music_mode": var_music_on.get(),
                "discord_mentions": var_mentions.get(),
                "discord_dinamismo": var_dinamismo.get(),
                "discord_server_active": var_server.get(),
                "discord_dm_active": var_dm.get(),
                "discord_dm_dono_always": var_dm_dono.get(),
                "discord_auto_post": tempo_post,
                "discord_auto_post_unit": var_unit.get(),
                "discord_target_user_active": var_target_on.get(),
                "discord_target_user_name": entry_target.get().strip(),
                "discord_disabled_guilds": new_disabled
            })
            
            with open(BRAIN_FILE, 'w', encoding='utf-8') as f: json.dump(d, f, indent=4, ensure_ascii=False)
            self.add_to_log("💾 [SISTEMA] Configurações do Discord Salvas!")
            janela_discord.destroy()

        ctk.CTkButton(janela_discord, text="SALVAR DISCORD E FECHAR", command=salvar_discord, fg_color="#FF3366", hover_color="#CC2952", font=ctk.CTkFont(size=14, weight="bold"), height=40).pack(pady=(10, 20), padx=30, fill="x")
        
        janela_discord.transient(self)
        janela_discord.grab_set()
        janela_discord.focus_force()

# ==========================================
# PONTE PARA O RUN.PY
# ==========================================
class RemGUI:
    janela = None

    @classmethod
    def iniciar_gui_loop(cls, nome_ai_override=None):
        if cls.janela is not None: return
        
        try:
            with open(BRAIN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                nome_ai = data.get("personality", {}).get("name", "IA")
        except:
            nome_ai = "IA"

        if nome_ai_override: nome_ai = nome_ai_override

        cls.janela = ArcanaDashboard(nome_ai=nome_ai)
        cls.janela.protocol("WM_DELETE_WINDOW", lambda: cls.janela.withdraw())
        cls.janela.mainloop()

    @classmethod
    def toggle(cls):
        if cls.janela:
            if cls.janela.state() != "normal":
                cls.janela.deiconify()
            else:
                cls.janela.withdraw()

if __name__ == "__main__":
    RemGUI.iniciar_gui_loop()