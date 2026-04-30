#!/usr/bin/env python3
"""
Claude Code Context Monitor
Real-time context usage monitoring with visual indicators and session analytics
"""

import json
import sys
import os
import subprocess


def get_git_status():
    """Get git branch and change count for statusline."""
    try:
        # Check if inside a git repository
        subprocess.check_output(["git", "rev-parse", "--git-dir"], stderr=subprocess.DEVNULL)

        # Get current branch
        branch = subprocess.check_output(["git", "branch", "--show-current"], stderr=subprocess.DEVNULL).decode().strip()

        if not branch:
            return ""

        # Count changes
        changes = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL).decode().splitlines()

        change_count = len(changes)

        # Color logic
        if change_count > 0:
            color = "\033[31m"  # Red = dirty
            suffix = f" ({change_count})"
        else:
            color = "\033[32m"  # Green = clean
            suffix = ""

        return f" \033[90m|\033[0m {color}🌿 {branch}{suffix}\033[0m"

    except Exception:
        return ""


def get_directory_display(workspace_data):
    """Get directory display name."""
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


def get_session_metrics(cost_data):
    """Get session metrics display."""
    if not cost_data:
        return ""

    metrics = []

    # Cost
    cost_usd = cost_data.get("total_cost_usd", 0)
    if cost_usd > 0:
        if cost_usd >= 0.10:
            cost_color = "\033[31m"  # Red for expensive
        elif cost_usd >= 0.05:
            cost_color = "\033[33m"  # Yellow for moderate
        else:
            cost_color = "\033[32m"  # Green for cheap

        cost_str = f"{cost_usd*100:.0f}¢" if cost_usd < 0.01 else f"${cost_usd:.3f}"
        metrics.append(f"{cost_color}💰 {cost_str}\033[0m")

    # Duration
    duration_ms = cost_data.get("total_duration_ms", 0)
    if duration_ms > 0:
        minutes = duration_ms / 60000
        if minutes >= 30:
            duration_color = "\033[33m"  # Yellow for long sessions
        else:
            duration_color = "\033[32m"  # Green

        if minutes < 1:
            duration_str = f"{duration_ms//1000}s"
        else:
            duration_str = f"{minutes:.0f}m"

        metrics.append(f"{duration_color}⏱ {duration_str}\033[0m")

    return f" \033[90m|\033[0m {' '.join(metrics)}" if metrics else ""


def main():
    try:
        # Read JSON input from Claude Code
        data = json.load(sys.stdin)

        # Extract information
        model_name = data.get("model", {}).get("display_name", "Claude")
        workspace = data.get("workspace", {})
        cost_data = data.get("cost", {})

        # Build status components
        directory = get_directory_display(workspace)
        session_metrics = get_session_metrics(cost_data)
        git_status = get_git_status()

        model_display = f"\033[94m[{model_name}]\033[0m"

        # Combine all components
        status_line = f"{model_display} \033[93m📁 {directory}\033[0m{git_status}{session_metrics}"

        print(status_line)

    except Exception as e:
        # Fallback display on any error
        print(f"\033[94m[Claude]\033[0m \033[93m📁 {os.path.basename(os.getcwd())}\033[0m 🧠 \033[31m[Error: {str(e)[:20]}]\033[0m")


if __name__ == "__main__":
    main()
