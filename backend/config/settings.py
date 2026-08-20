import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change-this-local-development-key")
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,my.gdtumn.com").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,https://my.gdtumn.com").split(",") if origin.strip()]
INSTALLED_APPS = ["django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "portfolio"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware", "config.security.SecurityHeadersMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default":{"ENGINE":os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),"NAME":os.environ.get("DATABASE_NAME", BASE_DIR / "db.sqlite3")}}
AUTH_PASSWORD_VALIDATORS = [{"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},{"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator"}]
LANGUAGE_CODE="en-us"; TIME_ZONE="UTC"; USE_I18N=True; USE_TZ=True
STATIC_URL="static/"; MEDIA_URL="media/"; MEDIA_ROOT=BASE_DIR / "media"; DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
SESSION_COOKIE_HTTPONLY=True; SESSION_COOKIE_SAMESITE="Lax"; SESSION_COOKIE_SECURE=not DEBUG; CSRF_COOKIE_SECURE=not DEBUG; CSRF_COOKIE_SAMESITE="Lax"
SECURE_CONTENT_TYPE_NOSNIFF=True; X_FRAME_OPTIONS="DENY"; SECURE_REFERRER_POLICY="same-origin"; SECURE_HSTS_SECONDS=31_536_000 if not DEBUG else 0; SECURE_HSTS_INCLUDE_SUBDOMAINS=not DEBUG; SECURE_HSTS_PRELOAD=not DEBUG
FILE_UPLOAD_MAX_MEMORY_SIZE=4 * 1024 * 1024
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "portfolio-rate-limits"}}
CHAT_SESSION_HOURS = 168
CHAT_RATE_LIMITS = {"join": (5, 15 * 60), "message": (30, 60), "upload": (10, 10 * 60), "owner": (60, 60)}
SCHEDULE_SESSION_HOURS = 30 * 24
SCHEDULE_RATE_LIMITS = {"event": (60, 10 * 60), "participant": (10, 10 * 60), "availability": (20, 10 * 60), "owner": (60, 60)}
WHEEL_SESSION_HOURS = 30 * 24
WHEEL_RATE_LIMITS = {"participant": (10, 10 * 60), "option": (30, 10 * 60), "spin": (12, 10 * 60), "owner": (60, 60)}
