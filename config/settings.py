"""
Django settings for the CA Result Verification System.
"""

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ─────────────────────────────────────────────────────────────
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())

# ── Applications ─────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local apps
    "apps.accounts",
    "apps.courses",
    "apps.feedback",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.session_timeout",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ── Database ─────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.sqlite3"),
        "NAME": config("DB_NAME", default=BASE_DIR / "db.sqlite3"),
    }
}

# ── Custom user model ────────────────────────────────────────────────────
# Must be set before the first migration.
AUTH_USER_MODEL = "accounts.User"

# ── Password validation ──────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalization ─────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Static & media files ─────────────────────────────────────────────────
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Auth redirects ────────────────────────────────────────────────────────
LOGIN_URL = "student_login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "student_login"

# ── Email ────────────────────────────────────────────────────────────────
# Console backend for development: activation/password-setup links print
# straight to the terminal running `runserver`, no real SMTP needed while
# building. Swap EMAIL_BACKEND in .env when you're ready for real email.
# ── Email Configuration ───────────────────────────────────────────────

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend"
)

EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", cast=int)

EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")

EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)

DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default=EMAIL_HOST_USER
)

# ── Lecturer signup restriction ─────────────────────────────────────────
# Since there's no Admin to vet lecturer accounts individually, this is
# the only gate: only emails ending in this domain can register as a
# lecturer. Set to "" to disable the restriction (e.g. for local testing).
ALLOWED_LECTURER_EMAIL_DOMAIN = config("ALLOWED_LECTURER_EMAIL_DOMAIN", default="")


# ── Authentication backends ──────────────────────────────────────────────
# Our custom backend lets students log in with their registration number
# (looked up via StudentProfile) as well as email; lecturers keep using
# email since they have no reg number. ModelBackend stays listed as a
# fallback for anything (e.g. createsuperuser flows) that authenticates
# purely by email/password without going through this custom logic.
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.RegNumberOrEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]


# ── Session timeout ───────────────────────────────────────────────────────
# SESSION_COOKIE_AGE + SESSION_SAVE_EVERY_REQUEST together give a true
# IDLE timeout: every request resets the clock, so a person is only ever
# logged out after N minutes of no activity — not N minutes after they
# first logged in. SESSION_EXPIRE_AT_BROWSER_CLOSE additionally ends the
# session the moment the browser itself is closed, regardless of the
# timeout, since it makes the cookie a non-persistent "session cookie"
# rather than one that survives a restart.
SESSION_COOKIE_AGE = config("SESSION_TIMEOUT_MINUTES", default=15, cast=int) * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True