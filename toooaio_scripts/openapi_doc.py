from typing import Any
from .openapi_to_pdf import build_pdf
import json


def openapi_to_json(openapi_dict: dict[str, Any], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_dict, f, ensure_ascii=False, indent=2)


def openapi_to_pdf(openapi_dict: dict[str, Any], output_path: str) -> None:
    build_pdf(openapi_dict, output_path)
