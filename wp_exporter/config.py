from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ExportConfig:
    base_url: str
    output_path: Path
    output_format: str
    token: str | None = None
    username: str | None = None
    application_password: str | None = None
    timeout_seconds: int = 30

    def normalized_base_url(self) -> str:
        return self.base_url.rstrip("/")

    def validate(self) -> None:
        if self.output_format not in {"csv", "sql"}:
            raise ValueError("output_format deve ser 'csv' ou 'sql'.")
