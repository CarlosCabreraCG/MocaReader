# UI de setups de voz
# ______________________

import flet as ft

# KEYWORD: voces_edge (lista de voces comunes)
VOCES_EDGE = [
    "es-MX-JorgeNeural",
    "es-MX-DaliaNeural",
    "es-ES-AlvaroNeural",
    "es-ES-ElviraNeural",
    "es-AR-TomasNeural",
    "es-CO-SalomeNeural",
    "es-PE-CamilaNeural",
    "es-US-AlonsoNeural",
]


def build_voice_list(state, on_change, on_edit, on_delete):
    items = []
    for v in state.voices:
        activa = v["id"] == state.active_voice_id
        c = state.colors
        items.append(
            ft.Container(
                on_click=lambda e, vid=v["id"]: on_change(vid),
                padding=10,
                border_radius=8,
                bgcolor=c["surface_1"] if activa else None,
                border=ft.border.all(2, c["accent"]) if activa else None,
                content=ft.Row(
                    controls=[
                        ft.Column(
                            spacing=2, expand=True,
                            controls=[
                                ft.Text(v["name"], color=c["text_1"], weight="bold"),
                                ft.Text(v["config"]["voice"], color=c["text_1"],
                                        size=11, opacity=0.7),
                            ],
                        ),
                        ft.IconButton(icon=ft.icons.EDIT, icon_color=c["text_1"],
                                      on_click=lambda e, vid=v["id"]: on_edit(vid)),
                        ft.IconButton(
                            icon=ft.icons.DELETE_OUTLINE,
                            icon_color=c["text_1"],
                            disabled=v.get("locked", False),
                            on_click=lambda e, vid=v["id"]: on_delete(vid),
                        ),
                    ],
                ),
            )
        )
    return ft.Column(spacing=6, controls=items)


def build_voice_editor(voice, on_save, on_cancel, colors):
    c = colors
    cfg = voice["config"]

    tf_name = ft.TextField(label="Nombre", value=voice["name"], width=280)

    dd_voice = ft.Dropdown(
        label="Voz",
        value=cfg["voice"],
        width=320,
        options=[ft.dropdown.Option(v) for v in VOCES_EDGE],
    )
    tf_rate = ft.TextField(label="Rate (ej: -10%)", value=cfg["rate"], width=140)
    tf_vol = ft.TextField(label="Volume (ej: +0%)", value=cfg["volume"], width=140)
    tf_pitch = ft.TextField(label="Pitch (ej: +0Hz)", value=cfg["pitch"], width=140)

    def guardar(e):
        on_save(tf_name.value.strip() or voice["name"], {
            "voice": dd_voice.value,
            "rate": tf_rate.value.strip(),
            "volume": tf_vol.value.strip(),
            "pitch": tf_pitch.value.strip(),
        })

    return ft.Container(
        padding=12, border_radius=10, bgcolor=c["surface_2"],
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Text(f"Editar voz: {voice['name']}", color=c["text_1"],
                        weight="bold", size=16),
                tf_name, dd_voice,
                ft.Row(spacing=10, controls=[tf_rate, tf_vol, tf_pitch]),
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