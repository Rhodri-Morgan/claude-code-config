.DEFAULT_GOAL := help
.PHONY: help install install-yes install-full

help: ## Show available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install this config into ~/.claude (prompts before replacing)
	./install.sh

install-yes: ## Install without the confirmation prompt (the install.sh prompt needs a tty, so agents need this)
	./install.sh --yes

install-full: ## Install and also merge transcripts, sessions and prompt history (~1.5 GB)
	./install.sh --session-state
