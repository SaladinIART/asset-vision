# Asset-Vision — convenience Makefile
# Usage: make <target>
# Requires: WSL2 Ubuntu 22.04 with bash

.PHONY: install run sample clean help

help:            ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	    awk 'BEGIN{FS=":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:         ## Install system packages, Python venv, and dependencies
	bash scripts/install.sh

run:             ## Start the web dashboard (localhost:8100)
	bash scripts/run.sh

sample:          ## (Re)generate the bundled sample images
	. ~/asset-venv/bin/activate && python generate_samples.py

clean:           ## Remove the SQLite database and captured frames
	rm -rf data/assets.db data/frames/
	@echo "Cleaned data/. Run 'make run' to start fresh."
