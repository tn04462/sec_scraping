from os import PathLike
from typing import Optional
from pydantic import BaseSettings, Field, BaseModel

class AppConfig(BaseModel):
    '''Application Configuration. Which tickers and forms to track.'''

    TRACKED_FORMS: list[str] = [
        "S-3",
        "EFFECT",
        # "8-K",
        # "6-K",
        "RW"
        # "424B1",
        # "424B2",
        # "424B3",
        # "424B4",
        # "424B5",
        # "S-1",
        ]
    
    TRACKED_TICKERS: list[str] = [
        "CEI",
        "IMPP",
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
    DILUTION_DB_CONNECTION_STRING: Optional[str] = None



    USERS_DB_PASSWORD: Optional[str] = None
    USERS_DB_HOST: Optional[str] = None
    USERS_DB_PORT: Optional[int] = None
    USERS_DB_USER: Optional[str] = None
    USERS_DB_DATABASE_NAME: Optional[str] = None
    USERS_DB_CONNECTION_STRING: Optional[str] = None


    DEFAULT_LOGGING_FILE: str or PathLike = None
    DOWNLOADER_ROOT_PATH: Optional[str] = None
    POLYGON_ROOT_PATH: Optional[str] = None
    POLYGON_OVERVIEW_FILES_PATH: Optional[str] = None
    POLYGON_API_KEY: Optional[str] = None
    SEC_USER_AGENT: Optional[str] = None
    

    class Config:
        """Loads the dotenv file."""
        env_file: str = r"./main/configuration/secret.env"

class TestConfig(GlobalConfig):
    """Testing configurations."""
    class Config:
        env_prefix: str = "TEST_"
    ENV_STATE = "test"


class DevConfig(GlobalConfig):
    """Development configurations."""

    class Config:
        env_prefix: str = "DEV_"
    ENV_STATE = "dev"


class ProdConfig(GlobalConfig):
    """Production configurations."""

    class Config:
        env_prefix: str = "PROD_"
    ENV_STATE = "prod"

class FactoryConfig:
    """Returns a config instance depending on the ENV_STATE variable."""

    def __init__(self, env_state: Optional[str]):
        self.env_state = env_state

    def __call__(self):
        if self.env_state == "dev":
            return DevConfig()

        elif self.env_state == "prod":
            return ProdConfig()
        
        elif self.env_state == "test":
            return TestConfig()


cnf = FactoryConfig("test")()
