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
        self.table_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self.feedback = ft.Text("", color=COLORS["text_soft"], size=12)

    def build(self, route: str):
        parts = [part for part in route.split("/") if part]
        requested_key = parts[0] if parts else self.entities[0]["key"]
        self.current_config = self._config_for(requested_key) or self.entities[0]
        self.current_key = self.current_config["key"]
        self._refresh_table()

        shell = ft.Container(
            expand=True,
            bgcolor=COLORS["bg_app"],
            content=ft.Row(
                [
                    self._sidebar(),
                    ft.Container(
                        expand=True,
                        padding=24,
                        content=ft.Column(
                            [
                                self._header(),
                                self.feedback,
                                self.table_column,
                            ],
                            expand=True,
                            spacing=18,
                        ),
                    ),
                ],
                expand=True,
                spacing=0,
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
                    border_radius=12,
                    bgcolor=COLORS["accent_soft"] if active else "transparent",
                    padding=ft.padding.symmetric(horizontal=14, vertical=12),
                    ink=True,
                    on_click=lambda e, key=entity["key"]: self.page.go(f"/{key}"),
                    content=ft.Row(
                        [
                            ft.Icon(
                                self._icon_for(entity["key"]),
                                color=COLORS["text_main"] if active else COLORS["text_soft"],
                                size=18,
                            ),
                            ft.Text(
                                entity["title"],
                                color=COLORS["text_main"] if active else COLORS["text_soft"],
                                size=14,
                                weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400,
                            ),
                        ],
                        spacing=10,
                    ),
                )
            )

        return ft.Container(
            width=260,
            padding=24,
            bgcolor=COLORS["bg_panel"],
            border=ft.border.only(right=ft.BorderSide(1, COLORS["border"])),
            content=ft.Column(
                [
                    ft.Text("ManagerPene", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text_main"]),
                    ft.Text("GenMan API client", size=12, color=COLORS["text_soft"]),
                    ft.Container(height=12),
                    ft.Container(
                        padding=16,
                        border_radius=14,
                        bgcolor=COLORS["glass"],
                        border=ft.border.all(1, COLORS["border"]),
                        content=ft.Column(
                            [
                                ft.Text(self.user.get("nombre", "-"), color=COLORS["text_main"], size=16, weight=ft.FontWeight.W_600),
                                ft.Text(self.user.get("email", "-"), color=COLORS["text_soft"], size=12),
                                ft.Text(
                                    f"{self.user.get('roll', '-')}",
                                    color=COLORS["text_muted"],
                                    size=11,
                                ),
                            ],
                            spacing=4,
                        ),
                    ),
                    ft.Container(height=12),
                    ft.Column(items, spacing=8, expand=True, scroll=ft.ScrollMode.AUTO),
                    ft.OutlinedButton(
                        "Cerrar sesion",
                        icon=ft.Icons.LOGOUT,
                        on_click=self.on_logout,
                        style=ft.ButtonStyle(
                            color=COLORS["text_soft"],
                            side=ft.BorderSide(1, COLORS["border"]),
                            shape=ft.RoundedRectangleBorder(radius=12),
                        ),
                        height=42,
                    ),
                ],
                expand=True,
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
                height=42,
            ),
            ft.OutlinedButton(
                "Recargar",
                icon=ft.Icons.REFRESH,
                on_click=lambda e: self._refresh_table(),
                style=ft.ButtonStyle(
                    color=COLORS["text_soft"],
                    side=ft.BorderSide(1, COLORS["border"]),
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),
                height=42,
            ),
        ]

        for action in config.get("extra_actions", []):
            if action == "from_pedido":
                actions.append(
                    ft.ElevatedButton(
                        "Venta desde pedido",
                        icon=ft.Icons.POINT_OF_SALE,
                        on_click=lambda e: self._open_pedido_to_venta(False),
                        style=button_style("accent"),
                        height=42,
                    )
                )
            if action == "from_pedido_stock":
                actions.append(
                    ft.ElevatedButton(
                        "Venta desde pedido con stock",
                        icon=ft.Icons.INVENTORY_2,
                        on_click=lambda e: self._open_pedido_to_venta(True),
                        style=button_style("success"),
                        height=42,
                    )
                )

        return ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(config["title"], size=30, weight=ft.FontWeight.BOLD, color=COLORS["text_main"]),
                        ft.Text(
                            f"Base URL: {self.api.base_url}",
                            size=12,
                            color=COLORS["text_soft"],
                        ),
                    ],
                    spacing=2,
                ),
                ft.Row(actions, spacing=10, wrap=True),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def _refresh_table(self):
        try:
            rows = self.api.get(self.current_config["endpoint"]) or []
        except ApiError as exc:
            self.feedback.value = str(exc)
            self.feedback.color = COLORS["danger"]
            self.table_column.controls = [self._empty_state("No se pudo cargar la entidad.")]
            self.page.update()
            return

        if not isinstance(rows, list):
            rows = [rows]

        self.feedback.value = f"{len(rows)} registro(s) cargados"
        self.feedback.color = COLORS["text_soft"]

        self.table_column.controls = [
            panel(
                ft.Column(
                    [
                        self._stats_strip(rows),
                        self._build_table(rows),
                    ],
                    spacing=16,
                ),
                expand=True,
            )
        ]
        self.page.update()

    def _stats_strip(self, rows: list[dict]):
        first = rows[0] if rows else {}
        summary_keys = self.current_config["table_columns"][:3]
        cards = [self._stat_card("Registros", str(len(rows)))]
        for key in summary_keys:
            cards.append(self._stat_card(key, str(first.get(key, "-")) if first else "-"))
        return ft.ResponsiveRow(cards)

    def _stat_card(self, label: str, value: str):
        return ft.Container(
            col={"sm": 12, "md": 3},
            padding=14,
            border_radius=14,
            bgcolor=COLORS["bg_panel"],
            border=ft.border.all(1, COLORS["border"]),
            content=ft.Column(
                [
                    ft.Text(label, color=COLORS["text_soft"], size=11),
                    ft.Text(value, color=COLORS["text_main"], size=16, weight=ft.FontWeight.W_600),
                ],
                spacing=6,
            ),
        )

    def _build_table(self, rows: list[dict]):
        if not rows:
            return self._empty_state("Todavia no hay registros para este modulo.")

        columns = self.current_config["table_columns"]
        header_cells = [ft.DataColumn(ft.Text(col, color=COLORS["text_main"])) for col in columns]
        header_cells.append(ft.DataColumn(ft.Text("Acciones", color=COLORS["text_main"])))

        data_rows = []
        for row in rows:
            cells = [
                ft.DataCell(
                    ft.Text(
                        self._format_value(row.get(column)),
                        color=COLORS["text_main"],
                        size=12,
                    )
                )
                for column in columns
            ]
            cells.append(ft.DataCell(self._row_actions(row)))
            data_rows.append(ft.DataRow(cells=cells))

        return ft.DataTable(
            columns=header_cells,
            rows=data_rows,
            border=ft.border.all(1, COLORS["border"]),
            border_radius=12,
            heading_row_color=COLORS["accent_soft"],
            data_row_color={"hovered": COLORS["row_hover"]},
            column_spacing=24,
        )

    def _row_actions(self, row: dict):
        controls = [
            ft.IconButton(
                icon=ft.Icons.EDIT,
                icon_color=COLORS["warning"],
                tooltip="Editar",
                on_click=lambda e, item=row: self._open_form(item),
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=COLORS["danger"],
                tooltip="Eliminar",
                on_click=lambda e, item=row: self._confirm_delete(item),
            ),
        ]

        if "backfill" in self.current_config.get("extra_actions", []):
            controls.append(
                ft.IconButton(
                    icon=ft.Icons.PUBLISHED_WITH_CHANGES,
                    icon_color=COLORS["success"],
                    tooltip="Backfill",
                    on_click=lambda e, item=row: self._run_backfill(item),
                )
            )

        return ft.Row(controls, spacing=0, wrap=True)

    def _open_form(self, item: dict | None = None):
        is_edit = item is not None
        title = f"{'Editar' if is_edit else 'Nuevo'} {self.current_config['title']}"
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
                        "Selecciona los elementos relacionados y su cantidad desde este formulario.",
                        color=COLORS["text_soft"],
                        size=12,
                    ),
                    relation_state["view"],
                ]
            )

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
            except ApiError as exc:
                form_error.value = str(exc)
                self.page.update()

        form_error = ft.Text("", size=12, color=COLORS["danger"])
        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["bg_panel"],
            title=ft.Text(title, color=COLORS["text_main"]),
            content=ft.Container(
                width=520,
                content=ft.Column(
                    controls + [form_error],
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                    height=460,
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close_dialog(dlg)),
                ft.ElevatedButton("Guardar", on_click=submit, style=button_style("primary")),
            ],
        )
        self.page.show_dialog(dlg)

    def _confirm_delete(self, item: dict):
        message = ft.Text(
            "Se eliminara este registro.",
            color=COLORS["text_soft"],
        )

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
            content=message,
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

    def _open_pedido_to_venta(self, with_stock: bool):
        pedido_id = ft.TextField(label="Pedido", **input_style())
        error = ft.Text("", size=12, color=COLORS["danger"])

        def submit(_):
            try:
                path = f"/apiManGen/Ventas/desde-pedido/{int(pedido_id.value)}"
                if with_stock:
                    path += "/con-stock"
                self.api.post(path)
                self.feedback.value = "Venta creada desde pedido."
                self.feedback.color = COLORS["success"]
                dlg.open = False
                self._refresh_table()
            except Exception as exc:
                error.value = str(exc)
                self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["bg_panel"],
            title=ft.Text("Generar venta desde pedido", color=COLORS["text_main"]),
            content=ft.Container(
                width=420,
                content=ft.Column([pedido_id, error], tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close_dialog(dlg)),
                ft.ElevatedButton("Crear", on_click=submit, style=button_style("primary")),
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
                value = float(value)
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

        state = {"selected": selected, "picker": picker}

        def open_picker(_):
            self.page.show_dialog(picker)

        open_button = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH,
            icon_color=COLORS["accent"],
            tooltip="Seleccionar fecha",
            on_click=open_picker,
            disabled=field.get("auto_now_local_on_create") and not is_edit,
        )
        helper_text = None
        if field.get("auto_now_local_on_create") and not is_edit:
            helper_text = ft.Text(
                "Se asigna automaticamente con la fecha y hora local.",
                size=11,
                color=COLORS["text_soft"],
            )

        view = ft.Column(
            [
                ft.Row([ft.Container(content=text_field, expand=True), open_button], vertical_alignment=ft.CrossAxisAlignment.END),
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
            option_map[str(related_id)] = self._related_label_from_row(related)

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
                quantity = float(quantity_field.value)
                if quantity <= 0:
                    raise ApiError("La cantidad debe ser mayor a cero.")

                related_id = int(dropdown.value)
                label = option_map.get(dropdown.value, "Relacion")

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
                    selected_items[related_id] = {"label": label, "cantidad": quantity}

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
            label = option_map.get(str(related_id)) or self._related_label_from_relation_item(related_item)
            quantity = self._extract_related_quantity(related_item)
            state["selected_items"][related_id] = {"label": label, "cantidad": quantity}

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

    def _extract_related_id(self, related_item, payload_id_key: str):
        if isinstance(related_item, dict):
            value = related_item.get(payload_id_key)
            if value is not None:
                return int(value)
            nested_key = payload_id_key[:-2] if payload_id_key.endswith("Id") else payload_id_key
            nested_value = related_item.get(nested_key)
            if isinstance(nested_value, dict) and nested_value.get("id") is not None:
                return int(nested_value["id"])
            if related_item.get("id") is not None and len(related_item.keys()) <= 3:
                return int(related_item["id"])
        return None

    def _extract_related_quantity(self, related_item):
        if isinstance(related_item, dict):
            value = related_item.get("cantidad", 1)
            try:
                return float(value)
            except (TypeError, ValueError):
                return 1.0
        return 1.0

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
        if field.get("auto_now_local_on_create"):
            return value.isoformat(timespec="milliseconds")
        if field.get("include_time"):
            return value.isoformat(timespec="milliseconds")
        return value.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="milliseconds")

    def _empty_state(self, text: str):
        return ft.Container(
            height=160,
            alignment=ft.Alignment(0, 0),
            content=ft.Text(text, color=COLORS["text_soft"], size=14),
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

    def _close_dialog(self, dlg: ft.AlertDialog):
        dlg.open = False
        self.page.update()

    @staticmethod
    def _icon_for(key: str):
        mapping = {
            "sucursales": ft.Icons.STOREFRONT,
            "usuarios": ft.Icons.GROUPS,
            "materias_primas": ft.Icons.SCIENCE,
            "productos": ft.Icons.INVENTORY_2,
            "pedidos": ft.Icons.RECEIPT_LONG,
            "ventas": ft.Icons.POINT_OF_SALE,
        }
        return mapping.get(key, ft.Icons.DATA_ARRAY)
