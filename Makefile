.PHONY: install
install:
	./install.sh

.PHONY: install-yes
install-yes:
	./install.sh --yes

.PHONY: install-full
install-full:
	./install.sh --session-state
