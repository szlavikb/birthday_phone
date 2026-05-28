# Mobilválasztó

A Flask-based phone comparison web app for comparing smartphone specs side-by-side. Built to help choose a birthday phone gift.

## Features

- Compare multiple smartphones across key specs: price, battery, camera sensor size, aperture, OIS, max zoom, max video, storage, and dimensions
- Mark phones as favorites and set a winner
- Upload and browse product images per phone
- Editable column descriptions (Hungarian UI)
- Hardcoded reference phone (Redmi Note 10 Pro) for baseline comparison
- Data seeded from Markdown files; persisted in SQLite

## Project Structure

```
main.py        – Flask routes
config.py      – Path constants, reference phone, default descriptions
db.py          – SQLite schema, CRUD operations
parsers.py     – Markdown parsers + DB seeding
state.py       – Favorites/winner persistence (app_state.json)
images.py      – Image file operations
data/          – SQLite database and app state JSON
static/        – CSS, JS, phone images
templates/     – Jinja2 HTML templates
```

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)

## Setup

```bash
uv sync
```

## Running

```bash
uv run python main.py
```

The app starts at [http://localhost:5000](http://localhost:5000).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/phones` | List all phones |
| `GET` | `/api/phones/<id>` | Get a phone |
| `POST` | `/api/phones` | Create a phone |
| `PUT` | `/api/phones/<id>` | Update a phone |
| `DELETE` | `/api/phones/<id>` | Delete a phone |
| `GET` | `/api/phones/<name>/images` | List images for a phone |
| `POST` | `/api/phones/<name>/images` | Upload images |
| `DELETE` | `/api/phones/<name>/images/<filename>` | Delete an image |
| `GET` | `/api/descriptions` | Get column descriptions |
| `POST` | `/api/descriptions` | Update a column description |
| `GET` | `/api/state` | Get favorites/winner state |
| `POST` | `/api/state` | Update favorites/winner state |

