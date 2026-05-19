import asyncio
import csv
import flet as ft
from datetime import date, datetime, time
import os
import subprocess
import tempfile
from urllib.parse import quote

from app.services.api_client import ApiError, PaymentRequiredError
from app.ui.theme import COLORS, button_style, input_style, panel


class DashboardScreen:
    def __init__(self, page: ft.Page, api, user: dict, entities: list[dict], on_logout):
        self.page = page
        self.api = api
        self.user = user
        self.entities = entities
        self.on_logout = on_logout
        self.current_key = None
        self.current_config = None
        self.rows_cache = []
        self.relation_items_cache = {}
        self.filter_inputs = {}
        self.stats_section = ft.Container()
        self.filters_section = ft.Container()
        self.rows_section = ft.Container(expand=True)
        self.content_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=18)
        self.feedback = ft.Text("", color=COLORS["text_soft"], size=12)

    def build(self, route: str):
        parts = [part for part in route.split("/") if part]
        requested_key = parts[0] if parts else self.entities[0]["key"]
        self.current_config = self._config_for(requested_key) or self.entities[0]
        self.current_key = self.current_config["key"]
        self.content_column.controls = [
            self.stats_section,
            self.filters_section,
            self.rows_section,
        ]
        self._refresh_table()

        shell = ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[COLORS["bg_app"], COLORS["bg_deep"], COLORS["bg_panel"]],
            ),
            content=ft.ResponsiveRow(
                [
                    ft.Container(self._sidebar(), col={"sm": 12, "md": 4, "lg": 3, "xl": 3}),
                    ft.Container(
                        padding=20,
                        col={"sm": 12, "md": 8, "lg": 9, "xl": 9},
                        content=ft.Column(
                            [
                                self._header(),
                                self.feedback,
                                self.content_column,
                            ],
                            expand=True,
                            spacing=16,
                        ),
                    ),
                ],
                columns=12,
                spacing=0,
                run_spacing=0,
                expand=True,
            ),
        )

        return ft.View(
            route=route,
            padding=0,
            bgcolor=COLORS["bg_app"],
            controls=[shell],
        )

    def _sidebar(self):
        items = []
        for entity in self.entities:
            active = entity["key"] == self.current_key
            items.append(
                ft.Container(
                    border_radius=16,
                    bgcolor=COLORS["accent_soft"] if active else COLORS["glass"],
                    border=ft.border.all(1, COLORS["border"]),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                    ink=True,
                    on_click=lambda e, key=entity["key"]: self.page.go(f"/{key}"),
                    content=ft.Row(
                        [
                            ft.Icon(
                                self._icon_for(entity),
                                color=COLORS["text_main"] if active else COLORS["text_soft"],
                                size=18,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        entity["title"],
                                        color=COLORS["text_main"] if active else COLORS["text_soft"],
                                        size=14,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                    ft.Text(
                                        entity.get("tagline", ""),
                                        color=COLORS["text_muted"],
                                        size=10,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                )
            )

        alert_button = self._build_stock_alert_button()
        return ft.Container(
            expand=True,
            bgcolor=COLORS["bg_panel"],
            border=ft.border.only(right=ft.BorderSide(1, COLORS["border"])),
            padding=24,
            content=ft.Column(
                [
                    ft.Text("Mangen", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text_main"]),
                    ft.Text("Operacion multi-sucursal para GenMan", size=12, color=COLORS["text_soft"]),
                    ft.Container(
                        margin=ft.margin.only(top=12, bottom=12),
                        content=panel(
                            ft.Column(
                                [
                                    ft.Text("Sesion activa", color=COLORS["text_muted"], size=11),
                                    ft.Text(self.user.get("nombre", "-"), color=COLORS["text_main"], size=18, weight=ft.FontWeight.W_600),
                                    ft.Text(self.user.get("email", "-"), color=COLORS["text_soft"], size=12),
                                    ft.Text(
                                        f"Rol: {self.user.get('roll', '-')}",
                                        color=COLORS["accent"],
                                        size=12,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                    *([
                                        ft.Row(
                                            [
                                                ft.Container(expand=True),
                                                alert_button,
                                            ],
                                            alignment=ft.MainAxisAlignment.END,
                                        )
                                    ] if alert_button else []),
                                ],
                                spacing=4,
                            ),
                            padding=18,
                        ),
                    ),
                    ft.Text("Modulos", color=COLORS["text_soft"], size=12),
                    ft.Column(items, spacing=10, expand=True, scroll=ft.ScrollMode.AUTO),
                    ft.OutlinedButton(
                        "Cerrar sesion",
                        icon=ft.Icons.LOGOUT,
                        on_click=self.on_logout,
                        style=ft.ButtonStyle(
                            color=COLORS["text_soft"],
                            side=ft.BorderSide(1, COLORS["border"]),
                            shape=ft.RoundedRectangleBorder(radius=14),
                        ),
                        height=46,
                    ),
                ],
                expand=True,
                spacing=8,
            ),
        )

    def _header(self):
        config = self.current_config
        actions = [
            ft.ElevatedButton(
                f"Nuevo {config.get('singular_title', config['title'])}",
                icon=ft.Icons.ADD,
                on_click=lambda e: self._open_form(),
                style=button_style("primary"),
                height=44,
            ),
        ]

        if self.current_key != "sucursales":
            actions.append(
                ft.ElevatedButton(
                    "Exportar Excel",
                    icon=ft.Icons.FILE_DOWNLOAD,
                    on_click=lambda e: self._export_filtered_rows(),
                    style=button_style("accent"),
                    height=44,
                )
            )

        actions.append(
            ft.OutlinedButton(
                "Recargar",
                icon=ft.Icons.REFRESH,
                on_click=lambda e: self._refresh_table(),
                style=ft.ButtonStyle(
                    color=COLORS["text_soft"],
                    side=ft.BorderSide(1, COLORS["border"]),
                    shape=ft.RoundedRectangleBorder(radius=14),
                ),
                height=44,
            ),
        )

        for action in config.get("extra_actions", []):
            if action == "from_pedido":
                actions.append(
                    ft.ElevatedButton(
                        "Venta desde pedido",
                        icon=ft.Icons.POINT_OF_SALE,
                        on_click=lambda e: self._open_pedido_to_venta(),
                        style=button_style("accent"),
                        height=44,
                    )
                )

        if self.current_key == "sucursales":
            actions.insert(
                1,
                ft.ElevatedButton(
                    "Exportar sucursal",
                    icon=ft.Icons.STOREFRONT,
                    on_click=lambda e: self._export_branch_workbook(),
                    style=button_style("success"),
                    height=44,
                ),
            )

        return panel(
            ft.ResponsiveRow(
                [
                    ft.Container(
                        col={"sm": 12, "lg": 6},
                        content=ft.Column(
                            [
                                ft.Text(config["title"], size=30, weight=ft.FontWeight.BOLD, color=COLORS["text_main"]),
                                ft.Text(config.get("tagline", ""), size=13, color=COLORS["text_soft"]),
                                # API URL intentionally hidden from UI for end users
                            ],
                            spacing=4,
                        ),
                    ),
                    ft.Container(
                        col={"sm": 12, "lg": 6},
                        content=ft.Row(
                            actions,
                            wrap=True,
                            alignment=ft.MainAxisAlignment.END,
                            spacing=10,
                            run_spacing=10,
                        ),
                    ),
                ],
                columns=12,
            ),
            padding=24,
        )

    def _stock_threshold_for_unit(self, unit: str):
        normalized = str(unit or "").strip().lower()
        if normalized in {"kg", "kilogramo", "kilogramos", "kilogramos"}:
            return 5.0
        if normalized == "unidad":
            return 10.0
        return None

    def _low_stock_items(self, rows: list[dict], item_type: str):
        items = []
        for row in rows:
            threshold = self._stock_threshold_for_unit(row.get("unidad"))
            if threshold is None:
                continue
            quantity = self._coerce_float(row.get("cantidad"), 0.0)
            if quantity <= threshold:
                items.append(
                    {
                        "label": str(row.get("nombre") or row.get("descripcion") or "Sin nombre"),
                        "quantity": quantity,
                        "unit": str(row.get("unidad") or "").strip(),
                        "threshold": threshold,
                        "type": item_type,
                    }
                )
        return items

    def _fetch_low_stock_alerts(self):
        alerts = {"products": [], "materias_primas": [], "error": None}
        try:
            products = self.api.get("/apiManGen/Producto") or []
            alerts["products"] = self._low_stock_items(products, "producto")
            materias = self.api.get("/apiManGen/Materia_prima") or []
            alerts["materias_primas"] = self._low_stock_items(materias, "materia_prima")
        except ApiError as exc:
            alerts["error"] = str(exc)
        return alerts

    def _build_stock_alert_button(self):
        alerts = self._fetch_low_stock_alerts()
        alert_count = len(alerts["products"]) + len(alerts["materias_primas"])
        icon_color = COLORS["warning"] if alert_count else COLORS["text_soft"]
        tooltip = (
            f"{alert_count} alerta(s) de stock" if alert_count else "No hay alertas de stock"
        )
        return ft.IconButton(
            icon=ft.Icons.NOTIFICATIONS,
            icon_color=icon_color,
            tooltip=tooltip,
            on_click=lambda e: self._show_stock_alerts_dialog(self._fetch_low_stock_alerts()),
            width=46,
            height=46,
        )

    def _show_stock_alerts_dialog(self, alerts: dict):
        search_input = ft.TextField(
            label="Buscar por nombre",
            width=520,
            on_change=lambda e: render_alert_items(),
            **input_style(),
        )
        results_column = ft.Column(spacing=8)

        def render_alert_items():
            search_value = str(search_input.value or "").strip().lower()
            content_items = []

            if alerts.get("error"):
                content_items.append(
                    ft.Text(
                        f"No se pudieron cargar las alertas: {alerts['error']}",
                        color=COLORS["danger"],
                        size=12,
                    )
                )

            def append_alerts(title: str, items: list[dict]):
                filtered_items = [
                    item for item in items
                    if not search_value or search_value in item["label"].lower()
                ]
                if not filtered_items:
                    return
                content_items.append(
                    ft.Text(
                        title,
                        color=COLORS["text_main"],
                        size=14,
                        weight=ft.FontWeight.W_600,
                    )
                )
                for item in filtered_items:
                    content_items.append(
                        ft.Row(
                            [
                                ft.Text(item["label"], color=COLORS["text_main"], size=12, expand=True),
                                ft.Text(
                                    f"{self._format_quantity_display(item['quantity'])} {item['unit']} (umbral {self._format_value(item['threshold'])})",
                                    color=COLORS["warning"],
                                    size=12,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        )
                    )

            append_alerts("Productos con stock bajo", alerts.get("products", []))
            append_alerts("Materias primas con stock bajo", alerts.get("materias_primas", []))

            if not content_items:
                content_items.append(
                    ft.Text(
                        "No hay alertas de stock que coincidan con la búsqueda.",
                        color=COLORS["success"],
                        size=12,
                    )
                )

            results_column.controls = content_items
            self.page.update()

        render_alert_items()

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["bg_panel"],
            title=ft.Text("Alertas de stock", color=COLORS["text_main"]),
            content=ft.Container(
                width=620,
                content=ft.Column(
                    [search_input, results_column],
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                    height=460,
                ),
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self._close_dialog(dlg)),
            ],
        )
        self.page.show_dialog(dlg)

    def _refresh_table(self):
        try:
            rows = self.api.get(self.current_config["endpoint"]) or []
        except ApiError as exc:
            if isinstance(exc, PaymentRequiredError):
                self._show_payment_required_alert()
            self.feedback.value = str(exc)
            self.feedback.color = COLORS["danger"]
            self.stats_section.content = None
            self.filters_section.content = None
            self.rows_section.content = self._empty_state("No se pudo cargar la entidad.")
            self.page.update()
            return

        if not isinstance(rows, list):
            rows = [rows]

        self.rows_cache = rows
        self.relation_items_cache = {}
        self._ensure_filter_inputs()
        self._render_rows()

    def _render_rows(self):
        rows = self._apply_filters(self.rows_cache)
        self.feedback.value = f"{len(rows)} registro(s) visibles"
        self.feedback.color = COLORS["text_soft"]

        self.stats_section.content = self._build_stats_strip(rows)
        if self.filters_section.content is None:
            self.filters_section.content = self._build_filter_panel()
        self.rows_section.content = self._build_rows_panel(rows)
        self.page.update()

    def _build_stats_strip(self, rows: list[dict]):
        total_rows = len(self.rows_cache)
        filtered_rows = len(rows)
        cards = [
            self._stat_card("Registros totales", str(total_rows), COLORS["primary"]),
            self._stat_card("Mostrados", str(filtered_rows), COLORS["accent"]),
        ]

        if self.current_key in {"ventas", "pedidos"}:
            total_sum = sum(self._coerce_float(row.get("total")) for row in rows)
            total_desc_sum = sum(self._coerce_float(row.get("totalDesc")) for row in rows)
            cards.extend(
                [
                    self._stat_card("Total filtrado", self._format_value(total_sum), COLORS["success"]),
                    self._stat_card("Total desc. filtrado", self._format_value(total_desc_sum), COLORS["warning"]),
                ]
            )
        return ft.ResponsiveRow(cards, columns=12, run_spacing=12)

    def _stat_card(self, label: str, value: str, accent: str):
        return ft.Container(
            col={"sm": 12, "md": 6, "lg": 3},
            padding=16,
            border_radius=18,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[COLORS["bg_panel"], COLORS["bg_deep"]],
            ),
            border=ft.border.all(1, COLORS["border"]),
            content=ft.Column(
                [
                    ft.Text(label, color=COLORS["text_soft"], size=11),
                    ft.Text(value, color=COLORS["text_main"], size=17, weight=ft.FontWeight.W_700),
                    ft.Container(height=4, bgcolor=accent, border_radius=99),
                ],
                spacing=8,
            ),
        )

    def _ensure_filter_inputs(self):
        filter_configs = list(self.current_config.get("filters", []))
        has_nombre_field = any(field["key"] == "nombre" for field in self.current_config.get("fields", []))
        has_nombre_filter = any(filter_config["key"] == "nombre" for filter_config in filter_configs)
        if has_nombre_field and not has_nombre_filter:
            filter_configs.insert(0, {"key": "search_nombre", "label": "Buscar por nombre", "type": "text"})

        expected_keys = [filter_config["key"] for filter_config in filter_configs]
        if list(self.filter_inputs.keys()) == expected_keys:
            return

        inputs = {}
        for filter_config in filter_configs:
            filter_type = filter_config["type"]
            if filter_type == "select":
                control = ft.Dropdown(
                    label=filter_config["label"],
                    options=[ft.dropdown.Option(option) for option in filter_config["options"]],
                    **input_style(as_dropdown=True),
                )
                control.on_change = lambda e: self._render_rows()
            else:
                control = ft.TextField(
                    label=filter_config["label"],
                    keyboard_type=ft.KeyboardType.NUMBER if filter_type == "number" else ft.KeyboardType.TEXT,
                    on_change=lambda e: self._render_rows(),
                    **input_style(),
                )
            inputs[filter_config["key"]] = {"config": filter_config, "control": control}
        self.filter_inputs = inputs
        self.filters_section.content = self._build_filter_panel()

    def _build_filter_panel(self):
        if not self.filter_inputs:
            return panel(
                ft.Text("Este modulo no tiene filtros configurados.", color=COLORS["text_soft"], size=12),
                padding=18,
            )

        controls = []
        for key, entry in self.filter_inputs.items():
            control = entry["control"]
            if self.current_key == "ventas" and key == "fecha":
                today_button = ft.ElevatedButton(
                    "Hoy",
                    icon=ft.Icons.CALENDAR_TODAY,
                    on_click=lambda e, k=key: self._set_today_filter(k),
                    style=button_style("accent"),
                    height=44,
                )
                controls.append(
                    ft.Container(
                        ft.Row(
                            [
                                ft.Container(control, expand=True),
                                today_button,
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        col={"sm": 12, "md": 6, "lg": 3},
                    )
                )
            else:
                controls.append(ft.Container(control, col={"sm": 12, "md": 6, "lg": 3}))

        clear_button = ft.OutlinedButton(
            "Limpiar filtros",
            icon=ft.Icons.FILTER_ALT_OFF,
            on_click=lambda e: self._clear_filters(),
            style=ft.ButtonStyle(
                color=COLORS["text_soft"],
                side=ft.BorderSide(1, COLORS["border"]),
                shape=ft.RoundedRectangleBorder(radius=14),
            ),
            height=44,
        )

        return panel(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Filtros", color=COLORS["text_main"], size=16, weight=ft.FontWeight.W_600),
                            clear_button,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.ResponsiveRow(controls, columns=12, run_spacing=12),
                ],
                spacing=14,
            ),
            padding=20,
        )

    def _build_rows_panel(self, rows: list[dict]):
        if not rows:
            return panel(self._empty_state("No hay resultados con los filtros actuales."), padding=20)

        cards = []
        for row in rows:
            cards.append(ft.Container(self._build_record_card(row), col={"sm": 12, "lg": 6, "xl": 4}))
        return ft.ResponsiveRow(cards, columns=12, run_spacing=14)

    def _build_record_card(self, row: dict):
        details = []
        for key in self.current_config.get("summary_fields") or self.current_config["table_columns"]:
            if key == "id":
                continue
            details.append(
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=6),
                    border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
                    content=ft.Row(
                        [
                            ft.Text(self._field_label(key), color=COLORS["text_soft"], size=11, expand=True),
                            ft.Text(self._format_value(row.get(key)), color=COLORS["text_main"], size=12, text_align=ft.TextAlign.RIGHT),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                )
            )

        relation_blocks = [
            self._build_relation_preview(row, relation)
            for relation in self._relations_for_current_config()
        ]

        action_row = ft.Row(
            self._record_actions(row),
            wrap=True,
            spacing=6,
            run_spacing=6,
        )

        return panel(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=40,
                                height=40,
                                border_radius=14,
                                bgcolor=COLORS["accent_soft"],
                                alignment=ft.Alignment(0, 0),
                                content=ft.Icon(self._icon_for(self.current_config), color=COLORS["accent"]),
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        self._record_title(row),
                                        color=COLORS["text_main"],
                                        size=16,
                                        weight=ft.FontWeight.W_700,
                                    ),
                                    ft.Text(
                                        self.current_config.get("singular_title", self.current_config["title"]),
                                        color=COLORS["text_muted"],
                                        size=11,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Column(details, spacing=0),
                    *relation_blocks,
                    action_row,
                ],
                spacing=14,
            ),
            padding=18,
        )

    def _record_actions(self, row: dict):
        controls = [
            ft.OutlinedButton(
                "Editar",
                icon=ft.Icons.EDIT,
                on_click=lambda e, item=row: self._open_form(item),
                style=ft.ButtonStyle(
                    color=COLORS["warning"],
                    side=ft.BorderSide(1, COLORS["warning"]),
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),
            ),
            ft.OutlinedButton(
                "Eliminar",
                icon=ft.Icons.DELETE_OUTLINE,
                on_click=lambda e, item=row: self._confirm_delete(item),
                style=ft.ButtonStyle(
                    color=COLORS["danger"],
                    side=ft.BorderSide(1, COLORS["danger"]),
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),
            ),
        ]

        if "backfill" in self.current_config.get("extra_actions", []):
            controls.append(
                ft.ElevatedButton(
                    "Backfill",
                    icon=ft.Icons.PUBLISHED_WITH_CHANGES,
                    on_click=lambda e, item=row: self._run_backfill(item),
                    style=button_style("success"),
                )
            )
        if self.current_key == "proveedores":
            controls.append(
                ft.OutlinedButton(
                    "WhatsApp",
                    icon=ft.Icons.CHAT,
                    on_click=lambda e, item=row: self._send_whatsapp(item),
                    style=ft.ButtonStyle(
                        color=COLORS["success"],
                        side=ft.BorderSide(1, COLORS["success"]),
                        shape=ft.RoundedRectangleBorder(radius=12),
                    ),
                )
            )
            controls.append(
                ft.OutlinedButton(
                    "Email",
                    icon=ft.Icons.EMAIL,
                    on_click=lambda e, item=row: self._send_email(item),
                    style=ft.ButtonStyle(
                        color=COLORS["accent"],
                        side=ft.BorderSide(1, COLORS["accent"]),
                        shape=ft.RoundedRectangleBorder(radius=12),
                    ),
                )
            )

        if self.current_key == "ventas":
            controls.append(
                ft.OutlinedButton(
                    "Imprimir",
                    icon=ft.Icons.PRINT_OUTLINED,
                    on_click=lambda e, item=row: self._open_venta_print(item),
                    style=ft.ButtonStyle(
                        color=COLORS["accent"],
                        side=ft.BorderSide(1, COLORS["accent"]),
                        shape=ft.RoundedRectangleBorder(radius=12),
                    ),
                )
            )
        return controls

    def _send_whatsapp(self, row: dict):
        phone = row.get("numeroTelefono", "") or ""
        digits = "+" + "".join(ch for ch in phone if ch.isdigit())
        if not digits or digits == "+":
            self.feedback.value = "Teléfono no disponible para WhatsApp."
            self.page.update()
            return

        message = quote(f"Hola {row.get('nombre', 'Proveedor')}.")
        url = f"https://wa.me/{digits.lstrip('+')}?text={message}"
        asyncio.create_task(self.page.launch_url(url))

    def _send_email(self, row: dict):
        email = row.get("email", "") or ""
        if not email:
            self.feedback.value = "Email no disponible para este proveedor."
            self.page.update()
            return

        subject = quote("Contacto desde ManGen")
        body = quote(f"Hola {row.get('nombre', 'Proveedor')},%0D%0A%0D%0AMe gustaría coordinar una compra.")
        url = f"mailto:{email}?subject={subject}&body={body}"
        asyncio.create_task(self.page.launch_url(url))

    def _build_relation_preview(self, row: dict, relation: dict):
        relation_items = []
        error_text = ft.Text("", color=COLORS["danger"], size=11)

        try:
            relation_items = self._get_relation_items(relation, row["id"])
        except ApiError as exc:
            error_text.value = str(exc)

        content = []
        if relation_items:
            preview_cards = [
                self._build_relation_preview_card(relation, relation_item)
                for relation_item in relation_items[:4]
            ]
            if self.current_key == "proveedores" and relation.get("payload_id_key") == "materiaPrimaId":
                content.append(ft.ResponsiveRow(preview_cards, columns=2, run_spacing=8, spacing=8))
            else:
                content.extend(preview_cards)
            if len(relation_items) > 4:
                content.append(ft.Text(f"+ {len(relation_items) - 4} relacion(es) mas", color=COLORS["text_muted"], size=11))
        else:
            content.append(ft.Text(relation.get("empty_text", "Sin relaciones."), color=COLORS["text_soft"], size=11))

        if error_text.value:
            content.append(error_text)

        return ft.Container(
            padding=14,
            border_radius=14,
            bgcolor=COLORS["glass"],
            border=ft.border.all(1, COLORS["border"]),
            content=ft.Column(
                [
                    ft.Text(relation["title"], color=COLORS["text_main"], size=13, weight=ft.FontWeight.W_600),
                    *content,
                ],
                spacing=8,
            ),
        )

    def _open_form(self, item: dict | None = None):
        is_edit = item is not None
        title = f"{'Editar' if is_edit else 'Nuevo'} {self.current_config.get('singular_title', self.current_config['title'])}"
        controls = []
        inputs = {}

        for field in self.current_config["fields"]:
            if field.get("create_only") and is_edit:
                continue
            if field.get("edit_only") and not is_edit:
                continue

            initial = "" if not item else item.get(field["key"], "")
            entry = self._create_input_entry(field, initial, is_edit)
            inputs[field["key"]] = entry
            controls.append(entry["view"])

        relation_states = []
        relations = self._relations_for_current_config()
        if relations:
            controls.extend(
                [
                    ft.Divider(color=COLORS["border"]),
                    ft.Text("Relaciones", color=COLORS["text_main"], size=18, weight=ft.FontWeight.W_600),
                ]
            )
            for relation in relations:
                relation_state = self._build_inline_relation_state(relation, item)
                relation_states.append(relation_state)
                controls.extend(
                    [
                        ft.Text(relation["title"], color=COLORS["text_main"], size=14, weight=ft.FontWeight.W_600),
                        relation_state["view"],
                    ]
                )

        totals_relation_state = next((state for state in relation_states if state["relation"].get("price_field")), None)
        self._configure_totals(inputs, totals_relation_state, item)

        form_error = ft.Text("", size=12, color=COLORS["danger"])

        def submit(_):
            try:
                payload = self._build_payload(inputs, is_edit)
                if is_edit:
                    self.api.put(f"{self.current_config['endpoint']}/{item['id']}", payload)
                    self.feedback.value = "Registro actualizado correctamente."
                else:
                    created = self.api.post(self.current_config["endpoint"], payload)
                    self._persist_inline_relations(created, relation_states)
                    self.feedback.value = "Registro creado correctamente."
                self.feedback.color = COLORS["success"]
                dlg.open = False
                self._refresh_table()
            except Exception as exc:
                form_error.value = str(exc)
                self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["bg_panel"],
            title=ft.Text(title, color=COLORS["text_main"]),
            content=ft.Container(
                width=640,
                content=ft.Column(
                    controls + [form_error],
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                    height=520,
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close_dialog(dlg)),
                ft.ElevatedButton("Guardar", on_click=submit, style=button_style("primary")),
            ],
        )
        self.page.show_dialog(dlg)

    def _build_relation_preview_card(self, relation: dict, relation_item: dict):
        detail_lines = self._relation_display_lines(relation, relation_item)
        card = ft.Container(
            padding=10,
            border_radius=12,
            bgcolor=COLORS["bg_app"],
            border=ft.border.all(1, COLORS["border"]),
            content=ft.Column(
                [
                    ft.Text(
                        self._related_label_from_relation_item(relation_item),
                        color=COLORS["text_main"],
                        size=12,
                        weight=ft.FontWeight.W_600,
                    ),
                    *[
                        ft.Text(line, color=COLORS["text_soft"], size=11)
                        for line in detail_lines
                    ],
                ],
                spacing=4,
            ),
        )
        if self.current_key == "proveedores" and relation.get("payload_id_key") == "materiaPrimaId":
            return ft.Container(card, col={"sm": 2, "md": 1})
        return card

    def _open_venta_print(self, item: dict):
        relation = self.current_config.get("relation")
        products = []
        if relation:
            try:
                products = self._get_relation_items(relation, item["id"])
            except ApiError as exc:
                self.feedback.value = str(exc)
                self.feedback.color = COLORS["danger"]
                self.page.update()
                return

        product_rows = []
        if products:
            for product in products:
                values = self._extract_relation_values(product, relation)
                quantity = self._format_quantity_display(values.get("cantidad"))
                unit_price = self._format_value(self._extract_related_price(product, relation.get("price_field", "precio")))
                product_rows.append(
                    ft.Container(
                        padding=10,
                        border_radius=12,
                        bgcolor=COLORS["bg_app"],
                        border=ft.border.all(1, COLORS["border"]),
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(self._related_label_from_relation_item(product), color=COLORS["text_main"], size=13, weight=ft.FontWeight.W_600),
                                        ft.Text(f"Cantidad: {quantity}", color=COLORS["text_soft"], size=11),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.Text(f"Unitario: {unit_price}", color=COLORS["accent"], size=11, weight=ft.FontWeight.W_600),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    )
                )
        else:
            product_rows.append(ft.Text("No hay productos asociados.", color=COLORS["text_soft"], size=12))

        printers = self._detect_printers()
        printer_note = (
            ft.Text(
                f"Impresora detectada: {printers[0]}",
                color=COLORS["success"],
                size=12,
            )
            if printers
            else ft.Text(
                "No se detecto impresora local. Puedes revisar la vista previa, pero no se intentara imprimir automaticamente.",
                color=COLORS["warning"],
                size=12,
            )
        )

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["bg_panel"],
            title=ft.Text("Imprimir venta", color=COLORS["text_main"]),
            content=ft.Container(
                width=620,
                content=ft.Column(
                    [
                        ft.Text(f"Metodo de pago: {item.get('metodoPago', '-')}", color=COLORS["text_main"], size=13),
                        ft.Text(f"Fecha: {self._format_value(item.get('fecha'))}", color=COLORS["text_soft"], size=12),
                        ft.Text(f"Total: {self._format_value(item.get('total'))}", color=COLORS["text_main"], size=13),
                        ft.Text(f"Total con descuento: {self._format_value(item.get('totalDesc'))}", color=COLORS["text_soft"], size=12),
                        printer_note,
                        ft.Divider(color=COLORS["border"]),
                        ft.Text("Productos", color=COLORS["text_main"], size=16, weight=ft.FontWeight.W_600),
                        *product_rows,
                    ],
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                    height=420,
                ),
            ),
            actions=[
                *(
                    [
                        ft.ElevatedButton(
                            "Imprimir ahora",
                            icon=ft.Icons.PRINT,
                            on_click=lambda e: self._print_venta(item, products, dlg),
                            style=button_style("accent"),
                        )
                    ]
                    if printers
                    else []
                ),
                ft.TextButton("Cerrar", on_click=lambda e: self._close_dialog(dlg)),
            ],
        )
        self.page.show_dialog(dlg)

    def _print_venta(self, item: dict, products: list[dict], dlg):
        printers = self._detect_printers()
        if not printers:
            self.feedback.value = "No se detecto ninguna impresora local para esta venta."
            self.feedback.color = COLORS["danger"]
            dlg.open = False
            self.page.update()
            return

        try:
            receipt_text = self._build_venta_receipt_text(item, products)
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as temp_file:
                temp_file.write(receipt_text)
                temp_path = temp_file.name

            if os.name == "nt":
                subprocess.run(["notepad.exe", "/p", temp_path], check=True, timeout=20)
            else:
                raise ApiError("La impresion automatica solo esta soportada en escritorio Windows.")

            self.feedback.value = f"Venta enviada a imprimir en {printers[0]}."
            self.feedback.color = COLORS["success"]
            dlg.open = False
            self.page.update()
        except Exception as exc:
            self.feedback.value = f"No se pudo imprimir la venta: {exc}"
            self.feedback.color = COLORS["danger"]
            self.page.update()

    def _build_venta_receipt_text(self, item: dict, products: list[dict]):
        lines = [
            "VENTA",
            "",
            f"Metodo de pago: {item.get('metodoPago', '-')}",
            f"Fecha: {self._format_value(item.get('fecha'))}",
            f"Total: {self._format_value(item.get('total'))}",
            f"Total con descuento: {self._format_value(item.get('totalDesc'))}",
            "",
            "PRODUCTOS",
            "",
        ]

        relation = self.current_config.get("relation")
        if products:
            for product in products:
                values = self._extract_relation_values(product, relation) if relation else {}
                quantity = self._format_quantity_display(values.get("cantidad"))
                unit_price = self._format_value(self._extract_related_price(product, relation.get("price_field", "precio"))) if relation else "-"
                lines.extend(
                    [
                        f"- {self._related_label_from_relation_item(product)}",
                        f"  Cantidad: {quantity}",
                        f"  Precio unitario: {unit_price}",
                    ]
                )
        else:
            lines.append("Sin productos asociados.")

        return "\n".join(lines)

    def _detect_printers(self):
        if getattr(self.page, "web", False) or os.name != "nt":
            return []
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-Printer | Select-Object -ExpandProperty Name",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except Exception:
            return []


    def _confirm_delete(self, item: dict):
        def remove(_):
            try:
                self.api.delete(f"{self.current_config['endpoint']}/{item['id']}")
                self.feedback.value = "Registro eliminado correctamente."
                self.feedback.color = COLORS["success"]
                dlg.open = False
                self._refresh_table()
            except ApiError as exc:
                self.feedback.value = str(exc)
                self.feedback.color = COLORS["danger"]
                dlg.open = False
                self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["bg_panel"],
            title=ft.Text("Confirmar eliminacion", color=COLORS["text_main"]),
            content=ft.Text(
                "Se eliminara este registro de la sucursal actual.",
                color=COLORS["text_soft"],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close_dialog(dlg)),
                ft.ElevatedButton("Eliminar", on_click=remove, style=button_style("danger")),
            ],
        )
        self.page.show_dialog(dlg)

    def _run_backfill(self, item: dict):
        try:
            result = self.api.post(f"/apiManGen/Sucursal/{item['id']}/backfill")
            self.feedback.value = f"Backfill ejecutado: {result}"
            self.feedback.color = COLORS["success"]
            self.page.update()
        except ApiError as exc:
            self.feedback.value = str(exc)
            self.feedback.color = COLORS["danger"]
            self.page.update()

    def _open_pedido_to_venta(self):
        error = ft.Text("", size=12, color=COLORS["danger"])
        affect_stock = ft.Switch(
            label="Afectar stock",
            value=True,
            active_color=COLORS["success"],
        )
        selected_state = {"pedido_id": None}
        try:
            pedidos = self.api.get("/apiManGen/Pedidos") or []
        except Exception as exc:
            self.feedback.value = str(exc)
            self.feedback.color = COLORS["danger"]
            self.page.update()
            return
        list_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=280)

        def select_pedido(pedido_id: int):
            selected_state["pedido_id"] = pedido_id
            render_pedidos()

        def render_pedidos():
            cards = []
            for pedido in pedidos:
                pedido_id = pedido.get("id")
                active = pedido_id == selected_state["pedido_id"]
                cards.append(
                    ft.Container(
                        padding=14,
                        border_radius=14,
                        bgcolor=COLORS["accent_soft"] if active else COLORS["bg_app"],
                        border=ft.border.all(1, COLORS["accent"] if active else COLORS["border"]),
                        ink=True,
                        on_click=lambda e, pid=pedido_id: select_pedido(pid),
                        content=ft.Column(
                            [
                                ft.Text(
                                    self._record_title(pedido),
                                    color=COLORS["text_main"],
                                    size=14,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Text(
                                    f"Estado: {pedido.get('estado', '-')}",
                                    color=COLORS["text_soft"],
                                    size=11,
                                ),
                                ft.Text(
                                    f"Total: {self._format_value(pedido.get('total'))}",
                                    color=COLORS["text_soft"],
                                    size=11,
                                ),
                            ],
                            spacing=4,
                        ),
                    )
                )
            if not cards:
                cards = [self._empty_state("No hay pedidos disponibles para convertir en venta.")]
            list_column.controls = cards

        def submit(_):
            try:
                pedido_id = selected_state["pedido_id"]
                if pedido_id is None:
                    raise ApiError("Selecciona un pedido.")
                path = f"/apiManGen/Ventas/desde-pedido/{pedido_id}"
                if affect_stock.value:
                    path += "/con-stock"
                self.api.post(path)
                self.feedback.value = "Venta creada desde pedido correctamente."
                self.feedback.color = COLORS["success"]
                dlg.open = False
                self._refresh_table()
            except Exception as exc:
                error.value = str(exc)
                self.page.update()

        render_pedidos()
        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["bg_panel"],
            title=ft.Text("Generar venta desde pedido", color=COLORS["text_main"]),
            content=ft.Container(
                width=540,
                content=ft.Column(
                    [
                        ft.Text(
                            "Selecciona un pedido. La venta impacta stock por defecto y el pedido pasara a Terminado.",
                            color=COLORS["text_soft"],
                            size=12,
                        ),
                        affect_stock,
                        list_column,
                        error,
                    ],
                    tight=True,
                    spacing=12,
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close_dialog(dlg)),
                ft.ElevatedButton("Crear venta", on_click=submit, style=button_style("primary")),
            ],
        )
        self.page.show_dialog(dlg)

    def _build_payload(self, inputs: dict, is_edit: bool):
        payload = {}
        for key, entry in inputs.items():
            field = entry["field"]
            value = entry["get_value"]()
            if field["type"] == "number":
                if value in ("", None):
                    if field.get("required"):
                        raise ApiError(f"El campo {field['label']} es obligatorio.")
                    continue
                value = self._parse_number(value, field["label"])
            elif isinstance(value, str):
                value = value.strip()

            if field.get("required") and value in ("", None):
                raise ApiError(f"El campo {field['label']} es obligatorio.")

            if is_edit and key == "password" and not value:
                continue
            if value not in ("", None):
                payload[key] = value
        return payload

    def _create_input_entry(self, field: dict, initial, is_edit: bool):
        if field["type"] == "select":
            control = ft.Dropdown(
                label=field["label"],
                value=initial,
                options=[ft.dropdown.Option(option) for option in field["options"]],
                **input_style(as_dropdown=True),
            )
            return {
                "field": field,
                "control": control,
                "view": control,
                "get_value": lambda c=control: c.value,
            }

        if field["type"] == "date":
            return self._create_date_entry(field, initial, is_edit)

        control = ft.TextField(
            label=field["label"],
            value="" if initial is None else str(initial),
            password=field["type"] == "password",
            can_reveal_password=field["type"] == "password",
            multiline=field.get("multiline", False),
            min_lines=3 if field.get("multiline") else 1,
            max_lines=5 if field.get("multiline") else 1,
            keyboard_type=ft.KeyboardType.NUMBER if field["type"] == "number" else ft.KeyboardType.TEXT,
            **input_style(),
        )
        return {
            "field": field,
            "control": control,
            "view": control,
            "get_value": lambda c=control: c.value,
        }

    def _create_date_entry(self, field: dict, initial, is_edit: bool):
        selected = self._parse_iso_value(initial)
        if not selected and field.get("auto_now_local_on_create") and not is_edit:
            selected = datetime.now().astimezone()

        text_field = ft.TextField(
            label=field["label"],
            value=self._format_date_display(selected, field),
            read_only=True,
            **input_style(),
        )

        state = {"selected": selected}

        def on_change(event):
            value = event.control.value
            if isinstance(value, date) and not isinstance(value, datetime):
                selected_dt = datetime.combine(
                    value,
                    time.min,
                    tzinfo=datetime.now().astimezone().tzinfo,
                )
            else:
                selected_dt = value
            state["selected"] = selected_dt
            text_field.value = self._format_date_display(selected_dt, field)
            self.page.update()

        picker = ft.DatePicker(
            value=selected.date() if isinstance(selected, datetime) else selected,
            first_date=date(2000, 1, 1),
            last_date=date(2100, 12, 31),
            current_date=date.today(),
            help_text=field["label"],
            cancel_text="Cancelar",
            confirm_text="Aceptar",
            on_change=on_change,
        )

        def open_picker(_):
            self.page.show_dialog(picker)

        helper_text = None
        if field.get("auto_now_local_on_create") and not is_edit:
            helper_text = ft.Text(
                "Se asigna automaticamente con la fecha y hora local.",
                size=11,
                color=COLORS["text_soft"],
            )

        view = ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(content=text_field, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.CALENDAR_MONTH,
                            icon_color=COLORS["accent"],
                            tooltip="Seleccionar fecha",
                            on_click=open_picker,
                            disabled=field.get("auto_now_local_on_create") and not is_edit,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
                *([helper_text] if helper_text else []),
            ],
            spacing=6,
            tight=True,
        )

        return {
            "field": field,
            "control": text_field,
            "view": view,
            "get_value": lambda s=state, f=field: self._serialize_date_value(s["selected"], f),
        }

    def _build_inline_relation_state(self, relation: dict, item: dict | None = None):
        error_text = ft.Text("", color=COLORS["danger"], size=12)
        related_rows = self.api.get(relation["related_endpoint"]) or []
        option_map = {}
        for related in related_rows:
            related_id = related.get("id")
            if related_id is None:
                continue
            option_map[str(related_id)] = {
                "label": self._related_label_from_row(related),
                "price": self._coerce_float(related.get(relation.get("price_field", "precio"))),
                "row": related,
            }

        dropdown = ft.Dropdown(
            label="Entidad relacionada",
            options=[
                ft.dropdown.Option(key=key, text=option["label"])
                for key, option in option_map.items()
            ],
            **input_style(as_dropdown=True),
        )
        relation_fields = self._relation_fields(relation)
        field_entries = {}
        field_controls = []
        for field in relation_fields:
            entry = self._create_input_entry(field, field.get("default", ""), False)
            field_entries[field["key"]] = entry
            field_controls.append(ft.Container(entry["view"], col={"sm": 12, "md": 3}))
        has_stock_variant = any(
            relation.get(key)
            for key in ("create_path_stock", "update_path_stock", "delete_path_stock")
        )
        use_stock = ft.Switch(
            label=relation.get("stock_toggle_label", "Ajustar stock"),
            value=False,
            active_color=COLORS["success"],
            visible=has_stock_variant,
        )
        action_button = ft.ElevatedButton(
            "Agregar relacion",
            icon=ft.Icons.ADD_LINK,
            style=button_style("accent"),
            height=44,
        )
        cancel_edit_button = ft.OutlinedButton(
            "Cancelar edicion",
            visible=False,
            height=44,
            style=ft.ButtonStyle(
                color=COLORS["text_soft"],
                side=ft.BorderSide(1, COLORS["border"]),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )
        selected_items = {}
        list_column = ft.Column(spacing=8)
        state = {
            "relation": relation,
            "item": item,
            "selected_items": selected_items,
            "use_stock": use_stock,
            "editing_related_id": None,
            "on_change": None,
        }

        def set_editing(related_id: int | None):
            state["editing_related_id"] = related_id
            cancel_edit_button.visible = related_id is not None
            if related_id is None:
                action_button.text = "Agregar relacion"
                action_button.icon = ft.Icons.ADD_LINK
                action_button.style = button_style("accent")
                dropdown.value = None
                self._set_relation_form_values(field_entries, relation_fields, {})
            else:
                current = selected_items[related_id]
                dropdown.value = str(related_id)
                self._set_relation_form_values(field_entries, relation_fields, current["values"])
                action_button.text = "Actualizar relacion"
                action_button.icon = ft.Icons.SAVE
                action_button.style = button_style("primary")
            self.page.update()

        def refresh_selected():
            if not selected_items:
                list_column.controls = [self._empty_state("Todavia no hay relaciones agregadas.")]
            else:
                cards = []
                for related_id, related_item in selected_items.items():
                    cards.append(
                        ft.Container(
                            padding=12,
                            border_radius=12,
                            bgcolor=COLORS["bg_app"],
                            border=ft.border.all(1, COLORS["border"]),
                            content=ft.Row(
                                [
                                    ft.Column(
                                [
                                    ft.Text(related_item["label"], color=COLORS["text_main"], size=13, weight=ft.FontWeight.W_600),
                                    *[
                                        ft.Text(line, color=COLORS["text_soft"] if index == 0 else COLORS["text_muted"], size=11)
                                        for index, line in enumerate(self._relation_display_lines(relation, related_item["values"], from_state=True))
                                    ],
                                        ],
                                        spacing=2,
                                        expand=True,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        icon_color=COLORS["warning"],
                                        tooltip="Editar relacion",
                                        on_click=lambda e, rid=related_id: set_editing(rid),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=COLORS["danger"],
                                        tooltip="Quitar relacion",
                                        on_click=lambda e, rid=related_id: remove_selected(rid),
                                    ),
                                ]
                            ),
                        )
                    )
                list_column.controls = cards
            if callable(state.get("on_change")):
                state["on_change"]()
            self.page.update()

        def remove_selected(related_id):
            try:
                if item is not None:
                    self._delete_existing_relation(
                        relation=relation,
                        item=item,
                        related_id=related_id,
                        use_stock=use_stock.value,
                    )
                    self._load_existing_relations(state, option_map)
                else:
                    selected_items.pop(related_id, None)
                if state["editing_related_id"] == related_id:
                    set_editing(None)
                error_text.value = ""
                refresh_selected()
            except Exception as exc:
                error_text.value = str(exc)
                self.page.update()

        def add_or_update_selected(_):
            try:
                if not dropdown.value:
                    raise ApiError("Selecciona una entidad relacionada.")

                related_id = int(dropdown.value)
                option = option_map.get(dropdown.value, {"label": "Relacion", "price": 0.0})
                label = option["label"]
                values = self._read_relation_form_values(relation, field_entries)

                if item is not None:
                    self._save_existing_relation(
                        relation=relation,
                        item=item,
                        related_id=related_id,
                        values=values,
                        use_stock=use_stock.value,
                        already_exists=related_id in selected_items,
                    )
                    self._load_existing_relations(state, option_map)
                else:
                    selected_items[related_id] = {
                        "label": label,
                        "values": values,
                        "unit_price": option.get("price", 0.0),
                    }

                error_text.value = ""
                set_editing(None)
                refresh_selected()
            except Exception as exc:
                error_text.value = str(exc)
                self.page.update()

        action_button.on_click = add_or_update_selected
        cancel_edit_button.on_click = lambda _: set_editing(None)

        if item is not None:
            self._load_existing_relations(state, option_map)

        refresh_selected()

        view = ft.Column(
            [
                ft.ResponsiveRow(
                    [
                        ft.Container(dropdown, col={"sm": 12, "md": 5}),
                        *field_controls,
                        ft.Container(action_button, col={"sm": 12, "md": 2}),
                        ft.Container(cancel_edit_button, col={"sm": 12, "md": 2}),
                    ],
                    run_spacing=10,
                ),
                use_stock,
                error_text,
                list_column,
            ],
            spacing=10,
        )
        state["view"] = view
        return state

    def _persist_inline_relations(self, created, relation_states):
        if not isinstance(created, dict) or created.get("id") is None:
            raise ApiError("La API no devolvio el identificador del registro creado para guardar las relaciones.")
        created_id = created["id"]
        for relation_state in relation_states or []:
            if not relation_state["selected_items"]:
                continue
            relation = relation_state["relation"]
            path_key = "create_path_stock" if relation_state["use_stock"].value and relation.get("create_path_stock") else "create_path"
            path_template = relation[path_key]
            for related_id, relation_item in relation_state["selected_items"].items():
                payload = self._relation_payload(relation, related_id, relation_item["values"])
                self.api.post(path_template.format(**self._relation_path_values(relation, created_id, related_id)), payload)

    def _load_existing_relations(self, state: dict, option_map: dict[str, str]):
        relation = state["relation"]
        item = state["item"]
        related_items = self.api.get(relation["list_path"].format(id=item["id"])) or []
        state["selected_items"].clear()
        for related_item in related_items:
            related_id = self._extract_related_id(related_item, relation)
            if related_id is None:
                continue
            option = option_map.get(str(related_id), {})
            label = option.get("label") or self._related_label_from_relation_item(related_item)
            state["selected_items"][related_id] = {
                "label": label,
                "values": self._extract_relation_values(related_item, relation),
                "unit_price": option.get("price", self._extract_related_price(related_item, relation.get("price_field", "precio"))),
            }

    def _save_existing_relation(self, relation: dict, item: dict, related_id: int, values: dict, use_stock: bool, already_exists: bool):
        if already_exists:
            update_path = relation.get("update_path_stock") if use_stock else relation["update_path"]
            self.api.patch(
                update_path.format(**self._relation_path_values(relation, item["id"], related_id)),
                self._relation_update_payload(relation, values),
            )
            return

        payload = self._relation_payload(relation, related_id, values)
        create_path = relation.get("create_path_stock") if use_stock else relation["create_path"]
        self.api.post(create_path.format(**self._relation_path_values(relation, item["id"], related_id)), payload)

    def _delete_existing_relation(self, relation: dict, item: dict, related_id: int, use_stock: bool):
        delete_path = relation.get("delete_path_stock") if use_stock else relation.get("delete_path")
        if delete_path:
            self.api.delete(delete_path.format(**self._relation_path_values(relation, item["id"], related_id)))
            return

        # Some relation endpoints only document create/update; setting quantity to 0
        # provides a best-effort removal path for those cases.
        update_path = relation.get("update_path_stock") if use_stock else relation.get("update_path")
        if not update_path:
            raise ApiError("No se puede eliminar esta relacion desde la interfaz.")
        self.api.patch(
            update_path.format(**self._relation_path_values(relation, item["id"], related_id)),
            self._relation_delete_payload(relation),
        )

    def _configure_totals(self, inputs: dict, relation_state: dict | None, item: dict | None):
        if self.current_key not in {"pedidos", "ventas"}:
            return
        total_entry = inputs.get("total")
        total_desc_entry = inputs.get("totalDesc")
        if not total_entry or not total_desc_entry:
            return

        total_control = total_entry["control"]
        total_desc_control = total_desc_entry["control"]
        state = {
            "manual_total": False,
            "manual_total_desc": False,
        }

        def mark_total_manual(_):
            state["manual_total"] = True

        def mark_total_desc_manual(_):
            state["manual_total_desc"] = True

        total_control.on_change = mark_total_manual
        total_desc_control.on_change = mark_total_desc_manual

        def apply_totals(force: bool = False):
            calculated = self._calculate_relation_total(relation_state)
            if calculated is None:
                return
            if force or not state["manual_total"] or not total_control.value:
                total_control.value = self._format_decimal_input(calculated)
                state["manual_total"] = False
            if force or not state["manual_total_desc"] or not total_desc_control.value:
                total_desc_control.value = self._format_decimal_input(calculated)
                state["manual_total_desc"] = False

        if relation_state is not None:
            # When products change inside pedidos/ventas, totals must be rebuilt
            # from the current relation state instead of preserving stale manual edits.
            relation_state["on_change"] = lambda: apply_totals(True)

        helper = ft.Row(
            [
                ft.Text(
                    "Los totales se calculan a partir de los productos y luego puedes ajustarlos manualmente.",
                    color=COLORS["text_soft"],
                    size=11,
                    expand=True,
                ),
                ft.OutlinedButton(
                    "Recalcular",
                    icon=ft.Icons.CALCULATE,
                    on_click=lambda e: (apply_totals(True), self.page.update()),
                    style=ft.ButtonStyle(
                        color=COLORS["accent"],
                        side=ft.BorderSide(1, COLORS["accent"]),
                        shape=ft.RoundedRectangleBorder(radius=12),
                    ),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        total_desc_entry["view"] = ft.Column([total_desc_entry["view"], helper], spacing=8, tight=True)

        if relation_state is not None:
            apply_totals(True)

    def _calculate_relation_total(self, relation_state: dict | None):
        if not relation_state:
            return None
        total = 0.0
        has_items = False
        for related_item in relation_state["selected_items"].values():
            values = related_item.get("values", {})
            quantity = self._coerce_float(values.get("cantidad"))
            unit_price = self._coerce_float(related_item.get("unit_price", values.get("precio")))
            total += quantity * unit_price
            has_items = True
        return total if has_items else 0.0

    def _parse_number(self, value, label: str):
        if isinstance(value, (int, float)):
            return float(value)
        try:
            normalized = str(value).strip().replace(",", ".")
            return float(normalized)
        except (TypeError, ValueError):
            raise ApiError(f"El campo {label} debe ser numerico.")

    @staticmethod
    def _serialize_relation_quantity(value):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return value
        return int(numeric) if numeric.is_integer() else numeric

    def _relation_payload(self, relation: dict, related_id: int, values: dict):
        return {
            relation["payload_id_key"]: related_id,
            **self._normalize_relation_values(relation, values),
        }

    def _relation_update_payload(self, relation: dict, values: dict):
        return self._normalize_relation_values(relation, values)

    def _relation_delete_payload(self, relation: dict):
        if any(field["key"] == "cantidad" for field in self._relation_fields(relation)):
            return {"cantidad": 0}
        raise ApiError("No se puede eliminar esta relacion desde la interfaz.")

    @staticmethod
    def _relation_path_values(relation: dict, item_id: int, related_id: int):
        values = {
            "id": item_id,
            "related_id": related_id,
        }
        related_path_key = relation.get("path_related_id_key")
        if related_path_key:
            values[related_path_key] = related_id
        return values

    @staticmethod
    def _coerce_float(value, default: float = 0.0):
        try:
            if value in ("", None):
                return default
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _format_decimal_input(value: float):
        return f"{value:.2f}"

    def _relations_for_current_config(self):
        relations = self.current_config.get("relations")
        if relations:
            return relations
        if self.current_config.get("relation"):
            return [self.current_config["relation"]]
        return []

    def _relation_fields(self, relation: dict):
        fields = relation.get("editor_fields")
        if fields:
            return fields
        return [
            {
                "key": "cantidad",
                "label": "Cantidad",
                "type": "number",
                "required": True,
                "default": "1",
            }
        ]

    def _read_relation_form_values(self, relation: dict, field_entries: dict):
        values = {}
        for field in self._relation_fields(relation):
            entry = field_entries[field["key"]]
            value = entry["get_value"]()
            if field["type"] == "number":
                if value in ("", None):
                    if field.get("required"):
                        raise ApiError(f"El campo {field['label']} es obligatorio.")
                    continue
                value = self._parse_number(value, field["label"])
                if field["key"] == "cantidad" and value <= 0:
                    raise ApiError("La cantidad debe ser mayor a cero.")
                value = self._serialize_relation_quantity(value)
            elif isinstance(value, str):
                value = value.strip()

            if field.get("required") and value in ("", None):
                raise ApiError(f"El campo {field['label']} es obligatorio.")
            values[field["key"]] = value
        return values

    def _set_relation_form_values(self, field_entries: dict, relation_fields: list[dict], values: dict):
        for field in relation_fields:
            control = field_entries[field["key"]]["control"]
            value = values.get(field["key"], field.get("default", ""))
            control.value = "" if value is None else str(value)

    def _extract_relation_values(self, related_item, relation: dict):
        values = {}
        for field in self._relation_fields(relation):
            lookup_keys = [field["key"]]
            if field["key"] == "cantidad" and relation.get("quantity_key"):
                lookup_keys.insert(0, relation["quantity_key"])
            values[field["key"]] = self._extract_relation_field_value(related_item, lookup_keys, field["type"])
        return values

    def _extract_relation_field_value(self, related_item, keys, field_type: str):
        if not isinstance(related_item, dict):
            return None
        if isinstance(keys, str):
            keys = [keys]
        for key in keys:
            direct_value = related_item.get(key)
            if direct_value not in (None, "") and not isinstance(direct_value, (dict, list)):
                return self._coerce_float(direct_value) if field_type == "number" else direct_value
        for value in related_item.values():
            if isinstance(value, dict):
                for key in keys:
                    nested_value = value.get(key)
                    if nested_value not in (None, ""):
                        return self._coerce_float(nested_value) if field_type == "number" else nested_value
        return None

    def _normalize_relation_values(self, relation: dict, values: dict):
        normalized = {}
        for field in self._relation_fields(relation):
            value = values.get(field["key"])
            if value in ("", None):
                continue
            if field["type"] == "number":
                normalized[field["key"]] = self._serialize_relation_quantity(value)
            elif isinstance(value, str):
                normalized[field["key"]] = value.strip()
            else:
                normalized[field["key"]] = value
        return normalized

    def _relation_display_lines(self, relation: dict, source, from_state: bool = False):
        display_fields = relation.get("display_fields")
        if display_fields:
            values = source if from_state else self._extract_relation_values(source, relation)
            lines = []
            for field in display_fields:
                raw_value = values.get(field["key"])
                if raw_value in ("", None):
                    continue
                if field.get("format") == "money":
                    rendered = self._format_value(self._coerce_float(raw_value))
                elif field.get("format") == "quantity":
                    rendered = self._format_quantity_display(raw_value)
                else:
                    rendered = str(raw_value)
                lines.append(f"{field['label']}: {rendered}")
            return lines

        values = source if from_state else self._extract_relation_values(source, relation)
        cantidad = values.get("cantidad")
        lines = []
        if cantidad not in ("", None):
            lines.append(f"Cantidad: {self._format_quantity_display(cantidad)}")
        unit_price = values.get("precio")
        if unit_price not in ("", None):
            lines.append(f"Precio: {self._format_value(self._coerce_float(unit_price))}")
        return lines

    def _get_relation_items(self, relation: dict, item_id: int):
        cache_key = (relation["list_path"], item_id)
        if cache_key in self.relation_items_cache:
            return self.relation_items_cache[cache_key]
        items = self.api.get(relation["list_path"].format(id=item_id)) or []
        self.relation_items_cache[cache_key] = items
        return items

    def _apply_filters(self, rows: list[dict]):
        filtered = rows
        if self._filter_value("search_nombre"):
            search_value = self._filter_value("search_nombre")
            filtered = [
                row for row in filtered
                if search_value in str(row.get("nombre", "")).lower()
                or search_value in self._record_title(row).lower()
            ]

        for key, entry in self.filter_inputs.items():
            if key == "search_nombre":
                continue
            raw_value = entry["control"].value
            if raw_value in (None, ""):
                continue

            if self.current_key == "proveedores" and key in {"materiaPrimaNombre", "marca", "precioMin", "precioMax"}:
                filtered = [row for row in filtered if self._provider_matches_offer_filters(row)]
                continue
            if self.current_key == "productos" and key == "materiaPrimaNombre":
                filtered = [row for row in filtered if self._product_matches_materia_prima_filter(row)]
                continue
            if self.current_key in {"ventas", "pedidos"} and key in {"totalMin", "totalMax"}:
                filtered = [row for row in filtered if self._row_matches_total_range(row)]
                continue

            value = str(raw_value).strip().lower()
            filter_type = entry["config"]["type"]
            if filter_type == "date":
                filtered = [row for row in filtered if value in self._format_value(row.get(key)).lower()]
            else:
                filtered = [row for row in filtered if value in str(row.get(key, "")).lower()]
        return filtered

    def _provider_matches_offer_filters(self, row: dict):
        relation = self.current_config.get("relation")
        if not relation:
            return True

        materia_nombre = self._filter_value("materiaPrimaNombre")
        marca = self._filter_value("marca")
        precio_min = self._filter_number_value("precioMin")
        precio_max = self._filter_number_value("precioMax")

        if not any(value is not None and value != "" for value in (materia_nombre, marca, precio_min, precio_max)):
            return True

        try:
            relation_items = self._get_relation_items(relation, row["id"])
        except ApiError:
            return False

        for relation_item in relation_items:
            if materia_nombre and materia_nombre not in self._related_label_from_relation_item(relation_item).lower():
                continue
            relation_values = self._extract_relation_values(relation_item, relation)
            if marca and marca not in str(relation_values.get("marca", "")).lower():
                continue
            precio = self._coerce_float(relation_values.get("precio"), None)
            if precio_min is not None and (precio is None or precio < precio_min):
                continue
            if precio_max is not None and (precio is None or precio > precio_max):
                continue
            return True
        return False

    def _product_matches_materia_prima_filter(self, row: dict):
        relation = self.current_config.get("relation")
        if not relation:
            return True
        materia_nombre = self._filter_value("materiaPrimaNombre")
        if not materia_nombre:
            return True
        try:
            relation_items = self._get_relation_items(relation, row["id"])
        except ApiError:
            return False
        return any(
            materia_nombre in self._related_label_from_relation_item(relation_item).lower()
            for relation_item in relation_items
        )

    def _row_matches_total_range(self, row: dict):
        total = self._coerce_float(row.get("total"), None)
        total_min = self._filter_number_value("totalMin")
        total_max = self._filter_number_value("totalMax")
        if total is None:
            return False
        if total_min is not None and total < total_min:
            return False
        if total_max is not None and total > total_max:
            return False
        return True

    def _filter_value(self, key: str):
        entry = self.filter_inputs.get(key)
        if not entry:
            return ""
        raw_value = entry["control"].value
        return str(raw_value).strip().lower() if raw_value not in (None, "") else ""

    def _filter_number_value(self, key: str):
        entry = self.filter_inputs.get(key)
        if not entry:
            return None
        raw_value = entry["control"].value
        if raw_value in (None, ""):
            return None
        try:
            return self._parse_number(raw_value, entry["config"]["label"])
        except ApiError:
            return None

    def _clear_filters(self):
        for entry in self.filter_inputs.values():
            entry["control"].value = None if isinstance(entry["control"], ft.Dropdown) else ""
        self._render_rows()

    def _set_today_filter(self, key: str):
        entry = self.filter_inputs.get(key)
        if not entry:
            return
        today_value = date.today().strftime("%d/%m/%Y")
        control = entry["control"]
        control.value = today_value
        self._render_rows()

    def _export_filtered_rows(self):
        rows = self._apply_filters(self.rows_cache)
        if not rows:
            self.feedback.value = "No hay registros para exportar."
            self.feedback.color = COLORS["warning"]
            self.page.update()
            return
        filename = f"{self.current_config.get('key', 'export')}.csv"
        self._write_rows_to_csv(filename, rows)

    def _export_branch_workbook(self):
        all_data = []
        for entity in self.entities:
            try:
                rows = self.api.get(entity["endpoint"]) or []
            except ApiError as exc:
                self.feedback.value = f"No se pudieron cargar {entity['title']}: {exc}"
                self.feedback.color = COLORS["danger"]
                self.page.update()
                return
            all_data.append((entity["title"], rows))

        if not all_data:
            self.feedback.value = "No hay datos para exportar de la sucursal."
            self.feedback.color = COLORS["warning"]
            self.page.update()
            return

        branch_name = self.user.get("nombre", "sucursal").replace(" ", "_")
        filename = f"sucursal_{branch_name}_datos.csv"
        self._write_branch_csv(filename, all_data)

    def _write_rows_to_csv(self, filename: str, rows: list[dict]):
        if not rows:
            return
        headers = list(rows[0].keys())
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", encoding="utf-8", newline="") as temp_file:
            writer = csv.writer(temp_file, delimiter=';')
            writer.writerow(headers)
            for row in rows:
                writer.writerow([self._export_value(row.get(key)) for key in headers])
            temp_path = temp_file.name

        self._open_file(temp_path)
        self.feedback.value = f"Excel generado: {filename}"
        self.feedback.color = COLORS["success"]
        self.page.update()

    def _write_branch_csv(self, filename: str, all_data: list[tuple[str, list[dict]]]):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", encoding="utf-8", newline="") as temp_file:
            writer = csv.writer(temp_file, delimiter=';')
            for title, rows in all_data:
                writer.writerow([title])
                if not rows:
                    writer.writerow(["Sin registros"])
                else:
                    headers = list(rows[0].keys())
                    writer.writerow(headers)
                    for row in rows:
                        writer.writerow([self._export_value(row.get(key)) for key in headers])
                writer.writerow([])
            temp_path = temp_file.name

        self._open_file(temp_path)
        self.feedback.value = "Excel de sucursal generado."
        self.feedback.color = COLORS["success"]
        self.page.update()

    def _export_value(self, value):
        if isinstance(value, dict):
            return str({k: self._export_value(v) for k, v in value.items()})
        if isinstance(value, list):
            return ", ".join(str(self._export_value(item)) for item in value)
        if value is None:
            return ""
        return str(value)

    def _open_file(self, path: str):
        try:
            if os.name == "nt":
                os.startfile(path)
            elif subprocess.run(["xdg-open", path], capture_output=True).returncode == 0:
                pass
        except Exception:
            self.feedback.value = f"Archivo generado en: {path}"
            self.feedback.color = COLORS["text_soft"]
            self.page.update()

    def _extract_related_id(self, related_item, relation: dict):
        if isinstance(related_item, dict):
            preferred_keys = [relation["payload_id_key"], *relation.get("payload_id_aliases", [])]
            normalized_keys = {key.lower() for key in preferred_keys}

            for key in preferred_keys:
                value = related_item.get(key)
                if value is not None:
                    try:
                        return int(value)
                    except (TypeError, ValueError):
                        pass

            for key in preferred_keys:
                nested_key = key[:-2] if key.endswith("Id") else key
                nested_value = related_item.get(nested_key)
                if isinstance(nested_value, dict) and nested_value.get("id") is not None:
                    return int(nested_value["id"])

            for key, candidate in related_item.items():
                normalized_key = key.lower()
                if normalized_key in normalized_keys and candidate is not None and not isinstance(candidate, (dict, list)):
                    try:
                        return int(candidate)
                    except (TypeError, ValueError):
                        pass
                if (
                    normalized_key.endswith("id")
                    and normalized_key != "id"
                    and candidate is not None
                    and not isinstance(candidate, (dict, list))
                ):
                    try:
                        return int(candidate)
                    except (TypeError, ValueError):
                        pass
            for value in related_item.values():
                if isinstance(value, dict) and value.get("id") is not None:
                    try:
                        return int(value["id"])
                    except (TypeError, ValueError):
                        pass
        return None

    def _extract_related_quantity(self, related_item, relation: dict | None = None):
        if isinstance(related_item, dict):
            quantity_keys = []
            if relation and relation.get("quantity_key"):
                quantity_keys.append(relation["quantity_key"])
            quantity_keys.extend(["cantidad", "cantidadRelacionada", "cantidad_relacionada"])

            normalized_keys = {key.lower() for key in quantity_keys}

            for key in quantity_keys:
                direct_value = related_item.get(key)
                if direct_value not in (None, ""):
                    return self._coerce_float(direct_value, 1.0)

            for key, value in related_item.items():
                if key.lower() in normalized_keys and value not in (None, "") and not isinstance(value, (dict, list)):
                    return self._coerce_float(value, 1.0)

            for value in related_item.values():
                if isinstance(value, dict):
                    for key in quantity_keys:
                        nested_quantity = value.get(key)
                        if nested_quantity not in (None, ""):
                            return self._coerce_float(nested_quantity, 1.0)
        return 1.0

    @staticmethod
    def _format_quantity_display(value):
        numeric = DashboardScreen._coerce_float(value, 0.0)
        if float(numeric).is_integer():
            return str(int(numeric))
        return f"{numeric:.4f}".rstrip("0").rstrip(".")

    def _extract_related_price(self, related_item, price_field: str):
        if not isinstance(related_item, dict):
            return 0.0
        direct_price = related_item.get(price_field)
        if direct_price not in (None, ""):
            return self._coerce_float(direct_price)
        for value in related_item.values():
            if isinstance(value, dict) and value.get(price_field) not in (None, ""):
                return self._coerce_float(value.get(price_field))
        return 0.0

    def _related_label_from_row(self, row: dict):
        for key in ("nombre", "descripcion", "email", "metodoPago"):
            value = row.get(key)
            if value:
                return str(value)
        return "Relacion"

    def _related_label_from_relation_item(self, related_item):
        if isinstance(related_item, dict):
            nested_values = [value for value in related_item.values() if isinstance(value, dict)]
            for nested in nested_values:
                label = self._related_label_from_row(nested)
                if label != "Relacion":
                    return label
            label = self._related_label_from_row(related_item)
            if label != "Relacion":
                return label
        return "Relacion"

    def _record_title(self, row: dict):
        for key in ("nombre", "descripcion", "email", "metodoPago", "estado"):
            value = row.get(key)
            if value:
                return str(value)
        return self.current_config.get("singular_title", "Registro")

    def _field_label(self, key: str):
        for field in self.current_config.get("fields", []):
            if field["key"] == key:
                return field["label"]
        return key.replace("_", " ").title()

    def _parse_iso_value(self, value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            timestamp = float(value)
            if abs(timestamp) < 10_000_000_000:
                timestamp *= 1000
            return datetime.fromtimestamp(timestamp / 1000, tz=datetime.now().astimezone().tzinfo)
        if isinstance(value, date):
            return datetime.combine(value, time.min, tzinfo=datetime.now().astimezone().tzinfo)
        if isinstance(value, str):
            normalized_text = value.strip()
            if normalized_text.isdigit():
                timestamp = float(normalized_text)
                if abs(timestamp) < 10_000_000_000:
                    timestamp *= 1000
                return datetime.fromtimestamp(timestamp / 1000, tz=datetime.now().astimezone().tzinfo)
            try:
                parsed_local_date = datetime.strptime(normalized_text, "%d/%m/%Y")
                return parsed_local_date.replace(tzinfo=datetime.now().astimezone().tzinfo)
            except ValueError:
                pass
            normalized = value.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(normalized)
            except ValueError:
                try:
                    parsed_date = date.fromisoformat(value[:10])
                    return datetime.combine(parsed_date, time.min, tzinfo=datetime.now().astimezone().tzinfo)
                except ValueError:
                    return None
        return None

    def _format_date_display(self, value, field: dict):
        if not value:
            return ""
        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, time.min)
        if field.get("include_time"):
            return value.strftime("%d/%m/%Y %H:%M")
        return value.strftime("%d/%m/%Y")

    def _serialize_date_value(self, value, field: dict):
        if not value:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, time.min, tzinfo=datetime.now().astimezone().tzinfo)
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.now().astimezone().tzinfo)
        value = value.replace(hour=0, minute=0, second=0, microsecond=0)
        return value.strftime("%d/%m/%Y")

    def _empty_state(self, text: str):
        return ft.Container(
            height=160,
            alignment=ft.Alignment(0, 0),
            content=ft.Text(text, color=COLORS["text_soft"], size=14, text_align=ft.TextAlign.CENTER),
        )

    def _show_payment_required_alert(self):
        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["bg_panel"],
            shape=ft.RoundedRectangleBorder(radius=18),
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=COLORS["warning"], size=28),
                    ft.Text("Pago pendiente", color=COLORS["text_main"], weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            content=ft.Text(
                "Esta falto de pago.",
                color=COLORS["text_soft"],
                size=14,
            ),
            actions=[
                ft.TextButton(
                    "Entendido",
                    style=ft.ButtonStyle(color=COLORS["warning"]),
                    on_click=lambda e: self._close_dialog(dlg),
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def _config_for(self, key: str):
        for entity in self.entities:
            if entity["key"] == key:
                return entity
        return None

    def _format_value(self, value):
        if value is None:
            return "-"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def _close_dialog(self, dlg):
        dlg.open = False
        self.page.update()

    @staticmethod
    def _icon_for(config: dict):
        icon_name = config.get("icon")
        return getattr(ft.Icons, icon_name, ft.Icons.DATA_ARRAY)
