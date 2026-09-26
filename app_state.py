# Estado global y paletas por defecto
# ______________________

import copy
from flet_app.persistence import load_palettes, save_palettes, load_settings, save_settings

# KEYWORD: MAX_PALETTES
MAX_PALETTES = 10

# KEYWORD: PALETTE_KEYS (orden fijo de los 6 colores)
PALETTE_KEYS = [
    "background",   # 1 fondo general
    "surface_1",    # 2 fondo widget común
    "surface_2",    # 3 fondo widget secundario
    "accent",       # 4 fondo widget destacado
    "text_1",       # 5 letras sobre surface_1 / surface_2
    "text_2",       # 6 letras sobre accent
]

# KEYWORD: DEFAULT_PALETTES (4 fijas: 2 claras, 2 oscuras)
DEFAULT_PALETTES = [
    {
        "id": "claro_1",
        "name": "Claro Cálido",
        "dark": False,
        "locked": True,
        "colors": {
            "background": "#FAF7F2",
            "surface_1":  "#FFFFFF",
            "surface_2":  "#F0EBE3",
            "accent":     "#E4572E",
            "text_1":     "#1F1B16",
            "text_2":     "#FFFFFF",
        },
    },
    {
        "id": "claro_2",
        "name": "Claro Frío",
        "dark": False,
        "locked": True,
        "colors": {
            "background": "#F2F5FA",
            "surface_1":  "#FFFFFF",
            "surface_2":  "#E6ECF5",
            "accent":     "#3A6EA5",
            "text_1":     "#16202E",
            "text_2":     "#FFFFFF",
        },
    },
    {
        "id": "oscuro_1",
        "name": "Oscuro Pizarra",
        "dark": True,
        "locked": True,
        "colors": {
            "background": "#14171C",
            "surface_1":  "#1E222A",
            "surface_2":  "#272C36",
            "accent":     "#F2A65A",
            "text_1":     "#E8EAED",
            "text_2":     "#14171C",
        },
    },
    {
        "id": "oscuro_2",
        "name": "Oscuro Bosque",
        "dark": True,
        "locked": True,
        "colors": {
            "background": "#101613",
            "surface_1":  "#18211C",
            "surface_2":  "#223029",
            "accent":     "#7FB069",
            "text_1":     "#E3EAE5",
            "text_2":     "#101613",
        },
    },
]

# Estado: voz y libros (añadir a app_state.py)
# ______________________

# KEYWORD: DEFAULT_VOICES (2 setups base)
DEFAULT_VOICES = [
    {
        "id": "voz_m",
        "name": "Masculino (Jorge)",
        "locked": True,
        "config": {"voice": "es-MX-JorgeNeural", "rate": "-10%",
                   "volume": "+0%", "pitch": "+0Hz"},
    },
    {
        "id": "voz_f",
        "name": "Femenino (Dalia)",
        "locked": True,
        "config": {"voice": "es-MX-DaliaNeural", "rate": "-10%",
                   "volume": "+0%", "pitch": "+0Hz"},
    },
]

# KEYWORD: MAX_VOICES
MAX_VOICES = 10

# KEYWORD: TEXTO_IGNORADO_DEFECTO
TEXTO_IGNORADO_DEFECTO = [
    r"librer[ií]a\s+crisol",
    r"p[aá]g(?:ina)?\.?\s*\d+",
    r"pag\.?\s*\d+",
]


def _new_palette_id(existing_ids):
    i = 1
    while f"custom_{i}" in existing_ids:
        i += 1
    return f"custom_{i}"


class AppState:
    def __init__(self):
        self.palettes = load_palettes()
        if not self.palettes:
            self.palettes = copy.deepcopy(DEFAULT_PALETTES)
            save_palettes(self.palettes)

        settings = load_settings()
        self.active_palette_id = settings.get("active_palette_id", self.palettes[0]["id"])

        if not self._palette_exists(self.active_palette_id):
            self.active_palette_id = self.palettes[0]["id"]

        # voces
        voces = load_settings().get("voices")
        self.voices = voces if voces else copy.deepcopy(DEFAULT_VOICES)
        self.active_voice_id = load_settings().get("active_voice_id", self.voices[0]["id"])

        # libros
        libros = load_settings().get("books", [])
        self.books = libros
        self.active_book_id = None
    # --- consultas ---
    def _palette_exists(self, pid):
        return any(p["id"] == pid for p in self.palettes)

    def get_palette(self, pid=None):
        pid = pid or self.active_palette_id
        for p in self.palettes:
            if p["id"] == pid:
                return p
        return self.palettes[0]

    @property
    def active_palette(self):
        return self.get_palette()

    @property
    def colors(self):
        return self.active_palette["colors"]

    # --- mutaciones ---
    def set_active_palette(self, pid):
        if self._palette_exists(pid):
            self.active_palette_id = pid
            self._persist_settings()

    def add_palette(self):
        if len(self.palettes) >= MAX_PALETTES:
            return None
        pid = _new_palette_id({p["id"] for p in self.palettes})
        base = copy.deepcopy(self.active_palette["colors"])
        nueva = {
            "id": pid,
            "name": f"Personalizada {pid.split('_')[1]}",
            "dark": self.active_palette["dark"],
            "locked": False,
            "colors": base,
        }
        self.palettes.append(nueva)
        save_palettes(self.palettes)
        return nueva

    def update_palette_colors(self, pid, colors):
        p = self.get_palette(pid)
        if p and not p.get("locked"):
            p["colors"] = dict(colors)
            save_palettes(self.palettes)

    def rename_palette(self, pid, name):
        p = self.get_palette(pid)
        if p and not p.get("locked"):
            p["name"] = name
            save_palettes(self.palettes)

    def delete_palette(self, pid):
        p = self.get_palette(pid)
        if not p or p.get("locked"):
            return
        self.palettes = [x for x in self.palettes if x["id"] != pid]
        if self.active_palette_id == pid:
            self.active_palette_id = self.palettes[0]["id"]
        save_palettes(self.palettes)
        self._persist_settings()

    def restore_defaults(self):
        # KEYWORD: restaurar solo las 4 por defecto, no toca custom_*
        customs = [p for p in self.palettes if not p.get("locked")]
        self.palettes = copy.deepcopy(DEFAULT_PALETTES) + customs
        save_palettes(self.palettes)

    def _persist_settings(self):
        self._persist_all()

    # --- voz ---
    def get_voice(self, vid=None):
        vid = vid or self.active_voice_id
        for v in self.voices:
            if v["id"] == vid:
                return v
        return self.voices[0]

    def set_active_voice(self, vid):
        if any(v["id"] == vid for v in self.voices):
            self.active_voice_id = vid
            self._persist_all()

    def add_voice(self):
        if len(self.voices) >= MAX_VOICES:
            return None
        i = 1
        ids = {v["id"] for v in self.voices}
        while f"voz_custom_{i}" in ids:
            i += 1
        nueva = {
            "id": f"voz_custom_{i}",
            "name": f"Voz {i}",
            "locked": False,
            "config": dict(self.get_voice()["config"]),
        }
        self.voices.append(nueva)
        self._persist_all()
        return nueva

    def update_voice(self, vid, name, config):
        v = self.get_voice(vid)
        if v and not v.get("locked"):
            v["name"] = name
            v["config"] = dict(config)
            self._persist_all()

    def delete_voice(self, vid):
        v = self.get_voice(vid)
        if not v or v.get("locked"):
            return
        self.voices = [x for x in self.voices if x["id"] != vid]
        if self.active_voice_id == vid:
            self.active_voice_id = self.voices[0]["id"]
        self._persist_all()

    def restore_default_voices(self):
        customs = [v for v in self.voices if not v.get("locked")]
        self.voices = copy.deepcopy(DEFAULT_VOICES) + customs
        self._persist_all()

    # --- libros ---
    def get_book(self, bid=None):
        bid = bid or self.active_book_id
        for b in self.books:
            if b["id"] == bid:
                return b
        return None

    def add_book(self, path):
        import os
        if not os.path.exists(path):
            return None
        bid = os.path.splitext(os.path.basename(path))[0] + "_" + str(len(self.books))
        libro = {
            "id": bid,
            "path": path,
            "name": os.path.basename(path),
            "voice_id": self.active_voice_id,
            "ignore": list(TEXTO_IGNORADO_DEFECTO),
            "page_start": 1,
            "page_end": 0,  # 0 = hasta el final
            "last_page_read": 1,
        }
        self.books.append(libro)
        self.active_book_id = bid
        self._persist_all()
        return libro

    def update_book(self, bid, **campos):
        b = self.get_book(bid)
        if not b:
            return
        for k, v in campos.items():
            b[k] = v
        self._persist_all()

    def delete_book(self, bid):
        self.books = [b for b in self.books if b["id"] != bid]
        if self.active_book_id == bid:
            self.active_book_id = self.books[0]["id"] if self.books else None
        self._persist_all()

    def _persist_all(self):
        save_settings({
            "active_palette_id": self.active_palette_id,
            "active_voice_id": self.active_voice_id,
            "voices": self.voices,
            "books": self.books,
        })