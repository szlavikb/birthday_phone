"""
Markdown file parsers and DB seeding logic.
"""
import re
from pathlib import Path

from config import DATA_DIR
from db import db_phone_exists, get_db, fix_seed_bug


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _to_float(s: str) -> float | None:
    try:
        return float(str(s).replace(",", "."))
    except (ValueError, AttributeError):
        return None


def _extract_name_link(cell: str) -> tuple[str, str]:
    """Parse '[Name](url)' or plain text → (name, link)."""
    m = re.search(r"\[([^\]]+)\]\(([^)]+)\)", cell)
    if m:
        return m.group(1), m.group(2)
    return cell.strip(), ""


# ---------------------------------------------------------------------------
# telefon_osszehasonlito.md  →  list of phone dicts
# ---------------------------------------------------------------------------

def parse_table_md(path: Path) -> list[dict]:
    """Read the comparison table MD and return a list of phone dicts."""
    phones: list[dict] = []

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    in_table = False
    for raw_line in lines:
        line = raw_line.strip()

        if line.startswith("| Modell"):
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("|---") or line.startswith("| ---"):
            continue
        if not line.startswith("|"):
            in_table = False
            continue

        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 12:
            continue

        name, link = _extract_name_link(cells[0])
        ois_raw = cells[5]
        ois = "✓" in ois_raw or "yes" in ois_raw.lower()

        phones.append({
            "name":        name,
            "price":       cells[1],
            "battery":     cells[2],
            "sensor_size": cells[3],
            "aperture":    cells[4],
            "ois":         ois,
            "max_zoom":    cells[6],
            "max_video":   cells[7],
            "storage":     cells[8],
            "height":      _to_float(cells[9]),
            "width":       _to_float(cells[10]),
            "thickness":   _to_float(cells[11]) if len(cells) > 11 else None,
            "link":        link,
        })

    return phones


# ---------------------------------------------------------------------------
# kamera_pro_kontra.md  →  {phone_name: {pros, cons, recommended_for}}
# ---------------------------------------------------------------------------

def parse_pro_con_md(path: Path) -> dict[str, dict]:
    """Read the camera pro/con MD and return a keyed dict per phone."""
    result: dict[str, dict] = {}
    current_name: str | None = None
    current_section: str | None = None

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    for raw_line in lines:
        line = raw_line.strip()

        if line.startswith("## "):
            current_name = line[3:].strip()
            result[current_name] = {"pros": [], "cons": [], "recommended_for": ""}
            current_section = None
            continue

        if current_name is None:
            continue

        if "**✅" in line or "Erősségek" in line:
            current_section = "pro"
        elif "**❌" in line or "Gyengeségek" in line:
            current_section = "con"
        elif "**🎯" in line or "Kinek ajánlott" in line:
            current_section = "recommended"
            if ":" in line:
                result[current_name]["recommended_for"] = line.split(":", 1)[1].strip()
        elif current_section == "pro" and line.startswith("- "):
            result[current_name]["pros"].append(line[2:])
        elif current_section == "con" and line.startswith("- "):
            result[current_name]["cons"].append(line[2:])
        elif current_section == "recommended" and line and not line.startswith("**"):
            if not result[current_name]["recommended_for"]:
                result[current_name]["recommended_for"] = line

    return result


# ---------------------------------------------------------------------------
# Pro/con matching: fuzzy-match phone name → pro_con dict key
# ---------------------------------------------------------------------------

def _find_pro_con(phone_name: str, pro_con_data: dict) -> dict:
    """Return the best matching pro_con entry for a phone name."""
    for key, val in pro_con_data.items():
        norm_key  = re.sub(r"\s*⚠.*", "", key).strip()
        norm_name = re.sub(r"\s*\(.*?\)", "", phone_name).strip()
        if norm_key.lower() == norm_name.lower() or phone_name.lower().startswith(norm_key.lower()):
            return val
    return {"pros": [], "cons": [], "recommended_for": ""}


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def seed_db() -> None:
    """Populate the DB from MD files. No-op if any phones already exist."""
    with get_db() as conn:
        if conn.execute("SELECT COUNT(*) FROM phones").fetchone()[0] > 0:
            print("[seed] DB already has phones – skipping.")
            return

    table_path   = DATA_DIR / "telefon_osszehasonlito.md"
    pro_con_path = DATA_DIR / "kamera_pro_kontra.md"

    if not table_path.exists():
        print(f"[seed] {table_path} not found – skipping seed.")
        return

    phones       = parse_table_md(table_path)
    pro_con_data = parse_pro_con_md(pro_con_path) if pro_con_path.exists() else {}

    with get_db() as conn:
        for phone in phones:
            pc = _find_pro_con(phone["name"], pro_con_data)
            cursor = conn.execute(
                """INSERT INTO phones
                   (name, price, battery, sensor_size, aperture, ois, max_zoom,
                    max_video, storage, height, width, thickness, link, recommended_for)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    phone["name"], phone["price"], phone["battery"],
                    phone["sensor_size"], phone["aperture"], int(phone["ois"]),
                    phone["max_zoom"], phone["max_video"], phone["storage"],
                    phone["height"], phone["width"], phone["thickness"],
                    phone["link"], pc["recommended_for"],
                ),
            )
            phone_id = cursor.lastrowid
            for text in pc["pros"]:
                conn.execute(
                    "INSERT INTO pro_con(phone_id,type,text) VALUES (?,?,?)",
                    (phone_id, "pro", text),
                )
            for text in pc["cons"]:
                conn.execute(
                    "INSERT INTO pro_con(phone_id,type,text) VALUES (?,?,?)",
                    (phone_id, "con", text),
                )

    print(f"[seed] Seeded {len(phones)} phones.")
    fix_seed_bug()
