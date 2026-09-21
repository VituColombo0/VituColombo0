#!/usr/bin/env python3
"""
GitHub Activity Bot — mantém o gráfico de contribuições ativo
com comportamento realista modificando arquivos de um projeto falso.
"""

import os
import sys
import random
import subprocess
import logging
import json
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

LOG_FILE = os.path.join(SCRIPT_DIR, "bot.log")
LAST_RUN_FILE = os.path.join(SCRIPT_DIR, ".last_run")

# Faixa de commits por execução (mínimo, máximo) - "Médias e Fortes"
MIN_COMMITS = 4
MAX_COMMITS = 10

# Projetos falsos para modificação realista
PROJECT_FILES = [
    {
        "path": "src/parser.py",
        "type": "python",
        "messages": [
            "fix: patch regression in parser",
            "refactor: simplify logic flow",
            "fix: correct off-by-one error",
            "style: apply linter suggestions",
            "fix: handle null pointer exception",
        ]
    },
    {
        "path": "config/settings.json",
        "type": "json",
        "messages": [
            "chore: sync configuration files",
            "chore: update dependencies",
            "chore: bump version number",
            "chore: reorganize project structure",
        ]
    },
    {
        "path": "docs/setup.md",
        "type": "markdown",
        "messages": [
            "docs: update changelog",
            "docs: improve inline documentation",
            "docs: add usage examples",
            "style: format code for consistency",
        ]
    }
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def modify_file(file_info: dict) -> str:
    """Modifica levemente o arquivo para gerar um diff."""
    path = os.path.join(SCRIPT_DIR, file_info["path"])
    file_type = file_info["type"]
    
    if not os.path.exists(path):
        # Cria se não existir
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if file_type == "json":
            with open(path, "w") as f:
                json.dump({"version": "1.0.0", "last_updated": ""}, f)
        elif file_type == "python":
            with open(path, "w") as f:
                f.write("def parse(data):\n    pass\n\n# Rev: 0\n")
        elif file_type == "markdown":
            with open(path, "w") as f:
                f.write("# Setup\n\nInstruções...\n\n<!-- Rev: 0 -->\n")

    timestamp = datetime.now().isoformat()
    
    # Modificação real
    if file_type == "json":
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception:
            data = {"version": "1.0.0"}
        data["last_updated"] = timestamp
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            
    elif file_type == "python":
        with open(path, "r") as f:
            lines = f.readlines()
        with open(path, "w") as f:
            for line in lines:
                if line.startswith("# Rev:"):
                    f.write(f"# Rev: {timestamp}\n")
                else:
                    f.write(line)
                    
    elif file_type == "markdown":
        with open(path, "r") as f:
            lines = f.readlines()
        with open(path, "w") as f:
            for line in lines:
                if line.startswith("<!-- Rev:"):
                    f.write(f"<!-- Rev: {timestamp} -->\n")
                else:
                    f.write(line)

    return file_info["path"]


def git_pull() -> bool:
    """Sincroniza com o remoto antes de qualquer alteração."""
    result = subprocess.run(
        ["git", "pull", "--rebase", "--quiet"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log.warning("git pull falhou: %s", result.stderr.strip())
        return False
    return True


def git_commit(filepath: str, message: str) -> bool:
    subprocess.run(["git", "add", filepath], check=True)
    result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log.warning("git commit falhou: %s", result.stderr.strip())
        return False
    return True


def git_push() -> bool:
    result = subprocess.run(["git", "push"], capture_output=True, text=True)
    if result.returncode != 0:
        log.error("git push falhou: %s", result.stderr.strip())
        return False
    return True


def already_ran_today() -> bool:
    """Verifica se o bot já fez commits com sucesso hoje."""
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(LAST_RUN_FILE):
        with open(LAST_RUN_FILE, "r") as f:
            last_date = f.read().strip()
        return last_date == today
    return False


def save_run_date() -> None:
    """Salva a data de hoje como última execução bem-sucedida."""
    today = datetime.now().strftime("%Y-%m-%d")
    with open(LAST_RUN_FILE, "w") as f:
        f.write(today)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=" * 50)
    log.info("Bot iniciado.")

    # 1. Checa se já rodou hoje
    if already_ran_today():
        log.info("Bot já rodou hoje. Nada a fazer.")
        return

    # 2. Sincronizar com o remoto
    if not git_pull():
        log.error("Falha no git pull. Abortando para evitar conflitos.")
        return

    # 3. Quantidade aleatória de commits (fortes/médias)
    num_commits = random.randint(MIN_COMMITS, MAX_COMMITS)
    log.info("Commits planejados para hoje: %d", num_commits)

    commits_done = 0

    for i in range(num_commits):
        # Escolhe um arquivo aleatório do projeto falso
        file_info = random.choice(PROJECT_FILES)
        
        # Modifica o arquivo para gerar um diff
        filepath = modify_file(file_info)

        # Escolhe uma mensagem realista
        message = random.choice(file_info["messages"])
        
        if git_commit(filepath, message):
            commits_done += 1
            log.info("  [%d/%d] Commit OK — \"%s\" (%s)",
                     i + 1, num_commits, message, filepath)

    # 4. Push único com todos os commits
    if commits_done > 0:
        if git_push():
            log.info("Push realizado com sucesso (%d commits).", commits_done)
            save_run_date()
        else:
            log.error("Push falhou após %d commits.", commits_done)
    else:
        log.warning("Nenhum commit foi realizado.")

    log.info("Bot finalizado.")
    log.info("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.exception("Erro fatal: %s", e)
        exit(1)
