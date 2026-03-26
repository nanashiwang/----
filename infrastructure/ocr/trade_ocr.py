from __future__ import annotations

import importlib
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from domain.schemas import TradeOCRResult


def _load_ocr_runtime():
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            pytesseract = importlib.import_module("pytesseract")
            image_module = importlib.import_module("PIL.Image")
        return pytesseract, image_module
    except Exception:  # pragma: no cover - optional runtime dependency
        return None, None


class TradeOCRService:
    def parse(self, image_path: str) -> TradeOCRResult:
        path = Path(image_path)
        if not path.exists():
            return TradeOCRResult(image_uri=image_path, warnings=['image file does not exist'])

        pytesseract, image_module = _load_ocr_runtime()
        if pytesseract is None or image_module is None:
            return TradeOCRResult(
                image_uri=str(path),
                raw_text='',
                confidence=0.0,
                warnings=['pytesseract is unavailable; returning placeholder OCR result'],
            )

        raw_text = pytesseract.image_to_string(image_module.open(path), lang='chi_sim+eng')
        return TradeOCRResult(
            image_uri=str(path),
            raw_text=raw_text,
            confidence=0.55,
            normalized_fields={'raw_length': len(raw_text)},
        )
