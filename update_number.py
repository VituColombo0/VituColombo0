#!/usr/bin/env python3
"""
GitHub Activity Bot — mantém o gráfico de contribuições ativo
com comportamento realista (dias de descanso, múltiplos commits,
mensagens variadas e horários aleatórios).
"""

import os
import random
import subprocess
import logging
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

NUMBER_FILE = "number.txt"
LOG_FILE = os.path.join(SCRIPT_DIR, "bot.log")

# Chance de pular o dia inteiro (simula dia de descanso) — 15%
SKIP_CHANCE = 0.15

# Faixa de commits por execução (mínimo, máximo)
MIN_COMMITS = 1
MAX_COMMITS = 5

# Mensagens de commit realistas (escolhidas aleatoriamente)
COMMIT_MESSAGES = [
    "refactor: clean up legacy code",
    "chore: update dependencies",
    "fix: resolve minor edge case",
    "docs: improve inline documentation",
    "style: format code for consistency",
    "chore: bump version number",
    "fix: correct off-by-one error",
    "refactor: simplify logic flow",
    "chore: remove unused imports",
    "docs: update changelog",
    "fix: handle null pointer exception",
    "style: normalize whitespace",
    "chore: sync configuration files",
    "refactor: extract utility function",
    "fix: patch regression in parser",
    "docs: add usage examples",
    "chore: reorganize project structure",
    "fix: resolve encoding issue",
    "style: apply linter suggestions",
    "refactor: improve error handling",
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

def read_number() -> int:
    with open(NUMBER_FILE, "r") as f:
        return int(f.read().strip())


def write_number(num: int) -> None:
    with open(NUMBER_FILE, "w") as f:
        f.write(str(num))


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


def git_commit(message: str) -> bool:
    subprocess.run(["git", "add", NUMBER_FILE], check=True)
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


def update_cron_with_random_time() -> None:
    """Reagenda a próxima execução para um horário aleatório amanhã."""
    random_hour = random.randint(0, 23)
    random_minute = random.randint(0, 59)

    new_entry = (
        f"{random_minute} {random_hour} * * * "
        f"cd {SCRIPT_DIR} && python3 {os.path.join(SCRIPT_DIR, 'update_number.py')}\n"
    )

    cron_tmp = "/tmp/current_cron"
    os.system(f"crontab -l > {cron_tmp} 2>/dev/null || true")

    with open(cron_tmp, "r") as f:
        lines = f.readlines()

    with open(cron_tmp, "w") as f:
        for line in lines:
            if "update_number.py" not in line:
                f.write(line)
        f.write(new_entry)

    os.system(f"crontab {cron_tmp}")
    os.remove(cron_tmp)

    log.info("Próxima execução agendada para %02d:%02d.", random_hour, random_minute)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=" * 50)
    log.info("Bot iniciado.")

    # 1. Dia de descanso?
    if random.random() < SKIP_CHANCE:
        log.info("Hoje é dia de descanso — nenhum commit será feito.")
        update_cron_with_random_time()
        return

    # 2. Sincronizar com o remoto
    if not git_pull():
        log.error("Falha no git pull. Abortando para evitar conflitos.")
        update_cron_with_random_time()
        return

    # 3. Quantidade aleatória de commits
    num_commits = random.randint(MIN_COMMITS, MAX_COMMITS)
    log.info("Commits planejados para hoje: %d", num_commits)

    current = read_number()
    commits_done = 0

    for i in range(num_commits):
        current += 1
        write_number(current)

        message = random.choice(COMMIT_MESSAGES)
        if git_commit(message):
            commits_done += 1
            log.info("  [%d/%d] Commit OK — \"%s\" (number=%d)",
                     i + 1, num_commits, message, current)

    # 4. Push único com todos os commits
    if commits_done > 0:
        if git_push():
            log.info("Push realizado com sucesso (%d commits).", commits_done)
        else:
            log.error("Push falhou após %d commits.", commits_done)
    else:
        log.warning("Nenhum commit foi realizado.")

    # 5. Reagendar para amanhã
    update_cron_with_random_time()

    log.info("Bot finalizado.")
    log.info("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.exception("Erro fatal: %s", e)
        # Mesmo com erro, tenta reagendar para não morrer para sempre
        try:
            update_cron_with_random_time()
        except Exception:
            pass
        exit(1)
