# UI de lectura
# ______________________

import threading
import time
import flet as ft
from flet_app.pdf_stream import bloques_desde_pdf
from flet_app.tts_engine import TTSEngine


class ReaderController:
    """Estado compartido entre la UI y el hilo de lectura."""

    def __init__(self, state, libro):
        self.state = state
        self.libro = libro
        self.control = {"stop": False, "paused": False, "skip_to": None}
        self.bloques_vistos = []      # textos ya vistos
        self.hilo = None
        self.engine = None
        self.pagina_actual = libro.get("last_page_read", 1)

    # KEYWORD: start
    def start(self, on_block, on_page, on_finish):
        voz = self.state.get_voice(self.libro["voice_id"])
        self.engine = TTSEngine()

        patrones = self.libro.get("ignore") or []
        gen = bloques_desde_pdf(
            self.libro["path"],
            self.libro.get("page_start", 1),
            self.libro.get("page_end", 0),
            patrones,
        )

        # Envolvemos el generador para ir guardando textos por índice
        def gen_con_texto():
            for tipo, payload in gen:
                if tipo == "block":
                    self.bloques_vistos.append(payload)
                yield tipo, payload

        def run():
            self.engine.reproducir_bloques(
                gen_con_texto(), voz["config"],
                on_block=on_block, on_page=on_page, control=self.control,
            )
            on_finish()

        self.hilo = threading.Thread(target=run, daemon=True)
        self.hilo.start()

    def pausar(self):
        self.control["paused"] = True

    def reanudar(self):
        self.control["paused"] = False

    def detener(self):
        self.control["stop"] = True
        if self.hilo and self.hilo.is_alive():
            self.hilo.join(timeout=2)
        if self.engine:
            self.engine.cerrar()


def build_reader_view(state, libro, on_exit):
    c = state.colors

    txt_parrafo = ft.Text("", color=c["text_1"], size=16)
    txt_pagina = ft.Text(f"Página {libro.get('last_page_read', 1)}",
                         color=c["text_1"], size=13, opacity=0.8)

    def set_parrafo(idx, _texto_ignorado=None):
        ctrl = ref["ctrl"]
        if 0 <= idx < len(ctrl.bloques_vistos):
            txt_parrafo.value = ctrl.bloques_vistos[idx]
        else:
            txt_parrafo.value = "…"
        try:
            txt_parrafo.update()
        except Exception:
            pass

    def on_block(idx, _):
        set_parrafo(idx)

    def on_page(num):
        ref["ctrl"].pagina_actual = num
        txt_pagina.value = f"Página {num}"
        try:
            txt_pagina.update()
        except Exception:
            pass

    def on_finish():
        # guardar última página leída
        state.update_book(libro["id"], last_page_read=ref["ctrl"].pagina_actual)

    # KEYWORD: play/pause
    def play(e):
        if ref.get("ctrl"):
            ref["ctrl"].reanudar()
            return
        ctrl = ReaderController(state, libro)
        ref["ctrl"] = ctrl
        ctrl.start(on_block, on_page, on_finish)
        estado["pausado"] = False

    def pause(e):
        ctrl = ref.get("ctrl")
        if ctrl:
            if estado["pausado"]:
                ctrl.reanudar()
                estado["pausado"] = False
            else:
                ctrl.pausar()
                estado["pausado"] = True

    # KEYWORD: avanzar/retroceder bloque
    def avanzar_bloque(e):
        ctrl = ref.get("ctrl")
        if not ctrl:
            return
        siguiente = len(ctrl.bloques_vistos)
        ctrl.control["skip_to"] = siguiente

    def retroceder_bloque(e):
        ctrl = ref.get("ctrl")
        if not ctrl:
            return
        actual = max(0, len(ctrl.bloques_vistos) - 2)
        ctrl.control["skip_to"] = actual

    def salir(e):
        ctrl = ref.get("ctrl")
        if ctrl:
            ctrl.detener()
        on_exit()

    ref = {"ctrl": None}
    estado = {"pausado": False}

    controles = ft.Row(
        wrap=True, spacing=10, alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.IconButton(icon=ft.icons.SKIP_PREVIOUS,
                          tooltip="Retroceder bloque",
                          icon_color=c["text_1"], on_click=retroceder_bloque),
            ft.IconButton(icon=ft.icons.PLAY_ARROW, tooltip="Play",
                          icon_color=c["accent"], on_click=play),
            ft.IconButton(icon=ft.icons.PAUSE, tooltip="Pausa/Reanudar",
                          icon_color=c["text_1"], on_click=pause),
            ft.IconButton(icon=ft.icons.SKIP_NEXT, tooltip="Avanzar bloque",
                          icon_color=c["text_1"], on_click=avanzar_bloque),
            ft.IconButton(icon=ft.icons.ARROW_BACK, tooltip="Página anterior",
                          icon_color=c["text_1"],
                          on_click=lambda e: _saltar_pagina(-1)),
            ft.IconButton(icon=ft.icons.ARROW_FORWARD, tooltip="Página siguiente",
                          icon_color=c["text_1"],
                          on_click=lambda e: _saltar_pagina(1)),
            ft.IconButton(icon=ft.icons.EXIT_TO_APP, tooltip="Regresar",
                          icon_color=c["text_1"], on_click=salir),
        ],
    )

    def _saltar_pagina(delta):
        # KEYWORD: skip_page (por ahora solo avanza/retrocede el contador;
        # el salto real dentro del stream se hace reanudando desde el
        # bloque correspondiente en una próxima iteración)
        ctrl = ref.get("ctrl")
        if not ctrl:
            return
        objetivo = max(1, ctrl.pagina_actual + delta)
        state.update_book(libro["id"], page_start=objetivo, last_page_read=objetivo)
        ctrl.control["stop"] = True
        # reiniciamos el stream desde esa página
        if ctrl.hilo and ctrl.hilo.is_alive():
            ctrl.hilo.join(timeout=2)

        nuevo = ReaderController(state, libro)
        ref["ctrl"] = nuevo
        nuevo.start(on_block, on_page, on_finish)

    return ft.Container(
        expand=True, padding=20, bgcolor=c["background"],
        content=ft.Column(
            spacing=20,
            controls=[
                ft.Container(
                    padding=20, border_radius=12, bgcolor=c["surface_1"],
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            txt_pagina,
                            ft.Divider(),
                            ft.Container(
                                content=txt_parrafo,
                                padding=10, border_radius=8,
                                bgcolor=c["surface_2"],
                            ),
                        ],
                    ),
                ),
                controles,
            ],
        ),
    )