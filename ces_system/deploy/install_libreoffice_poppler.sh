#!/usr/bin/env bash
set -e

echo "Actualizando paquetes..."
sudo apt update

echo "Instalando LibreOffice (para DOCX/PPTX/ODT/ODP -> PDF)..."
sudo apt install -y libreoffice

echo "Instalando Poppler (por si decides usar pdf2image en Linux)..."
sudo apt install -y poppler-utils

echo "Listo. LibreOffice y Poppler instalados en el sistema."
