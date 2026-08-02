# ============================================================
# Fit Tracker – DBMS Term Project
# THGA Bochum · Lecturer: Stephan Bökelmann
# ============================================================

LATEXMK := latexmk
OUTDIR := out
PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

FRONTEND_DIR := frontend
FRONTEND_VERSION := 0.1.2
FRONTEND_ARCH := amd64
FRONTEND_BUILD := $(FRONTEND_DIR)/dist/fittracker
FRONTEND_PKG := $(FRONTEND_DIR)/pkg
DEB_FILE := $(FRONTEND_DIR)/dist/fittracker-frontend_$(FRONTEND_VERSION)_$(FRONTEND_ARCH).deb

LMKFLAGS := -pdf -interaction=nonstopmode -halt-on-error \
            -cd -output-directory=../$(OUTDIR)

TEXENV := TEXINPUTS="$(CURDIR)/style:.:$$TEXINPUTS"
STYLE := style/thga-db.sty

vpath %.tex documentation

DOCS := user-manual developer-manual
ALL_PDF := $(addprefix $(OUTDIR)/, $(addsuffix .pdf, $(DOCS)))


# ---- Main targets -------------------------------------------

.PHONY: all docs schema test up down logs \
        frontend-sync frontend-run frontend-build \
        deb deb-info clean distclean help

all: docs

docs: $(ALL_PDF)

schema:
	plantuml -tsvg schema.puml

test:
	$(PYTHON) -m pytest -q tests
	cd $(FRONTEND_DIR) && uv run pytest -q

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api postgres


# ---- Frontend targets ---------------------------------------

frontend-sync:
	cd $(FRONTEND_DIR) && uv sync

frontend-run: frontend-sync
	cd $(FRONTEND_DIR) && uv run python -m fittracker_frontend

frontend-build: frontend-sync
	cd $(FRONTEND_DIR) && uv run pyinstaller \
		--name fittracker \
		--onedir \
		--windowed \
		--clean \
		--noconfirm \
		--paths src \
		src/fittracker_frontend/__main__.py

deb: frontend-build
	rm -rf $(FRONTEND_PKG)
	mkdir -p $(FRONTEND_PKG)/opt/fittracker
	mkdir -p $(FRONTEND_PKG)/usr/bin
	mkdir -p $(FRONTEND_PKG)/usr/share/applications
	cp -a $(FRONTEND_BUILD)/. $(FRONTEND_PKG)/opt/fittracker/
	ln -s /opt/fittracker/fittracker $(FRONTEND_PKG)/usr/bin/fittracker
	cp $(FRONTEND_DIR)/packaging/fittracker.desktop \
		$(FRONTEND_PKG)/usr/share/applications/fittracker.desktop
	rm -f $(DEB_FILE)
	fpm -s dir -t deb \
		--name fittracker-frontend \
		--version $(FRONTEND_VERSION) \
		--architecture $(FRONTEND_ARCH) \
		--description "Tkinter desktop frontend for the Fit Tracker REST API" \
		--maintainer "Ahmad Hoteit" \
		--license MIT \
		--url "https://github.com/wojak0/fittracker" \
		--depends libc6 \
		--depends libx11-6 \
		--depends libxext6 \
		--depends libxrender1 \
		--depends libxft2 \
		--depends libfontconfig1 \
		--package $(abspath $(DEB_FILE)) \
		-C $(FRONTEND_PKG) .

deb-info:
	dpkg-deb --info $(DEB_FILE)


# ---- LaTeX rules --------------------------------------------

$(OUTDIR):
	mkdir -p $(OUTDIR)

$(OUTDIR)/%.pdf: %.tex $(STYLE) | $(OUTDIR)
	$(TEXENV) $(LATEXMK) $(LMKFLAGS) $<


# ---- Clean up -----------------------------------------------

clean:
	rm -f $(addprefix $(OUTDIR)/, *.aux *.log *.fdb_latexmk *.fls *.out *.toc *.synctex.gz)
	rm -rf $(FRONTEND_DIR)/build $(FRONTEND_PKG)

distclean:
	rm -rf $(OUTDIR)
	rm -rf $(FRONTEND_DIR)/build
	rm -rf $(FRONTEND_DIR)/dist
	rm -rf $(FRONTEND_PKG)


# ---- Help ---------------------------------------------------

help:
	@echo "Available targets:"
	@echo "  all             – build all PDF documents"
	@echo "  docs            – build all PDF documents"
	@echo "  schema          – render schema.puml as schema.svg"
	@echo "  test            – run backend and frontend tests"
	@echo "  up              – build and start PostgreSQL + FastAPI"
	@echo "  down            – stop backend containers"
	@echo "  logs            – follow backend container logs"
	@echo "  frontend-sync   – install locked frontend dependencies"
	@echo "  frontend-run    – run the Tkinter frontend"
	@echo "  frontend-build  – create the PyInstaller executable"
	@echo "  deb             – build the Debian installer"
	@echo "  deb-info        – display Debian package metadata"
	@echo "  clean           – remove temporary build files"
	@echo "  distclean       – remove all generated outputs"
