# UI de libros
# ______________________

import flet as ft


def build_book_list(state, on_select, on_delete):
    c = state.colors
    items = []
    for b in state.books:
        activo = b["id"] == state.active_book_id
        items.append(
            ft.Container(
                on_click=lambda e, bid=b["id"]: on_select(bid),
                padding=10, border_radius=8,
                bgcolor=c["surface_1"] if activo else None,
                border=ft.border.all(2, c["accent"]) if activo else None,
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.icons.MENU_BOOK, color=c["text_1"]),
                        ft.Column(
                            spacing=2, expand=True,
                            controls=[
                                ft.Text(b["name"], color=c["text_1"], weight="bold",
                                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(f"Última: pág. {b.get('last_page_read', 1)}",
                                        color=c["text_1"], size=11, opacity=0.7),
                            ],
                        ),
                        ft.IconButton(icon=ft.icons.DELETE_OUTLINE,
                                      icon_color=c["text_1"],
                                      on_click=lambda e, bid=b["id"]: on_delete(bid)),
                    ],
                ),
            )
        )
    if not items:
        items.append(ft.Text("Sin libros. Añade uno abajo.", color=c["text_1"],
                             size=12, opacity=0.7))
    return ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, controls=items)


def build_book_config(state, book, on_save_field, on_play):
    c = state.colors
    if not book:
        return ft.Column(
            controls=[ft.Text("Selecciona un libro", color=c["text_1"])],
        )

    # KEYWORD: voice_dropdown (voz asociada al libro)
    dd_voice = ft.Dropdown(
        label="Setup de voz",
        value=book["voice_id"],
        width=320,
        options=[ft.dropdown.Option(v["id"], v["name"]) for v in state.voices],
        on_change=lambda e: on_save_field(book["id"], "voice_id", e.control.value),
    )

    tf_start = ft.TextField(
        label="Página inicio", value=str(book["page_start"]), width=130,
        on_blur=lambda e: on_save_field(book["id"], "page_start",
                                        int(e.control.value or 1)),
    )
    tf_end = ft.TextField(
        label="Página fin (0 = final)", value=str(book["page_end"]), width=170,
        on_blur=lambda e: on_save_field(book["id"], "page_end",
                                        int(e.control.value or 0)),
    )

    # KEYWORD: ignore_list
    ignore_chips = ft.Row(
        wrap=True, spacing=6,
        controls=[
            ft.Chip(
                label=ft.Text(patron, size=11),
                bgcolor=c["surface_2"],
                on_delete=lambda e, p=patron: on_save_field(
                    book["id"], "ignore",
                    [x for x in book["ignore"] if x != p]
                ),
            )
            for patron in book["ignore"]
        ],
    )

    tf_new_ignore = ft.TextField(label="Añadir patrón (regex)", width=280,
                                 hint_text="ej: pág\\.?\\s*\\d+")

    def add_ignore(e):
        val = tf_new_ignore.value.strip()
        if not val:
            return
        nueva = list(book["ignore"]) + [val]
        on_save_field(book["id"], "ignore", nueva)
        tf_new_ignore.value = ""

    btn_add_ignore = ft.IconButton(icon=ft.icons.ADD, on_click=add_ignore)

    return ft.Container(
        padding=14, border_radius=10, bgcolor=c["surface_1"],
        content=ft.Column(
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text(book["name"], color=c["text_1"], weight="bold", size=18),
                ft.Text(book["path"], color=c["text_1"], size=11, opacity=0.6),
                ft.Divider(),
                ft.Text("Voz", color=c["text_1"], weight="bold"),
                dd_voice,
                ft.Text("Páginas", color=c["text_1"], weight="bold"),
                ft.Row(spacing=10, controls=[tf_start, tf_end]),
                ft.Text("Textos a ignorar", color=c["text_1"], weight="bold"),
                ignore_chips,
                ft.Row(spacing=6, controls=[tf_new_ignore, btn_add_ignore]),
                ft.Divider(),
                ft.ElevatedButton(
                    "▶  Leer libro", width=200,
                    bgcolor=c["accent"], color=c["text_2"],
                    on_click=lambda e: on_play(book["id"]),
                ),
            ],
        ),
    )