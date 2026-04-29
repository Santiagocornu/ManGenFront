import flet as ft
from datetime import date, datetime, time

from app.services.api_client import ApiError
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
                    padding=ft.padding.symmetric(horizontal=14, vertical=12),
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

        return ft.Container(
            expand=True,
            bgcolor=COLORS["bg_panel"],
            border=ft.border.only(right=ft.BorderSide(1, COLORS["border"])),
            padding=24,
            content=ft.Column(
                [
                    ft.Text("ManagerPene", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text_main"]),
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
        ]

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

        return panel(
            ft.ResponsiveRow(
                [
                    ft.Container(
                        col={"sm": 12, "lg": 6},
                        content=ft.Column(
                            [
                                ft.Text(config["title"], size=30, weight=ft.FontWeight.BOLD, color=COLORS["text_main"]),
                                ft.Text(config.get("tagline", ""), size=13, color=COLORS["text_soft"]),
                                ft.Text(
                                    f"API: {self.api.base_url}",
                                    size=11,
                                    color=COLORS["text_muted"],
                                ),
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

    def _refresh_table(self):
        try:
            rows = self.api.get(self.current_config["endpoint"]) or []
        except ApiError as exc:
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
        summary_fields = self.current_config.get("summary_fields") or self.current_config["table_columns"][:3]
        first = rows[0] if rows else {}
        cards = [self._stat_card("Registros", str(len(rows)), COLORS["accent"])]
        for key in summary_fields[:3]:
            cards.append(self._stat_card(self._field_label(key), self._format_value(first.get(key)) if first else "-", COLORS["primary"]))
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
        expected_keys = [filter_config["key"] for filter_config in self.current_config.get("filters", [])]
        if list(self.filter_inputs.keys()) == expected_keys:
            return

        inputs = {}
        for filter_config in self.current_config.get("filters", []):
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
                    padding=ft.padding.symmetric(vertical=6),
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

        relation_block = self._build_relation_preview(row) if self.current_config.get("relation") else None

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
                    *( [relation_block] if relation_block else [] ),
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
        return controls

    def _build_relation_preview(self, row: dict):
        relation = self.current_config["relation"]
        relation_items = []
        error_text = ft.Text("", color=COLORS["danger"], size=11)

        try:
            relation_items = self.api.get(relation["list_path"].format(id=row["id"])) or []
        except ApiError as exc:
            error_text.value = str(exc)

        content = []
        if relation_items:
            for relation_item in relation_items[:4]:
                content.append(
                    ft.Container(
                        padding=10,
                        border_radius=12,
                        bgcolor=COLORS["bg_app"],
                        border=ft.border.all(1, COLORS["border"]),
                        content=ft.Row(
                            [
                                ft.Text(self._related_label_from_relation_item(relation_item), color=COLORS["text_main"], size=12, expand=True),
                                ft.Text(
                                    f"x {self._extract_related_quantity(relation_item):.2f}",
                                    color=COLORS["accent"],
                                    size=11,
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    )
                )
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

        relation_state = None
        if self.current_config.get("relation"):
            relation_state = self._build_inline_relation_state(self.current_config["relation"], item)
            controls.extend(
                [
                    ft.Divider(color=COLORS["border"]),
                    ft.Text("Relaciones", color=COLORS["text_main"], size=18, weight=ft.FontWeight.W_600),
                    ft.Text(
                        "Las relaciones se gestionan desde la entidad principal, como pide el flujo del proyecto.",
                        color=COLORS["text_soft"],
                        size=12,
                    ),
                    relation_state["view"],
                ]
            )

        self._configure_totals(inputs, relation_state, item)

        form_error = ft.Text("", size=12, color=COLORS["danger"])

        def submit(_):
            try:
                payload = self._build_payload(inputs, is_edit)
                if is_edit:
                    self.api.put(f"{self.current_config['endpoint']}/{item['id']}", payload)
                    self.feedback.value = "Registro actualizado correctamente."
                else:
                    created = self.api.post(self.current_config["endpoint"], payload)
                    self._persist_inline_relations(created, relation_state)
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
            options=[ft.dropdown.Option(key=key, text=label) for key, label in option_map.items()],
            **input_style(as_dropdown=True),
        )
        quantity_field = ft.TextField(
            label="Cantidad",
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            **input_style(),
        )
        use_stock = ft.Switch(
            label="Ajustar stock",
            value=False,
            active_color=COLORS["success"],
            visible="create_path_stock" in relation,
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
                quantity_field.value = "1"
            else:
                current = selected_items[related_id]
                dropdown.value = str(related_id)
                quantity_field.value = str(current["cantidad"])
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
                                            ft.Text(
                                                f"Cantidad: {related_item['cantidad']:.2f}",
                                                color=COLORS["text_soft"],
                                                size=11,
                                            ),
                                            ft.Text(
                                                f"Unitario: {self._format_value(related_item.get('unit_price'))}",
                                                color=COLORS["text_muted"],
                                                size=11,
                                            ),
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
                    delete_path = relation.get("delete_path_stock") if use_stock.value else relation.get("delete_path")
                    if not delete_path:
                        raise ApiError("No se puede eliminar esta relacion desde la interfaz.")
                    self.api.delete(delete_path.format(id=item["id"], related_id=related_id))
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
                quantity = self._parse_number(quantity_field.value, "Cantidad")
                if quantity <= 0:
                    raise ApiError("La cantidad debe ser mayor a cero.")

                related_id = int(dropdown.value)
                option = option_map.get(dropdown.value, {"label": "Relacion", "price": 0.0})
                label = option["label"]

                if item is not None:
                    self._save_existing_relation(
                        relation=relation,
                        item=item,
                        related_id=related_id,
                        quantity=quantity,
                        use_stock=use_stock.value,
                        already_exists=related_id in selected_items,
                    )
                    self._load_existing_relations(state, option_map)
                else:
                    selected_items[related_id] = {
                        "label": label,
                        "cantidad": quantity,
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
                        ft.Container(quantity_field, col={"sm": 12, "md": 3}),
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

    def _persist_inline_relations(self, created, relation_state):
        if not relation_state or not relation_state["selected_items"]:
            return
        if not isinstance(created, dict) or created.get("id") is None:
            raise ApiError("La API no devolvio el identificador del registro creado para guardar las relaciones.")
        relation = relation_state["relation"]
        created_id = created["id"]
        path_key = "create_path_stock" if relation_state["use_stock"].value and relation.get("create_path_stock") else "create_path"
        path_template = relation[path_key]

        for related_id, item in relation_state["selected_items"].items():
            payload = {
                relation["payload_id_key"]: related_id,
                "cantidad": item["cantidad"],
            }
            self.api.post(path_template.format(id=created_id), payload)

    def _load_existing_relations(self, state: dict, option_map: dict[str, str]):
        relation = state["relation"]
        item = state["item"]
        related_items = self.api.get(relation["list_path"].format(id=item["id"])) or []
        state["selected_items"].clear()
        for related_item in related_items:
            related_id = self._extract_related_id(related_item, relation["payload_id_key"])
            if related_id is None:
                continue
            option = option_map.get(str(related_id), {})
            label = option.get("label") or self._related_label_from_relation_item(related_item)
            quantity = self._extract_related_quantity(related_item)
            unit_price = option.get("price")
            if unit_price in (None, 0.0):
                unit_price = self._extract_related_price(related_item, relation.get("price_field", "precio"))
            state["selected_items"][related_id] = {
                "label": label,
                "cantidad": quantity,
                "unit_price": unit_price,
            }

    def _save_existing_relation(self, relation: dict, item: dict, related_id: int, quantity: float, use_stock: bool, already_exists: bool):
        if already_exists:
            update_path = relation.get("update_path_stock") if use_stock else relation["update_path"]
            self.api.patch(
                update_path.format(id=item["id"], related_id=related_id),
                {"cantidad": quantity},
            )
            return

        payload = {
            relation["payload_id_key"]: related_id,
            "cantidad": quantity,
        }
        create_path = relation.get("create_path_stock") if use_stock else relation["create_path"]
        self.api.post(create_path.format(id=item["id"]), payload)

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
            relation_state["on_change"] = lambda: apply_totals(False)

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
            quantity = self._coerce_float(related_item.get("cantidad"))
            unit_price = self._coerce_float(related_item.get("unit_price"))
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

    def _apply_filters(self, rows: list[dict]):
        filtered = rows
        for key, entry in self.filter_inputs.items():
            raw_value = entry["control"].value
            if raw_value in (None, ""):
                continue
            value = str(raw_value).strip().lower()
            filter_type = entry["config"]["type"]
            if filter_type == "date":
                filtered = [row for row in filtered if value in self._format_value(row.get(key)).lower()]
            else:
                filtered = [row for row in filtered if value in str(row.get(key, "")).lower()]
        return filtered

    def _clear_filters(self):
        for entry in self.filter_inputs.values():
            entry["control"].value = None if isinstance(entry["control"], ft.Dropdown) else ""
        self._render_rows()

    def _extract_related_id(self, related_item, payload_id_key: str):
        if isinstance(related_item, dict):
            value = related_item.get(payload_id_key)
            if value is not None:
                return int(value)
            for key, candidate in related_item.items():
                if key.lower().endswith("id") and candidate is not None and not isinstance(candidate, (dict, list)):
                    try:
                        return int(candidate)
                    except (TypeError, ValueError):
                        pass
            nested_key = payload_id_key[:-2] if payload_id_key.endswith("Id") else payload_id_key
            nested_value = related_item.get(nested_key)
            if isinstance(nested_value, dict) and nested_value.get("id") is not None:
                return int(nested_value["id"])
            for value in related_item.values():
                if isinstance(value, dict) and value.get("id") is not None:
                    try:
                        return int(value["id"])
                    except (TypeError, ValueError):
                        pass
            if related_item.get("id") is not None and len(related_item.keys()) <= 3:
                return int(related_item["id"])
        return None

    def _extract_related_quantity(self, related_item):
        if isinstance(related_item, dict):
            value = related_item.get("cantidad", 1)
            return self._coerce_float(value, 1.0)
        return 1.0

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
        if isinstance(value, date):
            return datetime.combine(value, time.min, tzinfo=datetime.now().astimezone().tzinfo)
        if isinstance(value, str):
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
        if not field.get("auto_now_local_on_create") and not field.get("include_time"):
            value = value.replace(hour=0, minute=0, second=0, microsecond=0)
        offset = value.strftime("%z")
        java_offset = f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"
        return f"{value.strftime('%Y-%m-%dT%H:%M:%S')}.{int(value.microsecond / 1000):03d}{java_offset}"

    def _empty_state(self, text: str):
        return ft.Container(
            height=160,
            alignment=ft.Alignment(0, 0),
            content=ft.Text(text, color=COLORS["text_soft"], size=14, text_align=ft.TextAlign.CENTER),
        )

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
