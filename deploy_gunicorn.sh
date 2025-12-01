#!/usr/bin/env bash
set -e

#########################################
# CES_SYSTEM · Deploy rápido con Gunicorn
#########################################

# Nombre del módulo WSGI (en tu proyecto es ces_system)
PROJECT_NAME="ces_system"

# Rutas base
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$BASE_DIR/.venv"
ENV_FILE="$BASE_DIR/.env"
SERVER_ENV_FILE="$BASE_DIR/.env.server"
REQUIREMENTS_FILE="$BASE_DIR/requirements.txt"

# Config Gunicorn
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN_BIND="${GUNICORN_BIND:-0.0.0.0:8000}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "=== [CES_SYSTEM] Deploy con Gunicorn ==="
echo "Base:         $BASE_DIR"
echo "Virtualenv:   $VENV_DIR"
echo ".env:         $ENV_FILE"
echo ".env.server:  $SERVER_ENV_FILE"
echo

#########################################
# 1) Cargar variables de entorno
#########################################

if [ -f "$ENV_FILE" ]; then
  echo "[1/5] Cargando variables desde .env"
  set -a
  . "$ENV_FILE"
  set +a
else
  echo "⚠ No se encontró .env en $ENV_FILE (asegúrate de subirlo al VPS)."
fi

if [ -f "$SERVER_ENV_FILE" ]; then
  echo "[1b/5] Cargando overrides desde .env.server"
  set -a
  . "$SERVER_ENV_FILE"
  set +a
else
  echo "(Opcional) No se encontró .env.server, usando solo .env"
fi
echo

#########################################
# 2) Crear/activar entorno virtual
#########################################

if [ ! -d "$VENV_DIR" ]; then
  echo "[2/5] Creando entorno virtual en $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
fi

echo "[2b/5] Activando entorno virtual..."
. "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip

if [ -f "$REQUIREMENTS_FILE" ]; then
  echo "[2c/5] Instalando dependencias de $REQUIREMENTS_FILE ..."
  pip install -r "$REQUIREMENTS_FILE"
else
  echo "⚠ No se encontró requirements.txt, asegúrate de instalar las libs manualmente."
fi
echo

#########################################
# 3) Migraciones y collectstatic
#########################################

echo "[3/5] Ejecutando migraciones..."
python manage.py migrate --noinput

echo "[4/5] Ejecutando collectstatic..."
python manage.py collectstatic --noinput
echo

#########################################
# 4) Arrancar Gunicorn
#########################################

echo "[5/5] Lanzando Gunicorn..."
echo "  Workers : $GUNICORN_WORKERS"
echo "  Bind    : $GUNICORN_BIND"
echo "  Timeout : $GUNICORN_TIMEOUT"
echo "  App     : ${PROJECT_NAME}.wsgi:application"
echo

exec gunicorn \
  --workers "$GUNICORN_WORKERS" \
  --bind "$GUNICORN_BIND" \
  --timeout "$GUNICORN_TIMEOUT" \
  --access-logfile - \
  --error-logfile - \
  "${PROJECT_NAME}.wsgi:application"
