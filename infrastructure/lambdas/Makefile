SHELL := /bin/sh

UV ?= uv
UV_CACHE_DIR ?= $(CURDIR)/.uv-cache
UV_ENV := UV_CACHE_DIR=$(UV_CACHE_DIR)
PYTHON := $(UV_ENV) $(UV) run --no-sync python
DIST_DIR ?= $(CURDIR)/dist

.PHONY: build clean format lint package test

build: package

test:
	@set -e; \
	for tests in */tests; do \
		[ -d "$$tests" ] || continue; \
		has_tests=0; \
		for test_file in "$$tests"/test_*.py; do \
			[ -f "$$test_file" ] || continue; \
			has_tests=1; \
			break; \
		done; \
		if [ "$$has_tests" = "0" ]; then \
			echo "Skipping $$tests; no tests found"; \
			continue; \
		fi; \
		echo "Running tests in $$tests"; \
		$(PYTHON) -m unittest discover -s "$$tests" -p "test_*.py"; \
	done

lint:
	$(UV_ENV) $(UV) run --with ruff ruff check . --fix

format:
	$(UV_ENV) $(UV) run --with ruff ruff format .

package:
	@mkdir -p "$(DIST_DIR)"
	@set -e; \
	for src in */src; do \
		lambda_name=$${src%/src}; \
		if [ ! -f "$$src/create_link/handler.py" ] && [ ! -f "$$src/handler.py" ]; then \
			echo "Skipping $$lambda_name; no handler source found"; \
			continue; \
		fi; \
		echo "Packaging $$lambda_name"; \
		(cd "$$src" && zip -qr "$(DIST_DIR)/$$lambda_name.zip" . -x "*/__pycache__/*" "*.pyc"); \
	done

clean:
	rm -rf "$(DIST_DIR)"
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
