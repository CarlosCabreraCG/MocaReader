# App principal - Etapa 2
# ______________________

import flet as ft
from app_state import AppState, MAX_PALETTES, MAX_VOICES
from flet_app.palette_ui import build_palette_list, build_palette_editor
from flet_app.voice_ui import build_voice_list, build_voice_editor
from books_ui import build_book_list, build_book_config
from flet_app.reader_ui import build_reader_view


def main(page: ft.Page):
    page.title = "Audiolibro"
    page.window_width = 1100
    page.window_height = 750
    page.padding = 0

    state = AppState()

    # KEYWORD: file_picker (elegir PDF)
    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    root = ft.Container(expand=True)
    page.add(root)

    # KEYWORD: edit_palette / edit_voice (estados de editores abiertos)
    ui = {
        "edit_palette": None,
        "edit_voice": None,
        "reading_book": None,
        "tab_index": 0,
    }

    def aplicar_tema():
        c = state.colors
        page.bgcolor = c["background"]
        render()

    # ---------- PERSONALIZACIÓN ----------
    def tab_personalizacion():
        c = state.colors

        # --- paletas ---
        lista_pal = build_palette_list(
            state,
            on_change=cambiar_paleta,
            on_edit=abrir_editor_paleta,
        )
        acciones_pal = ft.Row(
            spacing=8,
            controls=[
                ft.ElevatedButton(
                    "Nueva", icon=ft.icons.ADD,
                    disabled=len(state.palettes) >= MAX_PALETTES,
                    on_click=lambda e: nueva_paleta(),
                    bgcolor=c["surface_2"], color=c["text_1"],
                ),
                ft.OutlinedButton("Restaurar", icon=ft.icons.RESTORE,
                                  on_click=lambda e: restaurar_paletas()),
            ],
        )
        panel_paletas = ft.Container(
            padding=12, border_radius=10, bgcolor=c["surface_1"],
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("Paletas", size=18, weight="bold", color=c["text_1"]),
                    lista_pal, ft.Divider(), acciones_pal,
                ],
            ),
        )

        # --- voces ---
        lista_voz = build_voice_list(
            state,
            on_change=cambiar_voz,
            on_edit=abrir_editor_voz,
            on_delete=borrar_voz,
        )
        acciones_voz = ft.Row(
            spacing=8,
            controls=[
                ft.ElevatedButton(
                    "Nueva", icon=ft.icons.ADD,
                    disabled=len(state.voices) >= MAX_VOICES,
                    on_click=lambda e: nueva_voz(),
                    bgcolor=c["surface_2"], color=c["text_1"],
                ),
                ft.OutlinedButton("Restaurar", icon=ft.icons.RESTORE,
                                  on_click=lambda e: restaurar_voces()),
            ],
        )
        panel_voces = ft.Container(
            padding=12, border_radius=10, bgcolor=c["surface_1"],
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("Setups de voz", size=18, weight="bold", color=c["text_1"]),
                    lista_voz, ft.Divider(), acciones_voz,
                ],
            ),
        )

        # --- editor derecho ---
        if ui["edit_palette"]:
            p = state.get_palette(ui["edit_palette"])
            editor = build_palette_editor(p, on_save=guardar_editor_paleta,
                                          on_cancel=cerrar_editores)
        elif ui["edit_voice"]:
            v = state.get_voice(ui["edit_voice"])
            editor = build_voice_editor(v, on_save=guardar_editor_voz,
                                        on_cancel=cerrar_editores,
                                        colors=c)
        else:
            editor = ft.Container(
                padding=16,
                content=ft.Text("Selecciona un elemento para editar",
                                color=c["text_1"], opacity=0.7),
            )

        return ft.Row(
            expand=True, spacing=0,
            controls=[
                ft.Container(width=380, padding=16, bgcolor=c["background"],
                             content=ft.Column(
                                 scroll=ft.ScrollMode.AUTO, spacing=16,
                                 controls=[panel_paletas, panel_voces])),
                ft.Container(expand=True, padding=16, bgcolor=c["background"],
                             content=editor),
            ],
        )

    # ---------- LIBROS ----------
    def tab_libros():
        c = state.colors

        lista = build_book_list(state, on_select=seleccionar_libro,
                                on_delete=borrar_libro)
        panel_lista = ft.Container(
            width=340, padding=14, bgcolor=c["surface_1"], border_radius=10,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("Mis libros", size=18, weight="bold", color=c["text_1"]),
                    ft.Container(expand=True, content=lista),
                    ft.ElevatedButton(
                        "Añadir PDF", icon=ft.icons.UPLOAD_FILE,
                        bgcolor=c["surface_2"], color=c["text_1"],
                        on_click=lambda e: elegir_pdf(),
                    ),
                ],
            ),
        )

        libro = state.get_book()
        panel_cfg = build_book_config(state, libro,
                                      on_save_field=guardar_campo_libro,
                                      on_play=iniciar_lectura)

        return ft.Row(
            expand=True, spacing=16,
            controls=[
                ft.Container(padding=16, bgcolor=c["background"],
                             content=ft.Row(controls=[panel_lista])),
                ft.Container(expand=True, padding=16, bgcolor=c["background"],
                             content=ft.Container(
                                 expand=True, content=panel_cfg)),
            ],
        )

    # ---------- RENDER ----------
    def render():
        c = state.colors
        tabs = ft.Tabs(
            selected_index=ui["tab_index"],
            on_change=lambda e: cambiar_tab(int(e.control.selected_index)),
            expand=True,
            tabs=[
                ft.Tab(text="Personalización",
                       content=ft.Container(expand=True,
                                            content=tab_personalizacion())),
                ft.Tab(text="Libros",
                       content=ft.Container(expand=True, content=tab_libros())),
            ],
        )
        root.content = ft.Container(expand=True, bgcolor=c["background"],
                                    content=tabs)
        page.update()

        tabs_list = [
            ft.Tab(text="Personalización",
                   content=ft.Container(expand=True, content=tab_personalizacion())),
            ft.Tab(text="Libros",
                   content=ft.Container(expand=True, content=tab_libros())),
        ]
        if ui["reading_book"]:
            tabs_list.append(
                ft.Tab(
                    text="Lectura",
                    content=ft.Container(
                        expand=True,
                        content=build_reader_view(
                            state,
                            state.get_book(ui["reading_book"]),
                            on_exit=lambda: salir_lectura(),
                        ),
                    ),
                ),
            )

        # KEYWORD: tab_index_safe (evita que Flet caiga a la pestaña 0)
        n_tabs = len(tabs_list)
        idx = ui["tab_index"]
        if idx is None or idx < 0 or idx >= n_tabs:
            idx = 0
        ui["tab_index"] = idx

        tabs = ft.Tabs(
            selected_index=0,          # arranca en 0 y movemos después
            on_change=lambda e: cambiar_tab(int(e.control.selected_index)),
            expand=True,
            tabs=tabs_list,
        )
        root.content = ft.Container(expand=True, bgcolor=c["background"],
                                    content=tabs)
        page.update()

        # KEYWORD: fix_selected_tab (mueve a la pestaña deseada tras el update)
        if idx != 0:
            tabs.selected_index = idx
            page.update()
    def cambiar_tab(i):
        ui["tab_index"] = i
        page.update()

    # ---------- ACCIONES PALETA ----------
    def cambiar_paleta(pid):
        state.set_active_palette(pid)
        ui["edit_palette"] = None
        aplicar_tema()

    def abrir_editor_paleta(pid):
        p = state.get_palette(pid)
        if p.get("locked"):
            page.snack_bar = ft.SnackBar(
                ft.Text("Las paletas por defecto no se editan; crea una nueva."))
            page.snack_bar.open = True
            page.update()
            return
        ui["edit_palette"] = pid
        ui["edit_voice"] = None
        render()

    def borrar_paleta(pid):
        p = state.get_palette(pid)
        if not p or p.get("locked"):
            return
        state.delete_palette(pid)
        render()

    def guardar_editor_paleta(colors):
        state.update_palette_colors(ui["edit_palette"], colors)
        ui["edit_palette"] = None
        aplicar_tema()

    def nueva_paleta():
        p = state.add_palette()
        if not p:
            return
        state.set_active_palette(p["id"])
        ui["edit_palette"] = p["id"]
        aplicar_tema()

    def restaurar_paletas():
        state.restore_defaults()
        ui["edit_palette"] = None
        aplicar_tema()

    # ---------- ACCIONES VOZ ----------
    def cambiar_voz(vid):
        state.set_active_voice(vid)
        ui["edit_voice"] = None
        render()

    def abrir_editor_voz(vid):
        v = state.get_voice(vid)
        if v.get("locked"):
            page.snack_bar = ft.SnackBar(
                ft.Text("Las voces por defecto no se editan; crea una nueva."))
            page.snack_bar.open = True
            page.update()
            return
        ui["edit_voice"] = vid
        ui["edit_palette"] = None
        render()

    def guardar_editor_voz(name, config):
        state.update_voice(ui["edit_voice"], name, config)
        ui["edit_voice"] = None
        render()

    def nueva_voz():
        v = state.add_voice()
        if not v:
            return
        state.set_active_voice(v["id"])
        ui["edit_voice"] = v["id"]
        render()

    def restaurar_voces():
        state.restore_default_voices()
        ui["edit_voice"] = None
        render()

    def borrar_voz(vid):
        state.delete_voice(vid)
        render()

    def cerrar_editores():
        ui["edit_palette"] = None
        ui["edit_voice"] = None
        render()

    # ---------- ACCIONES LIBRO ----------
    def elegir_pdf():
        file_picker.on_result = lambda e: _pdf_elegido(e)
        file_picker.pick_files(
            allow_multiple=False, allowed_extensions=["pdf"],
        )

    def _pdf_elegido(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        path = e.files[0].path
        state.add_book(path)
        render()

    def seleccionar_libro(bid):
        state.active_book_id = bid
        state._persist_all()
        render()

    def borrar_libro(bid):
        state.delete_book(bid)
        render()

    def guardar_campo_libro(bid, campo, valor):
        state.update_book(bid, **{campo: valor})
        render()

    def iniciar_lectura(bid):
        ui["reading_book"] = bid
        # KEYWORD: lectura_tab_index (Personalización=0, Libros=1, Lectura=2)
        ui["tab_index"] = 2
        render()

    def salir_lectura():
        ui["reading_book"] = None
        ui["tab_index"] = 1
        render()

    aplicar_tema()


if __name__ == "__main__":
    ft.app(target=main) 