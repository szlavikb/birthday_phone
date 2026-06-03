"""
YAML file parsers and DB seeding logic.
"""
import re
from pathlib import Path

import yaml

from config import DATA_DIR
from db import get_db, fix_seed_bug


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _to_float(s) -> float | None:
    try:
        return float(str(s).replace(",", "."))
    except (ValueError, AttributeError, TypeError):
        return None


def _extract_link(raw: str) -> str:
    """Parse '[text](url)' or plain URL → url."""
    if not raw:
        return ""
    m = re.search(r"\(([^)]+)\)", str(raw))
    return m.group(1) if m else str(raw).strip()


def _fmt_price(ar_huf) -> str:
    """Format integer price as Hungarian '129 900 Ft'."""
    if ar_huf is None:
        return ""
    return f"{int(ar_huf):,} Ft".replace(",", "\u00a0")


# ---------------------------------------------------------------------------
# osszehasonlito.yaml  →  list of phone dicts
# ---------------------------------------------------------------------------

def parse_yaml_phones(path: Path) -> list[dict]:
    """Read osszehasonlito.yaml and return a list of phone dicts."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    phones: list[dict] = []
    for entry in data or []:
        cam   = entry.get("kamera",    {}) or {}
        mem   = entry.get("memoria",   {}) or {}
        dims  = entry.get("meretek_mm",{}) or {}
        selfie = entry.get("szelfi_kamera", {}) or {}

        ram = mem.get("ram_gb")
        rom = mem.get("rom_gb")
        storage = (
            f"{rom}GB / {ram}GB RAM" if rom and ram
            else f"{rom}GB" if rom
            else ""
        )

        battery_mah = entry.get("akkumulator_mah")
        battery = f"{battery_mah} mAh" if battery_mah else ""

        phones.append({
            "name":             entry.get("modell", ""),
            "price":            _fmt_price(entry.get("ar_huf")),
            "battery":          battery,
            "sensor_size":      cam.get("szenzormeret", "") or "",
            "aperture":         cam.get("rekesz", "")       or "",
            "ois":              bool(cam.get("ois", False)),
            "max_zoom":         cam.get("max_zoom")          or "",
            "max_video":        cam.get("max_video", "")     or "",
            "selfie_megapixel": selfie.get("megapixel"),
            "selfie_aperture":  selfie.get("rekesz", "")     or "",
            "selfie_max_video": selfie.get("max_video", "")  or "",
            "storage":          storage,
            "height":           _to_float(dims.get("magassag")),
            "width":            _to_float(dims.get("szelesseg")),
            "thickness":        _to_float(dims.get("vastagsag")),
            "link":             _extract_link(entry.get("link", "")),
            "_raw":             entry,
        })

    return phones


# ---------------------------------------------------------------------------
# pro_kontra.yaml  →  {phone_name: {pros, cons, recommended_for}}
# ---------------------------------------------------------------------------

def parse_yaml_pro_con(path: Path) -> dict[str, dict]:
    """Read pro_kontra.yaml and return a keyed dict per phone."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    result: dict[str, dict] = {}
    for entry in data or []:
        name  = entry.get("modell", "")
        pros  = entry.get("pro",    []) or []
        cons  = entry.get("kontra", []) or []
        rec   = entry.get("kinek_ajanlott", "") or ""
        if isinstance(pros, str): pros = [pros]
        if isinstance(cons, str): cons = [cons]
        result[name] = {
            "pros": list(pros),
            "cons": list(cons),
            "recommended_for": rec,
        }
    return result


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def seed_db() -> None:
    """Populate the DB from YAML files. No-op if any phones already exist."""
    with get_db() as conn:
        if conn.execute("SELECT COUNT(*) FROM phones").fetchone()[0] > 0:
            print("[seed] DB already has phones – skipping.")
            return

    phones_path  = DATA_DIR / "osszehasonlito.yaml"
    pro_con_path = DATA_DIR / "pro_kontra.yaml"

    if not phones_path.exists():
        print(f"[seed] {phones_path} not found – skipping seed.")
        return

    phones       = parse_yaml_phones(phones_path)
    pro_con_data = parse_yaml_pro_con(pro_con_path) if pro_con_path.exists() else {}

    with get_db() as conn:
        for phone in phones:
            phone.pop("_raw", None)

            pc = pro_con_data.get(phone["name"])
            if pc is None:
                print(f"[seed] No pro_kontra entry for {phone['name']!r}")
                pc = {"pros": [], "cons": [], "recommended_for": ""}

            cursor = conn.execute(
                """INSERT INTO phones
                   (name, price, battery, sensor_size, aperture, ois, max_zoom,
                    max_video, selfie_megapixel, selfie_aperture, selfie_max_video,
                    storage, height, width, thickness, link, recommended_for)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    phone["name"], phone["price"], phone["battery"],
                    phone["sensor_size"], phone["aperture"], int(phone["ois"]),
                    phone["max_zoom"], phone["max_video"],
                    phone.get("selfie_megapixel"), phone.get("selfie_aperture", ""),
                    phone.get("selfie_max_video", ""),
                    phone["storage"],
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


def sync_pro_con_from_yaml() -> None:
    """Update pro/con and recommended_for from pro_kontra.yaml (idempotent)."""
    phones_path = DATA_DIR / "osszehasonlito.yaml"
    pro_con_path = DATA_DIR / "pro_kontra.yaml"
    if not phones_path.exists() or not pro_con_path.exists():
        return

    phones = parse_yaml_phones(phones_path)
    pro_con_data = parse_yaml_pro_con(pro_con_path)
    updated = 0

    with get_db() as conn:
        for phone in phones:
            pc = pro_con_data.get(phone["name"])
            if pc is None:
                print(f"[sync] No pro_kontra entry for {phone['name']!r}")
                continue
            row = conn.execute(
                "SELECT id FROM phones WHERE name=?", (phone["name"],)
            ).fetchone()
            if row is None:
                continue
            phone_id = row[0]
            conn.execute(
                "UPDATE phones SET recommended_for=? WHERE id=?",
                (pc["recommended_for"], phone_id),
            )
            conn.execute("DELETE FROM pro_con WHERE phone_id=?", (phone_id,))
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
            updated += 1

    print(f"[sync] Pro/con synced for {updated} phones.")


def sync_selfie_from_yaml() -> None:
    """Update selfie columns from osszehasonlito.yaml (idempotent)."""
    phones_path = DATA_DIR / "osszehasonlito.yaml"
    if not phones_path.exists():
        return

    phones = parse_yaml_phones(phones_path)
    with get_db() as conn:
        for phone in phones:
            conn.execute(
                """UPDATE phones
                   SET selfie_megapixel=?, selfie_aperture=?, selfie_max_video=?
                   WHERE name=?""",
                (
                    phone.get("selfie_megapixel"),
                    phone.get("selfie_aperture", ""),
                    phone.get("selfie_max_video", ""),
                    phone["name"],
                ),
            )
    print(f"[sync] Selfie fields synced for {len(phones)} phones.")


def sync_phones_from_yaml() -> None:
    """Upsert core phone fields from osszehasonlito.yaml (idempotent)."""
    phones_path = DATA_DIR / "osszehasonlito.yaml"
    if not phones_path.exists():
        return

    phones = parse_yaml_phones(phones_path)
    inserted = 0
    updated = 0

    with get_db() as conn:
        for phone in phones:
            row = conn.execute(
                "SELECT id FROM phones WHERE name=?",
                (phone["name"],),
            ).fetchone()

            if row is None:
                conn.execute(
                    """INSERT INTO phones
                       (name, price, battery, sensor_size, aperture, ois, max_zoom,
                        max_video, selfie_megapixel, selfie_aperture, selfie_max_video,
                        storage, height, width, thickness, link, recommended_for)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        phone["name"], phone["price"], phone["battery"],
                        phone["sensor_size"], phone["aperture"], int(phone["ois"]),
                        phone["max_zoom"], phone["max_video"],
                        phone.get("selfie_megapixel"), phone.get("selfie_aperture", ""),
                        phone.get("selfie_max_video", ""),
                        phone["storage"],
                        phone["height"], phone["width"], phone["thickness"],
                        phone["link"], "",
                    ),
                )
                inserted += 1
            else:
                conn.execute(
                    """UPDATE phones
                       SET price=?, battery=?, sensor_size=?, aperture=?, ois=?,
                           max_zoom=?, max_video=?, selfie_megapixel=?, selfie_aperture=?,
                           selfie_max_video=?, storage=?, height=?, width=?, thickness=?,
                           link=?
                       WHERE name=?""",
                    (
                        phone["price"], phone["battery"], phone["sensor_size"],
                        phone["aperture"], int(phone["ois"]), phone["max_zoom"],
                        phone["max_video"], phone.get("selfie_megapixel"),
                        phone.get("selfie_aperture", ""), phone.get("selfie_max_video", ""),
                        phone["storage"], phone["height"], phone["width"],
                        phone["thickness"], phone["link"], phone["name"],
                    ),
                )
                updated += 1

    print(f"[sync] Phones synced: {updated} updated, {inserted} inserted.")

