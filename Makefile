# KN Event Horizon developer entrypoints.
SHELL := /bin/bash
PROJECT_ROOT := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
VENV := $(PROJECT_ROOT)/.venv
PY := $(VENV)/bin/python
PYTHON_VERSION ?= 3.12
# DATA_DIR resolves as in the shell helpers (kn_load_env): from .env when it sets it, else from the
# environment, else .data, with a relative path from the project root. Recipes quote it.
DATA_ROOT := $(shell source "$(PROJECT_ROOT)/scripts/shared/common.sh" && kn_load_env && \
	printf '%s' "$$DATA_DIR")
$(if $(DATA_ROOT),,$(error cannot resolve DATA_DIR with scripts/shared/common.sh))
PYTEST_CACHE := -o "cache_dir=$(DATA_ROOT)/cache/pytest"
# GitHub Actions runs only the lightweight unit tests. Tests that need a service endpoint
# (integration) or large memory or a long run time (heavy) run only locally. tests/conftest.py
# defines the same expressions, and tests/deploy/test_ci_workflow.py checks that they agree.
UNIT_TESTS := not integration and not heavy
LOCAL_TESTS := integration or heavy
# pytest with the integration database of make db-up configured.
LOCAL_PYTEST = test -x "$(PY)" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }; \
	source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; kn_db_test_env || exit 1; \
	"$(PY)" -m pytest $(PYTEST_CACHE)
BILINGUAL_PYTEST = mkdir -p "$(DATA_ROOT)/e2e"; \
	artifact_dir=$$(mktemp -d "$(DATA_ROOT)/e2e/bilingual-XXXXXXXX") || exit 1; \
	"$(PY)" -m pytest $(PYTEST_CACHE) tests/e2e tests/i18n --e2e-artifacts "$$artifact_dir"

export RUFF_CACHE_DIR := $(DATA_ROOT)/cache/ruff
export MYPY_CACHE_DIR := $(DATA_ROOT)/cache/mypy

.DEFAULT_GOAL := help

.PHONY: help bootstrap venv lock run doctor format format-check lint typecheck test coverage \
	test-integration ci-local skos-reference-check \
	complexity-gate shell-lint-gate lint-md lint-doc-links lint-spec-plan plan-status \
	ci-checks ci ci-github build quality code-quality quality-report \
	db-up db-down db-reset db-verify

help: ## List available targets
	@awk 'BEGIN {FS = ":.*## "; print "Usage: make <target>\n"} /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: ## Create/update .venv from uv.lock, check host prerequisites, install pinned tools
	@command -v uv >/dev/null 2>&1 || { echo "ERROR: uv is required"; exit 1; }
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; \
		uv sync --locked --extra dev --python "$(PYTHON_VERSION)"
	@"$(PY)" -m kn.quality.prerequisites --root "$(PROJECT_ROOT)" --data-dir "$(DATA_ROOT)" --install

venv: bootstrap ## Alias for bootstrap

lock: ## Refresh uv.lock after dependency changes
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; uv lock

run: ## Run the kn project identity command
	@test -x "$(VENV)/bin/kn" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(VENV)/bin/kn" info

doctor: ## Verify required tools, files, and the installed package
	@command -v git >/dev/null
	@command -v uv >/dev/null
	@command -v make >/dev/null
	@test -f pyproject.toml -a -f uv.lock -a -f AGENTS.md
	@test -x "$(PY)" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(PY)" -c 'import kn; print(kn.project_info().distribution)'
	@"$(PY)" -m kn.quality.prerequisites --root "$(PROJECT_ROOT)" --data-dir "$(DATA_ROOT)"

format: ## Format production code and tests with Ruff
	@"$(VENV)/bin/ruff" format src tests
	@"$(VENV)/bin/ruff" check --fix src tests

format-check: ## Check Python formatting without changing files
	@"$(VENV)/bin/ruff" format --check src tests

lint: ## Run Ruff lint checks
	@"$(VENV)/bin/ruff" check src tests

typecheck: ## Run mypy over production code
	@"$(VENV)/bin/mypy" --python-version "$(PYTHON_VERSION)"

test: ## Run the lightweight unit tests, the set that GitHub Actions runs
	@"$(PY)" -m pytest $(PYTEST_CACHE) -m "$(UNIT_TESTS)"

coverage: ## Run the lightweight unit tests and enforce the coverage floor
	@"$(PY)" -m pytest $(PYTEST_CACHE) -m "$(UNIT_TESTS)" --cov=kn --cov-report=term-missing

test-integration: ## Run the database integration tests locally against make db-up
	@$(LOCAL_PYTEST) -m integration

complexity-gate: ## Fail on Radon D-or-worse or cognitive complexity above 15
	@output="$$($(VENV)/bin/radon cc src tests -s -n D)"; \
		if [ -n "$$output" ]; then printf '%s\n' "$$output"; exit 1; fi
	@mkdir -p "$(DATA_ROOT)/cache/complexipy"
	@cd "$(DATA_ROOT)/cache/complexipy"; \
		output="$$($(VENV)/bin/complexipy "$(PROJECT_ROOT)/src" "$(PROJECT_ROOT)/tests" \
		--max-complexity-allowed 15 --failed --ignore-complexity --color no --plain --sort desc)"; \
		if [ -n "$$output" ]; then printf '%s\n' "$$output"; exit 1; fi

shell-lint-gate: ## Check every tracked shell script with bash and ShellCheck
	@find scripts -type f -name '*.sh' -print0 | xargs -0 -r -n1 bash -n
	@find scripts -type f -name '*.sh' -print0 | \
		xargs -0 -r "$(VENV)/bin/shellcheck" -x -P SCRIPTDIR -S warning

lint-md: ## Lint repository Markdown and then validate relative links
	@"$(PY)" -m pymarkdown scan -r README.md AGENTS.md CLAUDE.md GEMINI.md docs
	@$(MAKE) --no-print-directory lint-doc-links

lint-doc-links: ## Check that relative Markdown links and anchors resolve
	@"$(PY)" -m kn.quality.doc_links --root "$(PROJECT_ROOT)"

lint-spec-plan: ## Check capability registry, plan tasks, and the closed-research register
	@"$(PY)" -m kn.quality.plan_integrity --root "$(PROJECT_ROOT)"
	@"$(PY)" -m kn.quality.research_register --root "$(PROJECT_ROOT)"

plan-status: ## Count tasks by lane/status and show declared priority
	@"$(PY)" -m kn.quality.plan_summary --root "$(PROJECT_ROOT)"

ci-checks: catalog-check contract-check format-check lint typecheck complexity-gate shell-lint-gate lint-doc-links lint-spec-plan

ci: ci-checks test ## Run the required gate: checks and lightweight unit tests

ci-github: ci ## GitHub Actions entrypoint, the same gate as make ci

ci-local: ci ## Run make ci, every local-only test (make db-up first) and the Jena SKOS check
	@$(LOCAL_PYTEST) -m "$(LOCAL_TESTS)"
	@$(MAKE) --no-print-directory skos-reference-check

skos-reference-check: ## Validate every SKOS export with the pinned Apache Jena RIOT (local only)
	@test -x "$(PY)" || { echo "ERROR: run 'make bootstrap' first"; exit 1; }
	@"$(PY)" -m kn.quality.skos_reference --root "$(PROJECT_ROOT)" --data-dir "$(DATA_ROOT)"

build: ## Build source and wheel distributions
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; uv build

quality: ci-checks coverage lint-md build ## Run the full local quality suite

code-quality: quality ## Alias for the full local quality suite

db-up: ## Start the local PostGIS database, wait for healthy, and apply the role bootstrap
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; kn_db_up

db-down: ## Stop the local database service and keep its data volume
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; kn_db_down

db-reset: ## Delete the local database volume and start the database from empty
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; kn_db_reset

db-verify: ## Probe schemas, roles, and privileges in the running database (rolled back)
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; kn_db_verify

quality-report: ## Report Python/shell files over the 250-line soft limit
	@find src tests scripts -type f \( -name '*.py' -o -name '*.sh' \) -print0 | \
		xargs -0 -r wc -l | awk '$$2 != "total" && $$1 > 250 {print}' | sort -nr

.PHONY: contract-check contract-compile satcom-validate satcom-import db-upgrade
contract-check: ## Validate open contracts and check committed generated/ output byte for byte
	@cd "$(PROJECT_ROOT)" && "$(VENV)/bin/kn" contract lint
	@cd "$(PROJECT_ROOT)" && "$(VENV)/bin/kn" contract compile --check

contract-compile: ## Refresh the committed generated/contracts/ output for review
	@cd "$(PROJECT_ROOT)" && "$(VENV)/bin/kn" contract compile

.PHONY: contract-toolchain-check
contract-toolchain-check: ## Run the locked external linter/exporter in an isolated tool environment
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; \
		mkdir -p "$$DATA_DIR/contract-toolchain"; \
		artifact_dir=$$(mktemp -d "$$DATA_DIR/contract-toolchain/check-XXXXXXXX") || exit 1; \
		tool=(uv run --locked --isolated --only-group contract-tools \
		--python "$(PYTHON_VERSION)" datacontract); \
		"$${tool[@]}" --version >"$$artifact_dir/version.txt" && \
		"$${tool[@]}" lint tests/contracts/fixtures/valid.yaml \
		--json-schema src/kn/contracts/resources/odcs-3.1.0.json --no-inline-references \
		--output-format json --output "$$artifact_dir/lint.json" && \
		"$${tool[@]}" export jsonschema tests/contracts/fixtures/valid.yaml \
		--output "$$artifact_dir/export.json"

satcom-validate: ## Validate the supplied SATCOM package without writing
	@"$(VENV)/bin/kn" space satcom validate "$(DATA_ROOT)/satcom_enriched_package"

satcom-import: ## Archive and import SATCOM into the governed database
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; \
		KN_DATABASE_URL="postgresql://postgres@127.0.0.1:$$(kn_db_host_port)/kn" \
		KN_DATABASE_PASSWORD_FILE="$$(kn_db_password_file)" \
		"$(VENV)/bin/kn" space satcom import "$(DATA_ROOT)/satcom_enriched_package" --data-dir "$(DATA_ROOT)"

db-upgrade: ## Apply Python platform policy and versioned Alembic migrations
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; kn_db_govern upgrade

.PHONY: db-rebuild
db-rebuild: ## Rebuild all disposable KN schemas (requires KN_ENVIRONMENT=development)
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; kn_db_govern rebuild

.PHONY: catalog-check test-bilingual bilingual-acceptance
catalog-check: ## Check interface catalog parity, placeholders, key usage, and CLI literals
	@"$(PY)" -m kn.quality.catalogs --root "$(PROJECT_ROOT)"

test-bilingual: ## Check available bilingual paths and save evidence under DATA_DIR/e2e
	@$(BILINGUAL_PYTEST)

bilingual-acceptance: ## Require full bilingual release acceptance; fail on open paths
	@$(BILINGUAL_PYTEST) --require-bilingual-release

.PHONY: seed-import seed-check
seed-import: ## Stage deterministic vocabulary seeds, fixtures, and row reconciliation for review
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; \
		"$(VENV)/bin/kn" vocabulary import-proposals --data-dir "$(DATA_ROOT)"

seed-check: ## Reconcile proposals and compare staged outputs with checked-in reviewed content
	@source "$(PROJECT_ROOT)/scripts/shared/common.sh"; kn_load_env; \
		"$(VENV)/bin/kn" vocabulary import-proposals --check --data-dir "$(DATA_ROOT)"
