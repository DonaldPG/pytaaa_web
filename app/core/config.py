from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "pytaaa_web"
    
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "pytaaa_user"
    POSTGRES_PASSWORD: str = "pytaaa_pass"
    POSTGRES_DB: str = "pytaaa_db"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    # Enable SQL query logging (set to "true" for development)
    SQL_ECHO: bool = False

    class Config:
        case_sensitive = True
        env_file = ".env"

    def get_database_url(self) -> str:
        if self.SQLALCHEMY_DATABASE_URI:
            return self.SQLALCHEMY_DATABASE_URI
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

settings = Settings()
