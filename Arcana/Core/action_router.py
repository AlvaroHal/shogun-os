import json
import os
import re
import subprocess
import webbrowser

import psutil
import requests

from Arcana.Core.config import get_config


class ActionRouter:
    """
    Roteador central da Shogun.

    Recebe o texto bruto da IA, executa acoes declaradas por tags e devolve
    o texto limpo para o TTS falar.
    """

    DEFAULT_APPS = {
        "chrome": {
            "target": "chrome",
            "aliases": ["navegador", "browser", "google"],
            "process_names": ["chrome.exe"],
            "allow_multiple": True,
        },
        "navegador": {
            "target": "https://www.google.com",
            "aliases": ["internet", "web", "pesquisar"],
            "process_names": ["chrome.exe", "msedge.exe", "firefox.exe"],
            "allow_multiple": True,
        },
        "youtube": {
            "target": "https://www.youtube.com",
            "aliases": ["yt", "videos", "vídeos"],
            "process_names": [],
            "allow_multiple": True,
        },
        "bloco de notas": {
            "target": "notepad",
            "aliases": ["notepad", "notas", "anotações", "editor de texto"],
            "process_names": ["notepad.exe"],
            "allow_multiple": True,
        },
        "cmd": {
            "target": "cmd",
            "aliases": ["terminal", "prompt"],
            "process_names": ["cmd.exe"],
            "allow_multiple": True,
        },
    }

    CLOSE_PATTERNS = [
        r"\bfecha\b",
        r"\bfechar\b",
        r"\bfeche\b",
        r"\bencerra\b",
        r"\bencerrar\b",
        r"\bencerre\b",
        r"\bmata\b",
        r"\bmatar\b",
        r"\bmate\b",
        r"\bdesliga\b",
        r"\bdesligar\b",
        r"\bclose\b",
        r"\bquit\b",
        r"\bexit\b",
    ]

    @classmethod
    def _load_brain(cls):
        brain_path = get_config().brain_file
        try:
            if brain_path.exists():
                with open(brain_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as exc:
            print(f"[ROTEADOR] Falha ao ler brain.json: {exc}")
        return {}

    @classmethod
    def _load_apps(cls):
        apps = dict(cls.DEFAULT_APPS)
        custom_apps = cls._load_brain().get("custom_apps", {})
        if isinstance(custom_apps, dict):
            for app_name, app_data in custom_apps.items():
                if isinstance(app_data, dict):
                    apps[app_name] = app_data
        return apps

    @staticmethod
    def _find_app(apps, raw_name):
        if not raw_name:
            return None, None

        command = raw_name.lower().strip()
        for app_name, app_data in apps.items():
            if not isinstance(app_data, dict):
                continue
            aliases = [a.lower() for a in app_data.get("aliases", [])]
            if command == app_name.lower() or command in aliases:
                return app_name, app_data

        for app_name, app_data in apps.items():
            if not isinstance(app_data, dict):
                continue
            aliases = [a.lower() for a in app_data.get("aliases", [])]
            if app_name.lower() in command or any(alias in command for alias in aliases):
                return app_name, app_data

        last_words = " ".join(command.split()[-2:])
        for app_name, app_data in apps.items():
            if not isinstance(app_data, dict):
                continue
            aliases = [a.lower() for a in app_data.get("aliases", [])]
            if last_words and (
                last_words in app_name.lower()
                or any(last_words in alias for alias in aliases)
            ):
                return app_name, app_data

        return None, None

    @staticmethod
    def _infer_app_action(prompt_usuario):
        texto = prompt_usuario.lower()
        if any(re.search(pattern, texto) for pattern in ActionRouter.CLOSE_PATTERNS):
            return "fechar"
        return "abrir"

    @staticmethod
    def _has_close_intent(prompt_usuario):
        texto = prompt_usuario.lower()
        return any(re.search(pattern, texto) for pattern in ActionRouter.CLOSE_PATTERNS)

    @staticmethod
    def _is_running(app_data):
        process_names = app_data.get("process_names", [])
        if isinstance(process_names, str):
            process_names = [process_names]
        if not process_names:
            return False

        for proc in psutil.process_iter(["name"]):
            try:
                proc_name = (proc.info.get("name") or "").lower()
                if any(target.lower() in proc_name for target in process_names):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    @staticmethod
    def _close_app(app_name, app_data):
        process_names = app_data.get("process_names", [])
        if isinstance(process_names, str):
            process_names = [process_names]
        closed = False

        for proc in psutil.process_iter(["name"]):
            try:
                proc_name = (proc.info.get("name") or "").lower()
                if any(target.lower() in proc_name for target in process_names):
                    proc.terminate()
                    closed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if closed:
            print(f"[ROTEADOR] '{app_name}' fechado.")
        else:
            print(f"[ROTEADOR] Nenhum processo encontrado para '{app_name}'.")

    @staticmethod
    def _open_target(app_name, app_data, param=None):
        target = str(app_data.get("target", "")).strip()
        if not target:
            print(f"[ROTEADOR] App '{app_name}' sem alvo configurado.")
            return

        if app_name.lower() == "youtube":
            if param:
                url = f"https://www.youtube.com/results?search_query={param.replace(' ', '+')}"
            else:
                url = target
            webbrowser.open(url)
            print(f"[ROTEADOR] YouTube aberto: {param or target}")
            return

        if app_name.lower() in ["navegador", "chrome"] and param:
            webbrowser.open(f"https://www.google.com/search?q={param.replace(' ', '+')}")
            print(f"[ROTEADOR] Pesquisa aberta: {param}")
            return

        target_clean = target.replace('"', "").replace("'", "").strip()
        if os.path.exists(target_clean):
            os.startfile(target_clean)
        else:
            subprocess.Popen(f'start "" "{target_clean}"', shell=True)
        print(f"[ROTEADOR] '{app_name}' aberto.")

    @classmethod
    def _process_app_actions(cls, texto_ia):
        apps = cls._load_apps()
        app_tags = re.findall(
            r"<APP:\s*(abrir|fechar)\s*:\s*([^>:]+)(?::([^>]*))?>",
            texto_ia,
            re.IGNORECASE,
        )

        for action, app_raw, param in app_tags:
            action = action.lower().strip()
            param = param.strip() if param else None
            app_name, app_data = cls._find_app(apps, app_raw)

            if not app_name:
                print(f"[ROTEADOR] App nao cadastrado: {app_raw}")
                continue

            if action == "abrir":
                if cls._is_running(app_data) and not app_data.get("allow_multiple", True):
                    print(f"[ROTEADOR] '{app_name}' ja esta aberto.")
                    continue
                cls._open_target(app_name, app_data, param)
            elif action == "fechar":
                cls._close_app(app_name, app_data)

    @staticmethod
    def process_actions(texto_ia, prompt_usuario=""):
        if not texto_ia:
            return ""

        texto_lower = texto_ia.lower()
        prompt_lower = prompt_usuario.lower()
        contexto_geral = prompt_lower + " " + texto_lower

        if "<APP:" in texto_ia and ActionRouter._has_close_intent(prompt_lower):
            texto_ia = re.sub(
                r"<APP:\s*abrir\s*:",
                "<APP: fechar:",
                texto_ia,
                flags=re.IGNORECASE,
            )

        if "<CMD:" not in texto_ia and "<APP:" not in texto_ia:
            apps = ActionRouter._load_apps()
            app_name, _ = ActionRouter._find_app(apps, contexto_geral)
            if app_name:
                action = ActionRouter._infer_app_action(prompt_lower)
                texto_ia += f" <APP: {action}:{app_name}>"

        texto_limpo = texto_ia

        match_emocao = re.search(
            r"\[(NORMAL|RIR|RAIVA|TRISTE|SURPRESA)\]",
            texto_ia.upper(),
        )
        if match_emocao:
            emocao = match_emocao.group(1)
            try:
                requests.post(f"http://127.0.0.1:8765/emotion/{emocao}", timeout=0.5)
                print(f"[ROTEADOR] Emocao {emocao} enviada pro VTube Studio.")
            except Exception:
                pass

        ActionRouter._process_app_actions(texto_ia)

        match_cmd = re.search(r"<CMD:\s*(.+?)>", texto_ia, flags=re.IGNORECASE)
        if match_cmd:
            comando = match_cmd.group(1).strip().lower()
            try:
                apps = ActionRouter._load_apps()
                app_name, app_data = ActionRouter._find_app(
                    apps,
                    comando.replace("open", "").strip(),
                )
                if app_name:
                    ActionRouter._open_target(app_name, app_data)
                else:
                    subprocess.Popen(comando, shell=True)
                    print(f"[ROTEADOR] Executado direto no SO: {comando}")
            except Exception as e:
                print(f"[ROTEADOR] Erro ao disparar {comando}: {e}")

        texto_limpo = re.sub(
            r"\[(NORMAL|RIR|RAIVA|TRISTE|SURPRESA)\]",
            "",
            texto_limpo,
            flags=re.IGNORECASE,
        )
        texto_limpo = re.sub(r"<APP:\s*.+?>", "", texto_limpo, flags=re.IGNORECASE)
        texto_limpo = re.sub(r"<CMD:\s*.+?>", "", texto_limpo, flags=re.IGNORECASE)
        texto_limpo = re.sub(r"<MUSICA:\s*.+?>", "", texto_limpo, flags=re.IGNORECASE)
        texto_limpo = re.sub(r"\[PLAY:\s*.+?\]", "", texto_limpo, flags=re.IGNORECASE)
        texto_limpo = re.sub(r",\s*([.!?])", r"\1", texto_limpo)
        texto_limpo = re.sub(r"\s+([.,!?;:])", r"\1", texto_limpo)
        texto_limpo = re.sub(r"\s{2,}", " ", texto_limpo)

        return texto_limpo.strip()
