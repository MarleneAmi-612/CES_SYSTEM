from pathlib import Path
import os
from datetime import timedelta

from dotenv import load_dotenv
import pymysql

# MySQL con PyMySQL
pymysql.install_as_MySQLdb()

# === Base ===
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def strtobool(s: str) -> bool:
    return str(s).strip().lower() in ("1", "true", "yes", "on")

DEBUG = strtobool(os.environ.get("DEBUG", "True"))
SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key")
ALLOWED_HOSTS = ["*"] if DEBUG else ["tu-dominio.com", "admin.tu-dominio.com"]

# === Archivos de usuario ===
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# === Internacionalización ===
LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

# === Static ===
STATIC_URL = "static/"
# En producción puedes configurar:
# STATIC_ROOT = BASE_DIR / "staticfiles"

# === Claves primarias ===
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === Apps ===
INSTALLED_APPS = [
    "administracion.apps.AdministracionConfig",  # <-- primero

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'django.contrib.humanize',
    "axes",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "two_factor",
    "csp",

    "alumnos",
    "descarga",
]


# === Middleware (orden importa) ===
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "axes.middleware.AxesMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "alumnos.middleware.AlumnosSessionGuard",

    "django_otp.middleware.OTPMiddleware",

    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "ces_system.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ces_system.wsgi.application"

# === DB ===
def normalize_host(h: str) -> str:
    return "127.0.0.1" if (h or "").strip().lower() == "localhost" else h

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "ces_db"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": normalize_host(os.environ.get("DB_HOST", "127.0.0.1")),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4", "sql_mode": "STRICT_TRANS_TABLES"},
    },
    "ces": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("SIM_DB_NAME", "ces_simulacion"),
        "USER": os.environ.get("SIM_DB_USER", "root"),
        "PASSWORD": os.environ.get("SIM_DB_PASSWORD", ""),
        "HOST": normalize_host(os.environ.get("SIM_DB_HOST", "127.0.0.1")),
        "PORT": os.environ.get("SIM_DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4", "sql_mode": "STRICT_TRANS_TABLES"},
    },
}

# === Seguridad: cookies y sesión ===
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 60 * 30        # 30 min
SESSION_SAVE_EVERY_REQUEST = True   # sliding expiration

# === Seguridad: transporte (solo en PROD) ===
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# === CSRF trusted origins (con esquema) ===
CSRF_TRUSTED_ORIGINS = [
    "https://tu-dominio.com",
    "https://admin.tu-dominio.com",
]

# === Password policy fuerte ===
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# === Backends de autenticación ===
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# === Axes (antifuerza bruta) ===
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(hours=1)  # usar timedelta (recomendado)
AXES_RESET_ON_SUCCESS = True

# === Logging básico ===
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "INFO"},
        "axes.watch_login": {"handlers": ["console"], "level": "INFO"},
    },
}

# === CSP (Content Security Policy) — Formato 4.x ===
# Usamos NONCE automáticamente en plantillas con {{ csp_nonce }}
from csp.constants import NONCE

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", NONCE],
        "style-src": ["'self'", "https://fonts.googleapis.com", NONCE],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "frame-ancestors": ["'none'"],
        # "frame-src" se añadirá si activas hCaptcha
    }
}

# hCaptcha (si lo usas en el login)
HCAPTCHA_SITE_KEY = os.environ.get("HCAPTCHA_SITE_KEY", "")
HCAPTCHA_SECRET_KEY = os.environ.get("HCAPTCHA_SECRET_KEY", "")
HCAPTCHA_THRESHOLD_FAILS = 3

# Permite los dominios de hCaptcha si está activo
if HCAPTCHA_SITE_KEY:
    CONTENT_SECURITY_POLICY["DIRECTIVES"].setdefault("script-src", ["'self'", NONCE])
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["script-src"] += [
        "https://hcaptcha.com",
        "https://*.hcaptcha.com",
    ]
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["frame-src"] = [
        "'self'",
        "https://hcaptcha.com",
        "https://*.hcaptcha.com",
    ]

# === Opcional: Allowlist por IP para /administracion/ ===
ADMIN_IP_ALLOWLIST_ENABLED = strtobool(os.environ.get("ADMIN_IP_ALLOWLIST_ENABLED", "False"))
ADMIN_IP_PROTECTED_PREFIXES = ("/administracion/",)
ADMIN_IP_ALLOWLIST = [
    "127.0.0.1",    # añade tu IP pública/VPN aquí
    # "X.X.X.X",
]

# === URLs de login/redirect (útil para flujos de admin propio) ===
LOGIN_URL = "two_factor:login"
LOGIN_REDIRECT_URL = "/administracion/"
LOGOUT_REDIRECT_URL = "/administracion/acceso/"
LOGIN_URL = "administracion:login"
LOGIN_REDIRECT_URL = "/administracion/"

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"] 
STATIC_ROOT = str(BASE_DIR / "staticfiles") 

# Cookies de sesión “más seguras”
SESSION_COOKIE_AGE = 30 * 60            # 30 min
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'         # evita CSRF de 3ros

# CSRF cookies
CSRF_COOKIE_HTTPONLY = True
CSRF_USE_SESSIONS = False

# En producción:
# SECURE_SSL_REDIRECT = True
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True

AUTH_USER_MODEL = "administracion.AdminUser"
AXES_USERNAME_FORM_FIELD = "email"
