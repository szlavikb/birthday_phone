"""
Mobilválasztó – Flask entry point.
Only contains route handlers; all business logic lives in separate modules:
  config.py   – path constants, REFERENCE_PHONE, DEFAULT_DESCRIPTIONS
  db.py       – SQLite connection, schema init, phone/description CRUD
  parsers.py  – Markdown parsers + DB seed
  state.py    – app_state.json (favorites, winner)
  images.py   – image file operations
"""

from flask import Flask, jsonify, request, render_template

from config import REFERENCE_PHONE
from db import (
    init_db,
    fix_seed_bug,
    db_list_phones,
    db_get_phone,
    db_create_phone,
    db_update_phone,
    db_delete_phone,
    db_phone_exists,
    db_list_descriptions,
    db_update_description,
)
from parsers import seed_db, sync_pro_con_from_yaml, sync_selfie_from_yaml
from state import load_state, save_state, ensure_state_file
from images import list_images, save_image, delete_image
from scoring import compute_camera_winners, CAMERA_FIELDS

app = Flask(__name__, template_folder="templates", static_folder="static")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Phones
# ---------------------------------------------------------------------------

@app.get("/api/phones")
def api_list_phones():
    phones = db_list_phones()
    phones.append(REFERENCE_PHONE)
    return jsonify(phones)


@app.get("/api/phones/<phone_id>")
def api_get_phone(phone_id: str):
    if phone_id == REFERENCE_PHONE["id"]:
        return jsonify(REFERENCE_PHONE)
    phone = db_get_phone(int(phone_id))
    if phone is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(phone)


@app.post("/api/phones")
def api_create_phone():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    if db_phone_exists(name):
        return jsonify({"error": "Már létezik ilyen nevű telefon"}), 409
    phone = db_create_phone(data)
    return jsonify(phone), 201


@app.put("/api/phones/<int:phone_id>")
def api_update_phone(phone_id: int):
    data = request.get_json(force=True)
    phone = db_update_phone(phone_id, data)
    if phone is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(phone)


@app.delete("/api/phones/<int:phone_id>")
def api_delete_phone(phone_id: int):
    if not db_delete_phone(phone_id):
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Column descriptions
# ---------------------------------------------------------------------------

@app.get("/api/descriptions")
def api_get_descriptions():
    return jsonify(db_list_descriptions())


@app.post("/api/descriptions")
def api_post_description():
    data = request.get_json(force=True)
    key  = data.get("column_key")
    desc = data.get("description")
    if not key or desc is None:
        return jsonify({"error": "column_key and description required"}), 400
    db_update_description(key, desc)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# App state (favorites + winner)
# ---------------------------------------------------------------------------

@app.get("/api/state")
def api_get_state():
    return jsonify(load_state())


@app.post("/api/state")
def api_post_state():
    data  = request.get_json(force=True)
    state = load_state()
    if "excluded" in data:
        state["excluded"] = data["excluded"]
    if "winner" in data:
        state["winner"] = data["winner"]
    save_state(state)
    return jsonify(state)


# ---------------------------------------------------------------------------
# Camera column winners (best value among non-excluded phones)
# ---------------------------------------------------------------------------

@app.get("/api/camera-winners")
def api_camera_winners():
    """
    Return the best phone id per camera column.

    Query params:
      ids – optional comma-separated phone ids to restrict comparison
            (e.g. compare view). Without ids, all non-excluded phones count.
    """
    phones = db_list_phones()
    phones.append(REFERENCE_PHONE)

    state = load_state()
    excluded = {str(x) for x in state.get("excluded") or []}

    ids_param = request.args.get("ids", "").strip()
    phone_ids = {s.strip() for s in ids_param.split(",") if s.strip()} or None

    winners = compute_camera_winners(phones, excluded_ids=excluded, phone_ids=phone_ids)
    return jsonify({
        "winners": winners,
        "fields": list(CAMERA_FIELDS),
        "excluded": sorted(excluded),
        "phone_ids": sorted(phone_ids) if phone_ids else None,
    })


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

@app.get("/api/phones/<name>/images")
def api_list_images(name: str):
    return jsonify(list_images(name))


@app.post("/api/phones/<name>/images")
def api_upload_images(name: str):
    saved = [
        save_image(name, file)
        for file in request.files.getlist("images")
        if file.filename
    ]
    return jsonify({"saved": saved})


@app.delete("/api/phones/<name>/images/<filename>")
def api_delete_image(name: str, filename: str):
    if not delete_image(name, filename):
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    init_db()
    seed_db()
    sync_pro_con_from_yaml()
    sync_selfie_from_yaml()
    fix_seed_bug()
    ensure_state_file()
    app.run(debug=True, port=5000)


if __name__ == "__main__":
    main()
