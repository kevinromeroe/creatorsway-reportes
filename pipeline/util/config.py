"""Carga de la configuración del cliente y de las campañas.

Cada campaña vive en config/campanas/<id>/ con dos archivos:
  campana.yaml   identidad, piezas y textos (se edita a mano)
  metricas.yaml  cifras importadas del Excel (scripts/importar_excel.py)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
CAMPAIGNS_DIR = CONFIG_DIR / "campanas"


def load_client() -> dict[str, Any]:
    return _load(CONFIG_DIR / "cliente.yaml")


def load_campaign(campaign_id: str) -> dict[str, Any]:
    return _load(CAMPAIGNS_DIR / campaign_id / "campana.yaml")


def load_metrics(campaign_id: str) -> dict[str, Any]:
    return _load(CAMPAIGNS_DIR / campaign_id / "metricas.yaml")


def campaign_ids() -> list[str]:
    return sorted(p.name for p in CAMPAIGNS_DIR.iterdir() if (p / "campana.yaml").exists())


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe la configuración: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
