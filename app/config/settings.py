import logging

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(override=True)


class Settings(BaseSettings):
    ENVIRONTMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 5000

    INSTAGRAM_VERIFY_TOKEN: str = ""
    INSTAGRAM_ACCESS_TOKEN: str = ""
    INSTAGRAM_USER_ID: str = ""

    CONSUMER_KEY: str = ""
    CONSUMER_SECRET: str = ""
    AGENTFORCE_AGENT_ID: str = ""
    AGENTFORCE_ORG_ID: str = ""

    AWS_ACCESS_KEY_ID: str = ""
    AWS_ACCESS_SECRET_ID: str = ""
    AWS_REGION: str = ""
    BUCKET_NAME: str = ""

    AUCTION_BOT_OAUTH_TOKEN: str = ""
    AUCTION_BOT_SIGNING_SECRET: str = ""
    SLACK_WORKSPACE: str = ""
    SLACK_TEAM_ID: str = ""
    SLACK_ADMIN_TOKEN:str = ""
    MONGOURI: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
        validate_default=False,
    )


settings = None
try:
    settings = Settings()
    env = settings.ENVIRONTMENT.lower()
    log_level = logging.DEBUG if env == "development" else logging.INFO

    formatter = logging.Formatter(fmt="%(levelname)s: %(name)s: %(message)s")

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.basicConfig(level=log_level, handlers=[handler])

    log = logging.getLogger("settings")
    log.info("✅ All environment variables loaded successfully!")
except Exception as e:
    print(f"Error : {str(e)}")
