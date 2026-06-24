from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.config import settings


@dataclass
class ExtractionResult:
    status: str  # "success" | "failed"
    text: str | None = None
    error: str | None = None
    method: str = "pandas"


def _truncate(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    if len(df) > settings.max_table_rows:
        return df.head(settings.max_table_rows), True
    return df, False


def extract_csv(path: Path) -> ExtractionResult:
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return ExtractionResult(status="failed", error=f"Could not parse CSV: {exc}")

    df, truncated = _truncate(df)
    text = df.to_markdown(index=False)
    if truncated:
        text += f"\n\n[truncated to first {settings.max_table_rows} rows]"
    return ExtractionResult(status="success", text=text, method="pandas")


def extract_xlsx(path: Path) -> ExtractionResult:
    try:
        sheets = pd.read_excel(path, sheet_name=None)
    except Exception as exc:
        return ExtractionResult(status="failed", error=f"Could not parse XLSX: {exc}")

    parts = []
    for sheet_name, df in sheets.items():
        df, truncated = _truncate(df)
        part = f"## Sheet: {sheet_name}\n\n{df.to_markdown(index=False)}"
        if truncated:
            part += f"\n\n[truncated to first {settings.max_table_rows} rows]"
        parts.append(part)

    return ExtractionResult(status="success", text="\n\n".join(parts), method="openpyxl")
