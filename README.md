# Claude Code Config

Personal Claude Code configuration.

## Third-Party Skills

| Skill                       | Source                                                                                        | Description                                                   |
| --------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `openlogs-server-logs`      | [charlietlamb/openlogs](https://github.com/charlietlamb/openlogs)                             | Fetch and inspect local server logs via `openlogs tail`       |
| `pytorch-lightning`         | [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) | Deep learning with PyTorch Lightning                          |
| `scikit-learn`              | [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) | Machine learning with scikit-learn                            |
| `statistical-analysis`      | [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) | Guided statistical analysis with test selection and reporting |
| `literature-review`         | [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) | Systematic literature reviews across academic databases       |
| `shannon`                   | [unicodeveloper/shannon](https://github.com/unicodeveloper/shannon)                           | Autonomous AI pentester for web apps and APIs                 |

## Third-Party Agents

| Agent              | Source                                                                                                           | Description                                          |
| ------------------ | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `code-reviewer`    | [claude-code-templates](https://www.npmjs.com/package/claude-code-templates) (`development-tools/code-reviewer`) | Senior code reviewer for quality, security, and perf |
| `security-auditor` | [claude-code-templates](https://www.npmjs.com/package/claude-code-templates) (`security/security-auditor`)       | Security auditor for vulnerability analysis          |
| `data-scientist`   | [claude-code-templates](https://www.npmjs.com/package/claude-code-templates) (`data-ai/data-scientist`)          | Data science agent with access to all DS skills      |

## MCP Servers (Docker Toolkit)

MCP servers are provided via [MCP Toolkit by Docker](https://github.com/docker/mcp-toolkit). Install Docker Desktop and enable the MCP Toolkit extension, then configure servers through the Docker Desktop UI.

| Server            | Description                                                 |
| ----------------- | ----------------------------------------------------------- |
| AWS Documentation | Search AWS and AWSCC Terraform provider docs and IA modules |
| AWS Terraform     | Execute Terraform/Terragrunt commands and run Checkov scans |
| Context7          | Library documentation and code examples lookup              |
| GitHub Official   | Issues, PRs, commits, code search, repository management    |

## Required Plugins

These plugins must be installed manually after cloning:

```bash
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem

/plugin marketplace add warpdotdev/claude-code-warp
/plugin install warp@claude-code-warp
```

## ZSH Configuration

Add the following to `~/.zshrc` to launch Claude Code with different config directories:

```bash
cc() {
    CLAUDE_CONFIG_DIR=$REPOS/claude-config/.claude \
    claude --dangerously-skip-permissions "$@"
}
```
