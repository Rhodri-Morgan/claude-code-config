.PHONY: install
install:
	./install.sh

.PHONY: install-full
install-full:
	./install.sh --session-state

.PHONY: install-vibe
install-vibe:
	./install.sh --vibe
