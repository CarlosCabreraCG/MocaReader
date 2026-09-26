# UI de paletas
# ______________________

import flet as ft
from app_state import AppState


def hex_to_field(value: str):
    return value.lstrip("#").upper()


def build_palette_list(state: AppState, on_change, on_edit):
    # KEYWORD: palette_list
    items = []
    for p in state.palettes:
        activa = p["id"] == state.active_palette_id
        c = p["colors"]

        swatches = ft.Row(
            spacing=4,
            controls=[
                ft.Container(width=14, height=14, bgcolor=c[k], border_radius=3,
                             border=ft.border.all(1, "#00000022"))
                for k in ("background", "surface_1", "surface_2", "accent")
            ],
        )

        tile = ft.Container(
            on_click=lambda e, pid=p["id"]: on_change(pid),
            padding=10,
            border_radius=8,
            bgcolor=c["surface_1"] if activa else None,
            border=ft.border.all(2, c["accent"]) if activa else None,
            content=ft.Row(
                controls=[
                    ft.Column(
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Text(p["name"], color=c["text_1"], weight="bold"),
                            ft.Text("por defecto" if p.get("locked") else "personalizada",
                                    color=c["text_1"], size=11, opacity=0.7),
                        ],
                    ),
                    swatches,
                    ft.IconButton(
                        icon=ft.icons.EDIT,
                        icon_color=c["text_1"],
                        tooltip="Editar",
                        on_click=lambda e, pid=p["id"]: on_edit(pid),
                    ),
                ],
            ),
        )
        items.append(tile)
    return ft.Column(spacing=6, controls=items)


def build_palette_editor(palette, on_save, on_cancel):
    # KEYWORD: palette_editor
    campos = {}
    c = palette["colors"]

    def color_field(key):
        tf = ft.TextField(
            label=key,
            value=hex_to_field(c[key]),
            prefix_text="#",
            width=180,
            text_style=ft.TextStyle(font_family="monospace"),
        )
        campos[key] = tf
        return tf

    def on_pick(key, e: ft.FilePickerResultEvent=None):
        # placeholder: usaremos input hex por simplicidad
        pass

    def guardar(e):
        nuevos = {}
        for k, tf in campos.items():
            v = tf.value.strip().lstrip("#")
            if len(v) != 6:
                tf.error_text = "hex 6 dígitos"
                tf.update()
                return
            nuevos[k] = "#" + v.upper()
        on_save(nuevos)

    return ft.Container(
        padding=12,
        border_radius=10,
        bgcolor=c["surface_2"],
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Text(f"Editar: {palette['name']}", color=c["text_1"],
                        weight="bold", size=16),
                ft.Row(wrap=True, spacing=12, controls=[color_field(k) for k in c]),
                ft.Row(
                    spacing=10,
                    controls=[
                        ft.ElevatedButton("Guardar", on_click=guardar,
                                          bgcolor=c["accent"], color=c["text_2"]),
                        ft.OutlinedButton("Cancelar", on_click=lambda e: on_cancel()),
                    ],
                ),
            ],
        ),
    )