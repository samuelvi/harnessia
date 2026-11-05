.PHONY: prepare prepare-core prepare-instance prepare-all instance-create instance-attach instance-list space-create space-attach space-configure check \
	sources-clone sources-check sources-status sources-fetch sources-pull sources-reconcile test verify

ENGINE = PYTHONDONTWRITEBYTECODE=1 uv run --no-project --with 'PyYAML>=6,<7' python -m app

prepare:
	@if [ -z "$(INSTANCE)" ] || [ -z "$(SPACE)" ]; then echo "Usage: make prepare INSTANCE=<id> SPACE=<space-id>"; exit 2; fi
	@$(ENGINE) prepare --instance "$(INSTANCE)" --space "$(SPACE)"

prepare-core:
	@$(ENGINE) prepare-core

prepare-instance:
	@if [ -z "$(INSTANCE)" ]; then echo "Usage: make prepare-instance INSTANCE=<id>"; exit 2; fi
	@$(ENGINE) prepare-instance "$(INSTANCE)"

prepare-all:
	@if [ -n "$(INSTANCE)" ]; then echo "make prepare-all does not accept INSTANCE; use make prepare-instance INSTANCE=<id>"; exit 2; fi
	@$(ENGINE) prepare-all

instance-create:
	@if [ -z "$(INSTANCE)" ] || [ -z "$(INSTANCE_PATH)" ]; then echo "Usage: make instance-create INSTANCE=<id> INSTANCE_PATH=<path>"; exit 2; fi
	@$(ENGINE) instance create "$(INSTANCE)" "$(INSTANCE_PATH)"

instance-attach:
	@if [ -z "$(INSTANCE)" ] || [ -z "$(INSTANCE_PATH)" ]; then echo "Usage: make instance-attach INSTANCE=<id> INSTANCE_PATH=<path>"; exit 2; fi
	@$(ENGINE) instance attach "$(INSTANCE)" "$(INSTANCE_PATH)"

instance-list:
	@$(ENGINE) instance list

space-create:
	@if [ -z "$(INSTANCE)" ] || [ -z "$(SPACE)" ]; then echo "Usage: make space-create INSTANCE=<id> SPACE=<space-id>"; exit 2; fi
	@$(ENGINE) space create "$(INSTANCE)" "$(SPACE)"

space-attach:
	@if [ -z "$(INSTANCE)" ] || [ -z "$(SPACE)" ]; then echo "Usage: make space-attach INSTANCE=<id> SPACE=<space-id>"; exit 2; fi
	@$(ENGINE) space attach "$(INSTANCE)" "$(SPACE)"

space-configure:
	@if [ -z "$(INSTANCE)" ] || [ -z "$(SPACE)" ]; then echo "Usage: make space-configure INSTANCE=<id> SPACE=<space-id>"; exit 2; fi
	@$(ENGINE) space configure "$(INSTANCE)" "$(SPACE)"

check:
	@if [ -n "$(INSTANCE)" ]; then $(ENGINE) check --instance "$(INSTANCE)"; else $(ENGINE) check; fi

sources-clone:
	@$(ENGINE) sources-clone

sources-check:
	@$(ENGINE) sources-check

sources-status:
	@$(ENGINE) sources-status

sources-fetch:
	@$(ENGINE) sources-fetch

sources-pull:
	@$(ENGINE) sources-pull

sources-reconcile:
	@$(ENGINE) sources-reconcile

test:
	@PYTHONDONTWRITEBYTECODE=1 uv run --no-project --with 'PyYAML>=6,<7' python -m unittest discover -s tests

verify:
	@$(MAKE) --no-print-directory test
	@$(MAKE) --no-print-directory sources-check
	@$(MAKE) --no-print-directory check
