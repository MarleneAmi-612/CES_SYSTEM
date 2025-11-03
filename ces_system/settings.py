from pathlib import Path
import os
import socket
from datetime import timedelta
from dotenv import load_dotenv
from csp import constants as csp
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def strtobool(s: str) -> bool:
    return str(s).strip().lower() in ("1", "true", "yes", "on")

DEBUG = strtobool(os.environ.get("DEBUG", "True"))
SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key")

if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = ["tu-dominio.com", "admin.tu-dominio.com"]
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(local_ip)
    except Exception:
        pass

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = str(BASE_DIR / "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "administracion.apps.AdministracionConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "axes",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "two_factor",
    "alumnos",
    "descarga",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "axes.middleware.AxesMiddleware",
    "alumnos.middleware.AlumnosSessionGuard",
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
                "csp.context_processors.nonce",
                "administracion.context_processors.csp_nonce",
            ],
        },
    },
]

WSGI_APPLICATION = "ces_system.wsgi.application"

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

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_AGE = 30 * 60
CSRF_COOKIE_HTTPONLY = True

SECURE_SSL_REDIRECT = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = [
    "https://tu-dominio.com",
    "https://admin.tu-dominio.com",
]
if DEBUG:
    CSRF_TRUSTED_ORIGINS += [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(hours=1)
AXES_RESET_ON_SUCCESS = True
AXES_USERNAME_FORM_FIELD = "email"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "INFO"},
        "axes.watch_login": {"handlers": ["console"], "level": "INFO"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", csp.NONCE, "https://cdn.jsdelivr.net"],
        "style-src": ["'self'", csp.NONCE, "https://fonts.googleapis.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com", "data:"],
        "img-src": ["'self'", "data:", "blob:"],
    },
    "EXCLUDE_URL_PREFIXES": ["/admin/"],
}

HCAPTCHA_SITE_KEY = os.environ.get("HCAPTCHA_SITE_KEY", "")
HCAPTCHA_SECRET_KEY = os.environ.get("HCAPTCHA_SECRET_KEY", "")
HCAPTCHA_THRESHOLD_FAILS = int(os.environ.get("HCAPTCHA_THRESHOLD_FAILS", "3"))

if HCAPTCHA_SITE_KEY:
    CONTENT_SECURITY_POLICY["DIRECTIVES"].setdefault("frame-src", ["'self'"])
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["frame-src"] += ["https://hcaptcha.com", "https://*.hcaptcha.com"]
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["script-src"] += ["https://hcaptcha.com", "https://*.hcaptcha.com"]

ADMIN_IP_ALLOWLIST_ENABLED = strtobool(os.environ.get("ADMIN_IP_ALLOWLIST_ENABLED", "False"))
ADMIN_IP_PROTECTED_PREFIXES = ("/administracion/",)
ADMIN_IP_ALLOWLIST = ["127.0.0.1"]

AUTH_USER_MODEL = "administracion.AdminUser"
DATABASE_ROUTERS = ["ces_system.routers.SimulationRouter"]

POPPLER_BIN = os.environ.get("POPPLER_BIN", "")
SOFFICE_BIN = os.environ.get("SOFFICE_BIN", "")
LIBREOFFICE_PATH = os.environ.get("LIBREOFFICE_PATH", "soffice")

LOGIN_URL = "administracion:login"
LOGIN_REDIRECT_URL = reverse_lazy("administracion:home")
LOGOUT_REDIRECT_URL = reverse_lazy("administracion:login")
