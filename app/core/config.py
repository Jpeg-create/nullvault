from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    # Project tokens are meant to be embedded in another codebase's runtime
    # environment, so they default to a much longer lifetime than a normal
    # login token. One year, expressed in minutes.
    project_token_expire_minutes: int = 60 * 24 * 365
    encryption_key: str

    class Config:
        env_file = ".env"


settings = Settings()
