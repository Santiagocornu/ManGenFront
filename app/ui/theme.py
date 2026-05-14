import flet as ft


COLORS = {
    "bg_app": "#0d1321",
    "bg_panel": "#151d2f",
    "bg_deep": "#1d2a42",
    "glass": "#1f2d49aa",
    "accent": "#2dd4bf",
    "accent_soft": "#2dd4bf22",
    "primary": "#f97316",
    "primary_dark": "#ea580c",
    "success": "#22c55e",
    "danger": "#ef4444",
    "warning": "#f59e0b",
    "border": "#31415f",
    "row_hover": "#22314d",
    "text_main": "#f8fafc",
    "text_soft": "#b8c4db",
    "text_muted": "#7f8ca8",
}


def input_style(as_dropdown: bool = False):
    shared = {
        "filled": True,
        "bgcolor": COLORS["bg_app"],
        "border_color": COLORS["border"],
        "focused_border_color": COLORS["accent"],
        "color": COLORS["text_main"],
        "label_style": ft.TextStyle(color=COLORS["text_soft"], size=12),
        "hint_style": ft.TextStyle(color=COLORS["text_muted"], size=12),
        "text_size": 13,
        "border_radius": 14,
        "dense": True,
    }
    if as_dropdown:
        shared["filled"] = False
        shared.pop("hint_style", None)
        shared["text_style"] = ft.TextStyle(color=COLORS["text_main"], size=13)
        shared["content_padding"] = ft.padding.symmetric(horizontal=12, vertical=12)
        shared["menu_height"] = 280
        shared["height"] = 50
    return shared


def button_style(kind: str):
    palette = {
        "primary": (COLORS["primary"], COLORS["text_main"]),
        "accent": (COLORS["accent"], COLORS["bg_app"]),
        "success": (COLORS["success"], COLORS["text_main"]),
        "danger": (COLORS["danger"], COLORS["text_main"]),
    }
    bgcolor, color = palette[kind]
    return ft.ButtonStyle(
        bgcolor=bgcolor,
        color=color,
        shape=ft.RoundedRectangleBorder(radius=12),
        padding=ft.padding.symmetric(horizontal=18, vertical=14),
        text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_600),
    )


def panel(content, padding: int = 20, expand: bool = False):
    return ft.Container(
        expand=expand,
        padding=padding,
        border_radius=20,
        bgcolor=COLORS["bg_panel"],
        border=ft.border.all(1, COLORS["border"]),
        content=content,
    )
