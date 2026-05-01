import tkinter as tk
from tkinter import ttk, scrolledtext
import os
import re
import threading
import time
import logging
import keyboard
import subprocess
import psutil
import winsound
import urllib.parse 
import webbrowser
import json

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class AppLauncher:
    def __init__(self, output_callback=None):
        self.output_callback = output_callback
        self.gui_root = None
        self.enabled = True
        # Caminho corrigido para o seu banco de dados
        self.BRAIN_FILE = "Arcana/armazen/brain.json"
      
        # ==========================================
        # 📂 DICIONÁRIO DE APPS (CAMINHOS BLINDADOS)
        # ==========================================
        self.apps = {
            "Minecraft": {
                "target": "minecraft:",
                "aliases": ["jogo do bloco", "jogo quadrado", "farm", "mine"],
                "process_names": ["Minecraft.Windows.exe"],
                "allow_multiple": False
            },
            "Cyberpunk 2077": {
                "target": r"D:\SteamLibrary\steamapps\common\Cyberpunk 2077\bin\x64\Cyberpunk2077.exe",
                "aliases": ["2077", "cyberpunk", "night city", "dar uns tiros"],
                "process_names": ["Cyberpunk2077.exe"],
                "allow_multiple": False
            },
            "league of legends": {
                # O segredo: RAW string (r"") e o executável correto
                "target": r"D:\Riot Games\Riot Client\RiotClientServices.exe",
                "aliases": ["lol", "lolzinho", "league", "league of legends", "loey"],
                "process_names": ["RiotClientServices.exe", "LeagueClient.exe"],
                "allow_multiple": False
            },
            "bloco de notas": {
                "target": "notepad",
                "aliases": ["anotações", "notas", "editor de texto", "notepad", "escrever"],
                "process_names": ["notepad.exe"],
                "allow_multiple": True
            },
            "calculadora": {
                "target": "calc",
                "aliases": ["números", "cálculo", "calculadora", "contas"],
                "process_names": ["calculator.exe", "calc.exe", "CalculatorApp.exe"],
                "allow_multiple": True
            },
            "youtube": {
                "target": "https://www.youtube.com",
                "aliases": ["vídeos", "ver vídeo", "site do youtube", "youtube", "assistir algo"],
                "process_names": [], 
                "allow_multiple": True
            },
            "navegador": {
                "target": "https://www.google.com",
                "aliases": ["google", "pesquisar", "web", "internet", "browser", "navegador", "chrome", "edge"],
                "process_names": ["chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe"],
                "allow_multiple": True
            }
        }

    def obter_nomes_dos_apps(self):
        return ", ".join(self.apps.keys())

    def atualizar_servidores_gui(self, servidores):
        try:
            if os.path.exists(self.BRAIN_FILE):
                with open(self.BRAIN_FILE, 'r', encoding='utf-8') as f: 
                    data = json.load(f)
                
                guilds_cache = [{"id": nome, "name": nome} for nome in servidores]
                data["discord_guilds_cache"] = guilds_cache
                
                with open(self.BRAIN_FILE, 'w', encoding='utf-8') as f: 
                    json.dump(data, f, indent=4, ensure_ascii=False)
                    
                self.log("💾 [SISTEMA] Servidores do Discord gravados no cérebro!")
        except Exception as e:
            self.log(f"❌ [ERRO] Falha ao salvar servidores: {e}")

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
        
        last_words = ' '.join(command.split()[-2:])
        for app_name, app_data in self.apps.items():
            if last_words in app_name.lower() or any(last_words in a.lower() for a in app_data.get('aliases', [])):
                return app_name, app_data['target']
        
        return None, None

    def is_app_running(self, app_name):
        if app_name not in self.apps: return False
        process_names = self.apps[app_name].get('process_names', [])
        if not process_names: return False 

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
        try:
            # Limpeza de aspas para evitar duplicidade
            target_clean = target.replace('"', '').replace("'", "").strip()
            
            # 🚀 SOLUÇÃO PARA O ERRO "D:\Riot":
            # os.startfile é o método nativo que ignora o Shell do Windows (CMD).
            # Ele funciona como o clique duplo do mouse, resolvendo o problema de espaços.
            if os.path.exists(target_clean) or "\\" in target_clean or "/" in target_clean:
                os.startfile(target_clean)
                self.log(f"🚀 [SISTEMA] Executando binário: {target_clean}")
                return True
            else:
                # Fallback para comandos de sistema sem caminho fixo (calc, notepad)
                subprocess.Popen(f'start "" "{target_clean}"', shell=True)
                return True
        except Exception as e:
            self.log(f"❌ Erro ao abrir {app_name}: {str(e)}")
            return False

    def process_llm_tag(self, llm_response):
        if not self.enabled: return None

        # Regex para capturar a tag da IA
        tags_encontradas = re.findall(r'<APP:\s*(abrir|fechar)\s*:\s*([^>:]+)(?::([^>]*))?>', llm_response, re.IGNORECASE)
        if not tags_encontradas: return None

        resultados = []
        for match in tags_encontradas:
            action = match[0].lower().strip()
            app_raw = match[1].lower().strip()
            param = match[2].strip() if match[2] and match[2].strip() else None

            self.log(f"⚙️ Tag detectada -> Ação: {action.upper()} | Alvo: {app_raw}")

            app_name, target = self.find_app(app_raw)
            
            if not app_name:
                self.log(f"⚠️ Aplicativo '{app_raw}' não encontrado no dicionário.")
                continue

            is_running = self.is_app_running(app_name)

            if action == "abrir":
                if app_name.lower() == "youtube":
                    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(param)}" if param else "https://www.youtube.com"
                    webbrowser.open(url)
                    resultados.append("✅ YouTube aberto.")
                elif app_name.lower() == "navegador":
                    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(param)}" if param else "https://www.google.com"
                    webbrowser.open(url)
                    resultados.append("✅ Navegador aberto.")
                else:
                    if is_running and not self.apps[app_name].get('allow_multiple', True):
                        resultados.append(f"ℹ️ '{app_name}' já está aberto.")
                    else:
                        if self.open_app_cmd(app_name, target):
                            resultados.append(f"✅ '{app_name}' aberto.")
            
            elif action == "fechar":
                if self.close_app(app_name):
                    resultados.append(f"✅ '{app_name}' fechado.")

        return "\n".join(resultados) if resultados else None

class AppLauncherGUI:
    def __init__(self, root, launcher_instance):
        self.root = root
        self.launcher = launcher_instance
        self.root.title("Arcana Core - App Launcher")
        self.root.geometry("500x350")
        self.root.configure(bg="#1e1e2e")
        self.launcher.output_callback = self.add_to_log
        
        self.setup_styles()
        self.create_widgets()
        
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#1e1e2e")
        self.style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 9, "bold"))
        self.style.configure("Title.TLabel", font=("Segoe UI", 12, "bold"), foreground="#89b4fa")
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        ttk.Label(main_frame, text="Arcana - Status do Launcher", style="Title.TLabel").pack(pady=(0, 10))
        
        self.log_area = scrolledtext.ScrolledText(main_frame, bg="#313244", fg="#cdd6f4", font=("Consolas", 9), height=10)
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.log_area.config(state=tk.DISABLED)

    def add_to_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    launcher = AppLauncher()
    AppLauncherGUI(root, launcher)
    root.mainloop()