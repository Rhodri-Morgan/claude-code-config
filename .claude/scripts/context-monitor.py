#!/usr/bin/env python3
"""
Claude Code status line: model, folder and git status
"""

import json
import sys
import os
import subprocess


def get_git_status():
    """Get git branch and change count for statusline."""
    try:
        subprocess.check_output(["git", "rev-parse", "--git-dir"], stderr=subprocess.DEVNULL)

        branch = subprocess.check_output(["git", "branch", "--show-current"], stderr=subprocess.DEVNULL).decode().strip()

        if not branch:
            return ""

        changes = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL).decode().splitlines()

        change_count = len(changes)

        if change_count > 0:
            color = "\033[31m"
            suffix = f" ({change_count})"
        else:
            color = "\033[32m"
            suffix = ""

        return f" \033[90m|\033[0m {color}🌿 {branch}{suffix}\033[0m"

    except Exception:
        return ""


def get_directory_display(workspace_data):
    current_dir = workspace_data.get("current_dir", "")
    project_dir = workspace_data.get("project_dir", "")

    if current_dir and project_dir:
        if current_dir.startswith(project_dir):
            rel_path = current_dir[len(project_dir) :].lstrip("/")
            return rel_path or os.path.basename(project_dir)
        else:
            return os.path.basename(current_dir)
    elif project_dir:
        return os.path.basename(project_dir)
    elif current_dir:
        return os.path.basename(current_dir)
    else:
        return "unknown"


def tag_herdr_cwd(workspace_data):
    """Herdr (Windows) can't see a WSL agent's folder; label its terminal with Claude's cwd via hc at $HERDR_HC."""
    hc, terminal, cwd = os.environ.get("HERDR_HC"), os.environ.get("HC_TERMINAL_ID"), workspace_data.get("current_dir")
    if not hc or not terminal or not cwd:
        return
    cache = f"/tmp/herdr-cwd-{terminal}"
    try:
        with open(cache) as f:
            if f.read() == cwd:
                return
    except OSError:
        pass
    with open(cache, "w") as f:
        f.write(cwd)
    subprocess.Popen([hc, "label", terminal, f"cwd={cwd}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    try:
        data = json.load(sys.stdin)

        model_name = data.get("model", {}).get("display_name", "Claude")
        workspace = data.get("workspace", {})
        tag_herdr_cwd(workspace)

        directory = get_directory_display(workspace)
        git_status = get_git_status()

        model_display = f"\033[94m[{model_name}]\033[0m"

        status_line = f"{model_display} \033[93m📁 {directory}\033[0m{git_status}"

        print(status_line)

    except Exception as e:
        print(f"\033[94m[Claude]\033[0m \033[93m📁 {os.path.basename(os.getcwd())}\033[0m 🧠 \033[31m[Error: {str(e)[:20]}]\033[0m")


if __name__ == "__main__":
    main()
