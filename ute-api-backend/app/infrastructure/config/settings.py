from pathlib import Path
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


# Configuracion de conexion a la base de datos
class DBSettings(BaseSettings):
    user: str = ""
    password: str = ""
    host: str = "localhost"
    port: int = 5432
    name: str = ""
    appname: str = "ute_api"
    min_size: int = 1
    max_size: int = 5
    timeout_qry: float = 5.0
    timeout_conn: int = 10
    connect: bool = True

    model_config = SettingsConfigDict(
        env_prefix="DB_", env_file=_PROJECT_ROOT / ".env", extra="ignore"
        )

    # Arma el DSN de conexion a Postgres con credenciales escapadas
    @property
    def db_dsn(self) -> str:
        return (
            f"postgresql://{quote(self.user, safe='')}:"
            f"{quote(self.password, safe='')}"
            f"@{self.host}:{self.port}/{self.name}"
        )


# Configuracion general de la aplicacion
class Settings(BaseSettings):
    app_name: str = "API Portal UTE"
    server_port: int = 8000
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    gmail_credentials_path: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    drive_folder_dual: str = ""
    # C10A: almacenamiento de archivos. `drive` es el del piloto; `local` y `memoria` son solo para
    # desarrollo, regresión y pruebas (el piloto no guarda archivos de forma local).
    almacenamiento: str = "drive"
    drive_carpeta_id: str = ""
    drive_token_file: str = "/secretos/drive_token.json"
    frontend_url: str = "http://localhost:5173"

    cors_origins: str = (
        "http://localhost:5173"
    )
    log_format: str = "text"
    sentry_dsn: str = ""

    model_config = SettingsConfigDict(env_file=_PROJECT_ROOT / ".env", extra="ignore")

    # Resuelve la ruta absoluta de credentials.json
    @property
    def gmail_creds_resolved(self) -> str:
        raw = self.gmail_credentials_path.strip()
        if not raw:
            raw = "credentials.json"
        p = Path(raw)
        if p.is_absolute():
            return str(p)
        return str(_PROJECT_ROOT / p)

    # Ruta absoluta al directorio de uploads duales temporales
    @property
    def dual_upload_dir(self) -> str:
        return str(_PROJECT_ROOT / "uploads" / "dual")

    # Instancia de configuracion de base de datos
    @property
    def db(self) -> DBSettings:
        return DBSettings()


settings = Settings()
