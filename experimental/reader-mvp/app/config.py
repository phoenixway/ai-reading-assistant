from dataclasses import dataclass
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent.parent

@dataclass(frozen=True)
class Settings:
    db_path: Path = Path(os.getenv("READER_DB", ROOT / "data" / "reader.db"))
    llama_url: str = os.getenv("LLAMA_URL", "http://127.0.0.1:8080")
    target_segment_tokens: int = int(os.getenv("SEGMENT_TOKENS", "2500"))
    max_output_tokens: int = int(os.getenv("MAX_OUTPUT_TOKENS", "700"))
    reasoning_effort: str = os.getenv("REASONING_EFFORT", "low")
    temperature: float = float(os.getenv("LLAMA_TEMPERATURE", "0.2"))

    # Narrative extraction is a structured data task, not creative chat.
    # Keep it deterministic for reproducible ledger generation and benchmarks.
    extraction_temperature: float = float(
        os.getenv("LLAMA_EXTRACTION_TEMPERATURE", "0.0")
    )
    extraction_seed: int = int(
        os.getenv("LLAMA_EXTRACTION_SEED", "424242")
    )

settings = Settings()
