"""
Shared constants and configuration.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
DB_PATH    = DATA_DIR / "phones.db"
STATE_PATH = DATA_DIR / "app_state.json"

CLOUDINARY_FOLDER = os.getenv("CLOUDINARY_FOLDER", "birthday_phone")

# ---------------------------------------------------------------------------
# Hardcoded reference phone (NOT stored in the database)
# ---------------------------------------------------------------------------
REFERENCE_PHONE: dict = {
    "id": "ref-redmi-note-10-pro",
    "name": "Redmi Note 10 Pro",
    "price": "",
    "battery": "5020 mAh",
    "sensor_size": '1/1.52" közepes',
    "aperture": "f/1.9",
    "ois": False,
    "max_zoom": "nincs optikai zoom",
    "max_video": "4K@30fps",
    "selfie_megapixel": 16,
    "selfie_aperture": "f/2.45",
    "selfie_max_video": "1080p@30fps",
    "storage": "128GB / 6GB RAM",
    "height": 160.46,
    "width": 74.5,
    "thickness": 8.29,
    "link": "",
    "recommended_for": "",
    "is_reference": True,
    "pro_con": [],
}

# ---------------------------------------------------------------------------
# Default Hungarian column descriptions (seeded once into DB)
# ---------------------------------------------------------------------------
DEFAULT_DESCRIPTIONS: list[tuple[str, str, str]] = [
    ("model",       "Modell",       "A telefon gyártója és modellje."),
    ("price",       "Ár",           "Ajánlott kiskereskedelmi ár forintban (Ft). Az árak tájékoztató jellegűek és változhatnak."),
    ("battery",     "Akkumulátor",  "Az akkumulátor kapacitása mAh-ban. Nagyobb érték általában hosszabb üzemidőt jelent, bár a szoftver-optimalizáció is számít."),
    ("sensor_size", "Szenzorméret", "A főkamera képérzékelőjének mérete (pl. 1/1.4\"). Nagyobb szenzor = több fény = jobb képminőség, főleg sötétben."),
    ("aperture",    "Rekesz",       "A főkamera rekesznyílása (f-szám). Kisebb f-szám (pl. f/1.5) = nagyobb rekesz = több fény = jobb teljesítmény sötétben."),
    ("ois",         "OIS",          "Optikai képstabilizátor (Optical Image Stabilization). Csökkenti a kézremegés okozta elmosódást fotónál és videónál egyaránt."),
    ("max_zoom",    "Max. zoom",    "A maximálisan elérhető optikai zoom szorzója dedikált teleobiektívvel. Digitális zoom nem számít – csak az optikai valódi."),
    ("max_video",   "Max. videó",   "A legmagasabb felbontás és képsebesség kombináció, amelyet a kamera videóban támogat (pl. 4K@60fps)."),
    ("selfie_megapixel", "Szelfi MP", "Az előlapi (selfie) kamera felbontása megapixelben. Magasabb érték = részletgazdagabb képek, de a szenzorméret és szoftver is számít."),
    ("selfie_aperture",  "Szelfi rekesz", "Az előlapi kamera rekesznyílása (f-szám). Kisebb f-szám = több fény = jobb selfie sötétben."),
    ("selfie_max_video", "Szelfi videó", "A legmagasabb videófelbontás és képsebesség, amelyet az előlapi kamera támogat."),
    ("storage",     "ROM / RAM",    "Beépített tárhely (ROM) és operatív memória (RAM). Több RAM = gördülékenyebb multitasking; több ROM = több helyi tárhely."),
    ("height",      "Magasság",     "A telefon magassága mm-ben. Nagyobb képernyőhöz általában nagyobb magasság társul."),
    ("width",       "Szélesség",    "A telefon szélessége mm-ben. Szélesebb telefon kisebb kézbe nehezebben fér."),
    ("thickness",   "Vastagság",    "A telefon vastagsága mm-ben. Vékonyabb eszköz általában elegánsabb, de kisebb akkumulátorral jár."),
    ("link",        "Link",         "Hivatkozás a telefon termékoldalára (webshop vagy gyártói oldal)."),
]
