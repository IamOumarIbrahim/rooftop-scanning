@echo off
setlocal enabledelayedexpansion
echo ==================================================================
echo   REPRODUCING SOLARSCAN PRE-FEASIBILITY RESEARCH PAPER
echo ==================================================================

set PYTHONPATH=%CD%

echo [1/5] Running unit test suite...
python -m pytest tests/
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Unit tests failed!
    exit /b !ERRORLEVEL!
)

echo [2/5] Building validation dataset and computing metrics...
python experiments\build_validation_dataset.py
if !ERRORLEVEL! NEQ 0 exit /b !ERRORLEVEL!
python experiments\run_validation.py
if !ERRORLEVEL! NEQ 0 exit /b !ERRORLEVEL!
python experiments\run_sensitivity.py
if !ERRORLEVEL! NEQ 0 exit /b !ERRORLEVEL!

echo [3/5] Generating publication figures...
python experiments\generate_figures.py
if !ERRORLEVEL! NEQ 0 exit /b !ERRORLEVEL!

echo [4/5] Generating publication tables...
python experiments\generate_tables.py
if !ERRORLEVEL! NEQ 0 exit /b !ERRORLEVEL!

echo [5/5] Compiling IEEE conference manuscript...
where pdflatex >nul 2>nul
if !ERRORLEVEL! NEQ 0 (
    echo [WARNING] pdflatex not found on PATH. Skipping PDF compilation.
    echo Figures and tables regenerated successfully.
    exit /b 0
)

pushd manuscript
pdflatex -interaction=nonstopmode main.tex >nul 2>nul
bibtex main >nul 2>nul
pdflatex -interaction=nonstopmode main.tex >nul 2>nul
pdflatex -interaction=nonstopmode main.tex
set LATEX_ERR=!ERRORLEVEL!
popd

if !LATEX_ERR! NEQ 0 (
    echo [ERROR] LaTeX compilation failed!
    exit /b !LATEX_ERR!
)

echo ==================================================================
echo [SUCCESS] Paper figures, tables, and PDF regenerated successfully!
echo Output PDF: manuscript\main.pdf
echo ==================================================================

