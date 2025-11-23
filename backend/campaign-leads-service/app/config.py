from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str
    PORT: int
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str

    class Config:
        env_file = ".env"


settings = Settings()
