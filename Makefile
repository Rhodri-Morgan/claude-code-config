.PHONY: install
install:
	./install.sh

.PHONY: install-yes
install-yes:
	./install.sh --yes

.PHONY: install-full
install-full:
	./install.sh --session-state

.PHONY: install-full-yes
install-full-yes:
	./install.sh --session-state --yes
