import json
from pathlib import Path

from app.config.models import RuntimeProviderConfig


class ProviderConfigStore:
    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path)

    def load(self) -> RuntimeProviderConfig:
        if not self.file_path.exists():
            default_config = RuntimeProviderConfig.default()
            self.save(default_config)
            return default_config

        raw = json.loads(self.file_path.read_text(encoding="utf-8"))
        return RuntimeProviderConfig.model_validate(raw)

    def save(self, config: RuntimeProviderConfig) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = config.model_dump(mode="json")
        self.file_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
