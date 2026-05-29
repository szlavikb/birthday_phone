"""
Best-value scoring for phone spec columns.

Rules mirror static/js/app.js (_computeBestMap and _score* helpers).
Higher score = better. Ties: all top-scoring phones are winners.
"""
import re
from typing import Any, Callable

# Camera-related columns (main + selfie)
CAMERA_FIELDS: tuple[str, ...] = (
    "sensor_size",
    "aperture",
    "ois",
    "max_zoom",
    "max_video",
    "selfie_megapixel",
    "selfie_aperture",
    "selfie_max_video",
)


def _extract_num(s: Any, pattern: str) -> float | None:
    m = re.search(pattern, str(s or ""), re.IGNORECASE)
    return float(m.group(1)) if m else None


def score_battery(v: Any) -> float:
    n = _extract_num(v, r"(\d+)\s*mAh")
    return n if n is not None else 0.0


def score_sensor(v: Any) -> float:
    n = _extract_num(v, r"1/(\d+\.?\d*)")
    return -n if n is not None else -999.0


def score_aperture(v: Any) -> float:
    n = _extract_num(v, r"f/(\d+\.?\d*)")
    return -n if n is not None else -999.0


def score_ois(v: Any) -> float:
    return 1.0 if v in (True, 1, "1") else 0.0


def score_zoom(v: Any) -> float:
    s = str(v or "").lower()
    if not s or "nincs" in s or s == "–":
        return 0.0
    m = re.search(r"(\d+)×", s)
    return float(m.group(1)) if m else 1.0


def score_video(v: Any) -> float:
    s = str(v or "").lower()
    if "8k" in s and "120" in s:
        return 10.0
    if "8k" in s:
        return 9.0
    if "4k" in s and "120" in s:
        return 8.0
    if "4k" in s and "60" in s:
        return 7.0
    if "4k" in s:
        return 6.0
    if "1080" in s and "60" in s:
        return 4.0
    if "1080" in s:
        return 3.0
    return 0.0


def score_selfie_megapixel(v: Any) -> float:
    if v is None or v == "":
        return -999.0
    try:
        return float(int(v))
    except (ValueError, TypeError):
        return -999.0


SCORERS: dict[str, Callable[[Any], float]] = {
    "battery":            score_battery,
    "sensor_size":        score_sensor,
    "aperture":           score_aperture,
    "max_zoom":           score_zoom,
    "max_video":          score_video,
    "selfie_megapixel":   score_selfie_megapixel,
    "selfie_aperture":    score_aperture,
    "selfie_max_video":   score_video,
    "storage":            lambda v: float(m.group(1)) if (m := re.search(r"(\d+)\s*GB\s*RAM", str(v or ""), re.I)) else 0.0,
    "thickness":          lambda v: -float(v) if v is not None else -999.0,
}


def compute_best_map(
    phones: list[dict],
    excluded_ids: set[str] | None = None,
    fields: tuple[str, ...] | list[str] | None = None,
    phone_ids: set[str] | None = None,
) -> dict[str, list[str]]:
    """
    Return {field: [winning_phone_id, ...]} for the given fields.

    Only non-excluded phones participate. Optionally restrict to phone_ids subset.
    All phones sharing the top score are included (ties = multiple winners).
    """
    excluded = excluded_ids or set()
    active = [p for p in phones if str(p.get("id")) not in excluded]
    if phone_ids is not None:
        active = [p for p in active if str(p.get("id")) in phone_ids]

    target_fields = fields if fields is not None else tuple(SCORERS.keys())
    best: dict[str, list[str]] = {}

    for field in target_fields:
        scorer = SCORERS.get(field)
        if scorer is None:
            continue

        top_score = float("-inf")
        winners: list[str] = []

        for phone in active:
            score = scorer(phone.get(field))
            pid = str(phone.get("id"))
            if score > top_score:
                top_score = score
                winners = [pid]
            elif score == top_score and top_score > float("-inf"):
                winners.append(pid)

        best[field] = winners

    return best


def compute_camera_winners(
    phones: list[dict],
    excluded_ids: set[str] | None = None,
    phone_ids: set[str] | None = None,
) -> dict[str, list[str]]:
    """Best phone per camera column among non-excluded phones."""
    return compute_best_map(
        phones,
        excluded_ids=excluded_ids,
        fields=CAMERA_FIELDS,
        phone_ids=phone_ids,
    )
