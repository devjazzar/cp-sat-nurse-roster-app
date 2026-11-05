"""Settings come from the environment; deploy/.env.example lists every variable."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is not set; see deploy/.env.example")
    return value


DEBUG = os.environ.get("DJANGO_DEBUG", "") == "1"
SECRET_KEY = required("SECRET_KEY")

# With a domain only that name is served. Without one the hospital reaches the server by
# whatever IP or name it has, behind Caddy's self-signed certificate. Loopback is always
# allowed for the container's own health check.
DOMAIN = os.environ.get("DOMAIN", "")
ALLOWED_HOSTS = [DOMAIN, "localhost", "127.0.0.1"] if DOMAIN else ["*"]
CSRF_TRUSTED_ORIGINS = [f"https://{DOMAIN}"] if DOMAIN else []
if DEBUG:  # Vite's proxy does not pass the browser's Host on, so Django cannot match the Origin itself
    CSRF_TRUSTED_ORIGINS.append("http://localhost:5173")

# Caddy terminates TLS; `web` publishes no port, so this header can only come from Caddy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

INSTALLED_APPS = [
    "django.contrib.postgres",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "ninja",
    "procrastinate.contrib.django",
    "accounts",
    "audit",
    "hospital",
    "units",
    "nurses",
    "ops",
    "rosters",
    "solves",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "accounts.sessions.IdleAwareSessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "NAME": os.environ.get("POSTGRES_DB", "nurse_roster"),
        "USER": os.environ.get("POSTGRES_USER", "nurse_roster"),
        "PASSWORD": required("POSTGRES_PASSWORD"),
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
     "OPTIONS": {"user_attributes": ("username", "full_name")}},
]

# Twelve idle hours: every request a signed-in browser makes pushes the expiry forward, so anything
# that polls on a timer has to say it is not activity (`accounts.sessions.not_activity`), or an open
# tab would never expire.
SESSION_COOKIE_AGE = 12 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = True

USE_TZ = True
TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Riyadh")
LANGUAGE_CODE = "en"

SOLVER_URL = os.environ.get("SOLVER_URL", "http://solver:8080")
SOLVER_TOKEN = required("SOLVER_TOKEN")

# Uploads stay in memory and never reach a temporary file: the nurse import's CSV holds names and genders. One
# over FILE_UPLOAD_MAX_MEMORY_SIZE is dropped, so it arrives as no file at all. Nothing else here takes an upload.
FILE_UPLOAD_HANDLERS = ["django.core.files.uploadhandler.MemoryFileUploadHandler"]

BACKUPS_DIR = Path(os.environ.get("BACKUPS_DIR", "/backups"))

# The compiled SPA, copied into the image at build time. Absent in development, where Vite
# serves it. WhiteNoise serves its files; config.urls answers every other path with index.html.
SPA_DIR = Path(os.environ.get("SPA_DIR", BASE_DIR.parent / "spa"))
WHITENOISE_ROOT = SPA_DIR if SPA_DIR.is_dir() else None
WHITENOISE_MAX_AGE = 3600
WHITENOISE_IMMUTABLE_FILE_TEST = r"^assets/"
WHITENOISE_AUTOREFRESH = DEBUG
