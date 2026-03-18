# Claude Code Configuration

Claude Code configuration for projects. Contains custom skills, hooks, and settings.

### Third-Party Components

When installing any third-party component (skill, agent, command, plugin, etc.) from an external source:

1. **Install verbatim** — do not trim, rewrite, or modify third-party files. Use them exactly as provided by the author.
2. **Document in README.md** — add the component name, source URL, and a short description to the appropriate table (Third-Party Skills, Third-Party Agents, Required Plugins, etc.).
3. **Add permissions** — add the component to the `allow` list in `.claude/settings.json` so it can be invoked without prompting.
