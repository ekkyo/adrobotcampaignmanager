from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    keitaro_base_url: str = ""
    keitaro_api_key: str = ""
    database_url: str = "sqlite:///./campaigns.db"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
