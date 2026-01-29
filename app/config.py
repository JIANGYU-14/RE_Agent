from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent.parent / 'backend_stream/.env'
load_dotenv(dotenv_path=env_path)


@dataclass(frozen=True)
class Settings:
    project_name: str = "VeADK PaperAgent Backend"
    agentkit_base_url: str = ""
    agentkit_api_key: str = ""
    database_url: str = ""


settings = Settings(
    agentkit_base_url=os.getenv("AGENTKIT_BASE_URL", ""),
    agentkit_api_key=os.getenv("AGENTKIT_API_KEY", ""),
    database_url=os.getenv("DATABASE_URL", ""),
)
