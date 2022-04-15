from typing import Optional
from pydantic import BaseSettings, Field, BaseModel

class AppConfig(BaseModel):
    '''Application Configuration. Which tickers and forms to track.'''

    TRACKED_FORMS: list[str] = [
        "S-3",
        "424B1",
        "424B2",
        "424B3",
        "424B4",
        "424B5",
        "S-1",
        "EFFECT",
        "S-3MEF",
        "S-1MEF",
        "F-1",
        "F-3",
        "F-1MEF",
        "F-3MEF",
        "S-3ASR",
        "F-3ASR",
        "8-K",
        "6-K",
        "RW"
        ]
    
    TRACKED_TICKERS: list[str] = [
        "CEI",
        "IMPP",
        "CHK",
        "RE",
        "CMA",
        "LUMN",
        "BLDR",
        "CUBE",
        "KOF",
        "KEP",
        "HAS",
        "LNC",
        "LAMR",
        "TAP",
        "SCI",
        "GGG",
        "RS",
        "EXAS",
        "MORN",
        "DVA",
        "GLPI",
        "REXR",
        "CLVT",
        "OTEX",
        "Y",
        "LYFT",
        "JLL",
        "TEVA",
        "WSO",
        "SNA",
        "GME",
        "RPM",
        "PCTY",
        "AAL",
        "BBQ"
    ]

class GlobalConfig(BaseSettings):
    """Global configurations."""

    # These variables will be loaded from the .env file. However, if
    # there is a shell environment variable having the same name,
    # that will take precedence.

    APP_CONFIG: AppConfig = AppConfig()

    # define global variables with the Field class
    ENV_STATE: Optional[str] = Field(None, env="ENV_STATE")

    # environment specific variables do not need the Field class
    
    DILUTION_DB_PASSWORD: Optional[str] = None
    DILUTION_DB_HOST: Optional[str] = None
    DILUTION_DB_PORT: Optional[int] = None
    DILUTION_DB_USER: Optional[str] = None
    DILUTION_DB_DATABASE_NAME: Optional[str] = None
    DILUTION_DB_CONNECTION_STRING = f"postgres://{DILUTION_DB_USER}:{DILUTION_DB_PASSWORD}@{DILUTION_DB_HOST}:{DILUTION_DB_PORT}/{DILUTION_DB_DATABASE_NAME}"



    USERS_DB_PASSWORD: Optional[str] = None
    USERS_DB_HOST: Optional[str] = None
    USERS_DB_PORT: Optional[int] = None
    USERS_DB_USER: Optional[str] = None
    USERS_DB_DATABASE_NAME: Optional[str] = None
    USERS_DB_CONNECTION_STRING: Optional[str] = None


    DOWNLOADER_ROOT_PATH: Optional[str] = None
    POLYGON_ROOT_PATH: Optional[str] = None
    POLYGON_OVERVIEW_FILES_PATH: Optional[str] = None
    POLYGON_API_KEY: Optional[str] = None
    SEC_USER_AGENT: Optional[str] = None

    class Config:
        """Loads the dotenv file."""

        env_file: str = "./main/configuration/secret.env"


class DevConfig(GlobalConfig):
    """Development configurations."""

    class Config:
        env_prefix: str = "DEV_"


class ProdConfig(GlobalConfig):
    """Production configurations."""

    class Config:
        env_prefix: str = "PROD_"


class FactoryConfig:
    """Returns a config instance dependending on the ENV_STATE variable."""

    def __init__(self, env_state: Optional[str]):
        self.env_state = env_state

    def __call__(self):
        if self.env_state == "dev":
            return DevConfig()

        elif self.env_state == "prod":
            return ProdConfig()


cnf = FactoryConfig(GlobalConfig().ENV_STATE)()

