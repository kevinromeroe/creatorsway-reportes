"""Foto aprobada (9-nov-2026) de las cifras de cada campaña, para las pruebas de cuadre.

Las cifras cambian en cada actualización automática (lunes y jueves); las pruebas de cuadre comparan el cálculo
contra esta foto fija. Si se aprueba un corte nuevo como referencia, se copia aquí y se actualizan las cifras
esperadas de las pruebas.
"""
from pathlib import Path

import yaml

FOTO = Path(__file__).resolve().parent / "fixtures" / "aprobado-2026-11-09"


def metricas(cid: str) -> dict:
    return yaml.safe_load((FOTO / cid / "metricas.yaml").read_text(encoding="utf-8")) or {}


def publicas(cid: str) -> dict:
    return yaml.safe_load((FOTO / cid / "publicas.yaml").read_text(encoding="utf-8")) or {}
