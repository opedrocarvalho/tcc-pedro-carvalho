from datetime import timedelta

SQLALCHEMY_DATABASE_URI = (
    "postgresql+psycopg2://pipeline:pipeline@postgres/superset"
)

SECRET_KEY = "pipeline_superset_secret_key_change_in_production"

BABEL_DEFAULT_LOCALE = "pt_BR"
BABEL_DEFAULT_FOLDER = "superset/translations"

PERMANENT_SESSION_LIFETIME = timedelta(days=30)
WTF_CSRF_TIME_LIMIT = None
SESSION_COOKIE_SAMESITE = "Lax"
