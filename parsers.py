"""
YAML file parsers and DB seeding logic.
"""
import re
from pathlib import Path

import yaml

from config import DATA_DIR
from db import db_phone_exists, get_db, fix_seed_bug


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
            "name":        entry.get("modell", ""),
            "price":       _fmt_price(entry.get("ar_huf")),
            "battery":     battery,
            "sensor_size": cam.get("szenzormeret", "") or "",
            "aperture":    cam.get("rekesz", "")       or "",
            "ois":         bool(cam.get("ois", False)),
            "max_zoom":    cam.get("max_zoom")          or "",
            "max_video":   cam.get("max_video", "")     or "",
            "storage":     storage,
            "height":      _to_float(dims.get("magassag")),
            "width":       _to_float(dims.get("szelesseg")),
            "thickness":   _to_float(dims.get("vastagsag")),
            "link":        _extract_link(entry.get("link", "")),
            "_raw":        entry,          # kept for auto pro/con generation
            "_selfie":     selfie,
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
# Auto-generated pro/con from raw YAML data
# ---------------------------------------------------------------------------

def _auto_pro_con(raw: dict, selfie: dict) -> dict:
    """Generate basic pro/con items from spec data when no manual entry exists."""
    cam = raw.get("kamera", {}) or {}
    pros: list[str] = []
    cons: list[str] = []

    sensor   = cam.get("szenzormeret", "") or ""
    aperture = cam.get("rekesz", "")       or ""
    ois      = bool(cam.get("ois", False))
    max_zoom = cam.get("max_zoom")          or ""
    max_video= cam.get("max_video", "")     or ""
    kiemelt  = cam.get("kiemelt_tulajdonsag")
    battery_mah  = raw.get("akkumulator_mah") or 0
    selfie_mp    = selfie.get("megapixel")    or 0

    # Sensor size
    m = re.search(r"1/(\d+\.?\d*)", sensor)
    if m:
        d = float(m.group(1))
        if d <= 1.4:
            pros.append(f"Kiemelkedően nagy szenzor ({sensor}) – legjobb sötétteljesítmény")
        elif d <= 1.6:
            pros.append(f"Nagy szenzor ({sensor}) – jó sötétteljesítmény")
        elif d > 1.9:
            cons.append(f"Kisebb szenzorméret ({sensor})")

    # Aperture
    m = re.search(r"f/(\d+\.?\d*)", aperture, re.I)
    if m:
        fn = float(m.group(1))
        if fn <= 1.6:
            pros.append(f"Tág rekesz ({aperture}) – kiváló fénygyűjtés sötétben")
        elif fn <= 1.8:
            pros.append(f"Jó rekesz ({aperture}) – megfelelő fénygyűjtés")

    # OIS
    if ois:
        pros.append("OIS optikai képstabilizátor – stabil fotók és videók")
    else:
        cons.append("Nincs OIS – videónál és sötétben érzékelhető kézremegés")

    # Zoom
    if max_zoom:
        pros.append(f"Optikai zoom: {max_zoom} – valódi közelítés")
    else:
        cons.append("Nincs dedikált teleobiektív – csak digitális zoom")

    # Video
    v = max_video.upper()
    if "8K" in v:
        pros.append(f"8K videófelvétel ({max_video})")
    elif "4K" in v and "60" in v:
        pros.append("4K@60fps videófelvétel – gördülékeny felvételek")
    elif "4K" in v:
        cons.append("Videó max. 4K@30fps – nincs 60fps mód")

    # Battery
    if battery_mah >= 6000:
        pros.append(f"Nagy akkumulátor ({battery_mah} mAh) – hosszú üzemidő")

    # Selfie camera
    if selfie_mp >= 32:
        pros.append(f"Kiemelkedő szelfikamera ({selfie_mp} MP)")
    elif selfie_mp and selfie_mp < 16:
        cons.append(f"Kisebb szelfikamera ({selfie_mp} MP)")

    # Highlighted feature(s) from raw data
    if kiemelt:
        if isinstance(kiemelt, list):
            for k in kiemelt:
                if k not in " ".join(pros):
                    pros.append(str(k).capitalize())
        else:
            kstr = str(kiemelt).capitalize()
            if kstr not in " ".join(pros):
                pros.append(kstr)

    return {"pros": pros, "cons": cons, "recommended_for": ""}


# ---------------------------------------------------------------------------
# Pro/con matching: fuzzy-match phone name → pro_con dict key
# ---------------------------------------------------------------------------

def _find_pro_con(phone_name: str, pro_con_data: dict) -> dict | None:
    """Return the best matching pro_con entry, or None if no match."""
    # Normalize: strip trailing color/variant info in parentheses
    norm_name = re.sub(r"\s*\(.*?\)", "", phone_name).strip().lower()
    norm_name_short = re.sub(r"^(xiaomi|motorola|google|samsung|oppo|nothing|poco)\s+", "", norm_name).strip()

    for key, val in pro_con_data.items():
        norm_key = re.sub(r"\s*\(.*?\)", "", key).strip().lower()
        norm_key_short = re.sub(r"^(xiaomi|motorola|google|samsung|oppo|nothing|poco)\s+", "", norm_key).strip()
        if norm_key == norm_name or norm_key_short == norm_name_short:
            return val
        if norm_name.startswith(norm_key) or norm_key.startswith(norm_name):
            return val
    return None


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
            raw    = phone.pop("_raw", {})
            selfie = phone.pop("_selfie", {})

            pc = _find_pro_con(phone["name"], pro_con_data)
            if pc is None:
                pc = _auto_pro_con(raw, selfie)

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

