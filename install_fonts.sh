#!/usr/bin/env bash
set -e

FONT_SOURCE="./fonts"
FONT_TARGET="/usr/local/share/fonts/ces_custom"

echo "=== Instalando fuentes desde ${FONT_SOURCE} a ${FONT_TARGET} ==="

if [ ! -d "$FONT_SOURCE" ]; then
  echo "❌ No existe la carpeta ${FONT_SOURCE}. Nada que instalar."
  exit 1
fi

sudo mkdir -p "$FONT_TARGET"

sudo cp ${FONT_SOURCE}/*.ttf ${FONT_SOURCE}/*.otf "$FONT_TARGET" 2>/dev/null || true

echo "Reconstruyendo caché de fuentes..."
sudo fc-cache -f -v

echo "=== Fuentes instaladas correctamente ==="
