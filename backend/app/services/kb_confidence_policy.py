from __future__ import annotations

from .ranking_policy import calculate_kb_confidence as _calculate_kb_confidence
from .ranking_policy import clamp01 as _clamp01

clamp01 = _clamp01
calculate_kb_confidence = _calculate_kb_confidence
