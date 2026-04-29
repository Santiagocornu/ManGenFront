import flet as ft

from app.services.api_client import ApiError
from app.ui.theme import COLORS, button_style, input_style, panel


class LoginScreen:
    def __init__(self, page: ft.Page, on_login, on_register, on_change_password):
        self.page = page
        self.on_login = on_login
        self.on_register = on_register
        self.on_change_password = on_change_password
        self.current_section = "login"

        self.status_text = ft.Text("", size=12, color=COLORS["text_soft"])
        self.login_error_text = ft.Text("", color=COLORS["danger"], size=12)
        self.change_password_error_text = ft.Text("", color=COLORS["danger"], size=12)
        self.register_error_text = ft.Text("", color=COLORS["danger"], size=12)

        self.login_email_field = ft.TextField(
            label="Email",
            hint_text="usuario@mail.com",
            **input_style(),
        )
        self.login_password_field = ft.TextField(
            label="Contrase\u00f1a",
            password=True,
            can_reveal_password=True,
            **input_style(),
        )

        self.change_email_field = ft.TextField(
            label="Email",
            hint_text="usuario@mail.com",
            **input_style(),
        )
        self.change_password_field = ft.TextField(
            label="Contrase\u00f1a actual",
            password=True,
            can_reveal_password=True,
            **input_style(),
        )
        self.change_new_password_field = ft.TextField(
            label="Nueva contrase\u00f1a",
            password=True,
            can_reveal_password=True,
            **input_style(),
        )

        self.nombre_sucursal_field = ft.TextField(
            label="Nombre de sucursal",
            hint_text="Sucursal Centro",
            **input_style(),
        )
        self.nombre_admin_field = ft.TextField(
            label="Nombre del admin",
            hint_text="Juan Perez",
            **input_style(),
        )
        self.email_admin_field = ft.TextField(
            label="Email del admin",
            hint_text="admin@mail.com",
            **input_style(),
        )
        self.password_admin_field = ft.TextField(
            label="Contrase\u00f1a del administrador",
            password=True,
            can_reveal_password=True,
            **input_style(),
        )

        self.form_container = ft.Container(expand=True)

    def _clear_feedback(self):
        self.status_text.value = ""
        self.login_error_text.value = ""
        self.change_password_error_text.value = ""
        self.register_error_text.value = ""

    def _show_status(self, message: str, success: bool):
        self.status_text.value = message
        self.status_text.color = COLORS["success"] if success else COLORS["danger"]

    def _friendly_error(self, exc: Exception):
        message = str(exc).strip()
        if not message:
            return "Ocurrio un error inesperado. Intenta nuevamente."

        message = (
            message.replace("password", "contrase\u00f1a")
            .replace("Password", "Contrase\u00f1a")
            .replace("contrasena", "contrase\u00f1a")
        )

        if isinstance(exc, ApiError):
            return message

        return "Ocurrio un error inesperado. Intenta nuevamente."

    def set_section(self, section: str):
        self.current_section = section
        self._clear_feedback()
        self.form_container.content = self._build_section(section)
        self.page.update()

    def submit_login(self, _):
        self._clear_feedback()
        self.page.update()
        try:
            if not self.login_email_field.value.strip() or not self.login_password_field.value:
                raise ValueError("Completa el email y la contrase\u00f1a.")
            self.on_login(
                self.login_email_field.value.strip(),
                self.login_password_field.value,
            )
            self._show_status("Sesi\u00f3n iniciada correctamente.", True)
        except Exception as exc:
            self.login_error_text.value = self._friendly_error(exc)
        self.page.update()

    def submit_change_password(self, _):
        self._clear_feedback()
        self.page.update()
        try:
            if not self.change_email_field.value.strip():
                raise ValueError("Completa el email.")
            if not self.change_password_field.value:
                raise ValueError("Completa la contrase\u00f1a actual.")
            if not self.change_new_password_field.value:
                raise ValueError("Completa la nueva contrase\u00f1a.")

            self.on_change_password(
                self.change_email_field.value.strip(),
                self.change_password_field.value,
                self.change_new_password_field.value,
            )
            self.change_password_field.value = ""
            self.change_new_password_field.value = ""
            self._show_status("Contrase\u00f1a actualizada correctamente.", True)
        except Exception as exc:
            self.change_password_error_text.value = self._friendly_error(exc)
        self.page.update()

    def submit_register(self, _):
        self._clear_feedback()
        self.page.update()
        try:
            if not self.nombre_sucursal_field.value.strip():
                raise ValueError("Completa el nombre de la sucursal.")
            if not self.nombre_admin_field.value.strip():
                raise ValueError("Completa el nombre del admin.")
            if not self.email_admin_field.value.strip():
                raise ValueError("Completa el email del admin.")
            if not self.password_admin_field.value:
                raise ValueError("Completa la contrase\u00f1a del administrador.")

            self.on_register(
                self.nombre_sucursal_field.value.strip(),
                self.nombre_admin_field.value.strip(),
                self.email_admin_field.value.strip(),
                self.password_admin_field.value,
            )
            self.login_email_field.value = self.email_admin_field.value.strip()
            self.password_admin_field.value = ""
            self.set_section("login")
            self._show_status("Sucursal creada correctamente. Ahora puedes iniciar sesi\u00f3n.", True)
            self.page.update()
        except Exception as exc:
            self.register_error_text.value = self._friendly_error(exc)
            self.page.update()

    def build(self):
        self.form_container.content = self._build_section(self.current_section)
        content = ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[COLORS["bg_app"], COLORS["bg_panel"], COLORS["bg_deep"]],
            ),
            padding=24,
            content=ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        col={"sm": 12, "md": 10, "lg": 8, "xl": 6},
                        content=panel(
                            self._build_workspace(),
                            padding=28,
                        ),
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
        )

        return ft.View(
            route="/",
            padding=0,
            bgcolor=COLORS["bg_app"],
            controls=[content],
        )

    def _build_workspace(self):
        return ft.Container(
            content=ft.Column(
                [
                    self.status_text,
                    self.form_container,
                    ft.Divider(color=COLORS["border"], height=20),
                    self._build_navigation_row(),
            ],
            spacing=16,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
        )

    def _build_navigation_row(self):
        return ft.Row(
            controls=[
                self._nav_button("Iniciar sesi\u00f3n", "login", ft.Icons.LOGIN),
                self._nav_button("Cambiar contrase\u00f1a", "change_password", ft.Icons.LOCK_RESET),
                self._nav_button("Crear sucursal", "register", ft.Icons.STOREFRONT),
            ],
            wrap=True,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
            run_spacing=12,
        )

    def _build_section(self, section: str):
        builders = {
            "login": self._build_login_form,
            "register": self._build_register_form,
            "change_password": self._build_change_password_form,
            
        }
        return builders[section]()

    def _build_login_form(self):
        return ft.Column(
            [
                ft.Text("Iniciar sesi\u00f3n", size=28, weight=ft.FontWeight.BOLD, color=COLORS["text_main"]),
                ft.Text("Ingresa con email y contrase\u00f1a para operar sobre tu propia sucursal.", size=13, color=COLORS["text_soft"]),
                self.login_email_field,
                self.login_password_field,
                self.login_error_text,
                ft.ElevatedButton(
                    "Entrar",
                    icon=ft.Icons.LOGIN,
                    on_click=self.submit_login,
                    style=button_style("primary"),
                    height=46,
                ),
            ],
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_change_password_form(self):
        return ft.Column(
            [
                ft.Text("Cambiar contrase\u00f1a", size=28, weight=ft.FontWeight.BOLD, color=COLORS["text_main"]),
                ft.Text("Usa email, contrase\u00f1a actual y nueva contrase\u00f1a.", size=13, color=COLORS["text_soft"]),
                self.change_email_field,
                self.change_password_field,
                self.change_new_password_field,
                self.change_password_error_text,
                ft.ElevatedButton(
                    "Actualizar contrase\u00f1a",
                    icon=ft.Icons.SAVE,
                    on_click=self.submit_change_password,
                    style=button_style("accent"),
                    height=46,
                ),
            ],
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_register_form(self):
        return ft.Column(
            [
                ft.Text("Crear sucursal", size=28, weight=ft.FontWeight.BOLD, color=COLORS["text_main"]),
                ft.Text("Crea una nueva sucursal junto con su usuario ADMIN inicial.", size=13, color=COLORS["text_soft"]),
                self.nombre_sucursal_field,
                self.nombre_admin_field,
                self.email_admin_field,
                self.password_admin_field,
                self.register_error_text,
                ft.ElevatedButton(
                    "Crear sucursal",
                    icon=ft.Icons.STOREFRONT,
                    on_click=self.submit_register,
                    style=button_style("primary"),
                    height=46,
                ),
            ],
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _nav_button(self, label: str, section: str, icon):
        active = self.current_section == section
        kind = "primary" if active else "accent"
        return ft.ElevatedButton(
            label,
            icon=icon,
            on_click=lambda _: self.set_section(section),
            style=button_style(kind),
            height=48,
        )
