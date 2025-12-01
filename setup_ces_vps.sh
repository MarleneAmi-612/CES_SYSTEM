#!/usr/bin/env bash
set -e

echo "=== [CES_SYSTEM] Setup de dependencias en VPS (Ubuntu/Debian) ==="

# 1) Actualizar e instalar paquetes base
echo "[1/5] Actualizando paquetes..."
sudo apt-get update -y

echo "[2/5] Instalando dependencias del sistema..."
sudo apt-get install -y \
  python3 python3-venv python3-pip python3-dev build-essential \
  libffi-dev libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
  libjpeg-dev zlib1g-dev \
  poppler-utils \
  libreoffice \
  fonts-dejavu-core fonts-liberation \
  unzip

echo "✓ Paquetes base instalados."

# 2) Detectar rutas de LibreOffice y Poppler
echo "[3/5] Detectando rutas de LibreOffice y Poppler..."

SOFFICE_PATH="$(command -v soffice || true)"
POPPLER_PATH="/usr/bin"

echo "  SOFFICE_BIN: ${SOFFICE_PATH:-(no encontrado)}"
echo "  POPPLER_BIN: ${POPPLER_PATH}"

# 3) Crear archivo de entorno local (por ejemplo .env.server)
ENV_FILE=".env.server"

echo "[4/5] Escribiendo variables en ${ENV_FILE} (no sobreescribe .env local)..."

# Si no existe, lo creamos
if [ ! -f "${ENV_FILE}" ]; then
  cat > "${ENV_FILE}" <<EOF
# Entorno para VPS (producido por setup_ces_vps.sh)

DEBUG=False

# Rutas de binarios para conversiones
SOFFICE_BIN="${SOFFICE_PATH}"
POPPLER_BIN="${POPPLER_PATH}"

# Ajusta estas de acuerdo a tu BD/host real:
DJANGO_ALLOWED_HOSTS="*"

EOF
else
  echo "  ${ENV_FILE} ya existe, se agregan/actualizan SOFFICE_BIN y POPPLER_BIN..."
  # Elimina líneas anteriores si existen
  sed -i '/^SOFFICE_BIN=/d' "${ENV_FILE}" || true
  sed -i '/^POPPLER_BIN=/d' "${ENV_FILE}" || true
  # Añade al final
  {
    echo "SOFFICE_BIN=\"${SOFFICE_PATH}\""
    echo "POPPLER_BIN=\"${POPPLER_PATH}\""
  } >> "${ENV_FILE}"
fi

echo "✓ Variables de entorno actualizadas en ${ENV_FILE}"

# 4) Carpeta para fuentes personalizadas
echo "[5/5] Creando carpeta para fuentes personalizadas..."

CUSTOM_FONT_DIR="/usr/local/share/fonts/ces_custom"

sudo mkdir -p "${CUSTOM_FONT_DIR}"
sudo chmod 755 "${CUSTOM_FONT_DIR}"

echo "Carpeta de fuentes personalizada: ${CUSTOM_FONT_DIR}"
echo
echo "Ahora puedes copiar ahí las fuentes TTF/OTF que estés autorizado a usar."
echo "Ejemplo (desde tu proyecto, en una carpeta fonts/):"
echo "  sudo cp fonts/*.ttf \"${CUSTOM_FONT_DIR}\""
echo "  sudo fc-cache -f -v"

echo
echo "=== Setup CES_SYSTEM completado ==="
echo "Recuerda:"
echo "  - Usa ${ENV_FILE} en tu VPS (por ejemplo cargándolo antes de correr gunicorn)."
echo "  - Copia las fuentes necesarias a ${CUSTOM_FONT_DIR} y ejecuta: sudo fc-cache -f -v"
