#!/usr/bin/env bash
set -e

echo "=================================================================="
echo "  REPRODUCING SOLARSCAN PRE-FEASIBILITY RESEARCH PAPER"
echo "=================================================================="

echo "[1/5] Running unit test suite..."
python -m pytest tests/

echo "[2/5] Building validation dataset and computing metrics..."
python experiments/build_validation_dataset.py
python experiments/run_validation.py
python experiments/run_sensitivity.py

echo "[3/5] Generating publication figures..."
python experiments/generate_figures.py

echo "[4/5] Generating publication tables..."
python experiments/generate_tables.py

echo "[5/5] Compiling IEEE conference manuscript..."
cd manuscript
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
cd ..

echo "=================================================================="
echo "[SUCCESS] Paper figures, tables, and PDF regenerated successfully!"
echo "Output PDF: manuscript/main.pdf"
echo "=================================================================="
