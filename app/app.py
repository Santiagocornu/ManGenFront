import flet as ft

from app.config.entities import ENTITY_CONFIGS
from app.screens.dashboard import DashboardScreen
from app.screens.login_screen import LoginScreen
from app.services.api_client import ApiClient, ApiError
from app.ui.theme import COLORS


class ManagerPeneApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.api = ApiClient()
        self.user = None
        self.entities = []

        self.page.title = "ManagerPene"
        self.page.bgcolor = COLORS["bg_app"]
        self.page.padding = 0
        self.page.spacing = 0
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window_min_width = 360
        self.page.window_min_height = 640
        self.page.scroll = ft.ScrollMode.HIDDEN
        self.page.on_route_change = self._handle_route_change

    async def initialize(self):
        self._render_current_route(self.page.route or "/")

    def login(self, email: str, password: str):
        data = self.api.login(email=email, password=password)
        self.user = self._extract_user(data, email)
        self.entities = self._available_entities(self.user)
        if not self.entities:
            raise ApiError("No hay modulos disponibles para este usuario.")
        self.page.go(f"/{self.entities[0]['key']}")
        return data

    def register_sucursal_admin(
        self,
        nombre_sucursal: str,
        nombre_admin: str,
        email_admin: str,
        password_admin: str,
    ):
        return self.api.register_sucursal_admin(
            nombre_sucursal=nombre_sucursal,
            nombre_admin=nombre_admin,
            email_admin=email_admin,
            password_admin=password_admin,
        )

    def change_password(
        self,
        email: str,
        password: str,
        new_password: str,
    ):
        return self.api.change_password(
            email=email,
            password=password,
            new_password=new_password,
        )

    def logout(self, _=None):
        self.api.clear_token()
        self.user = None
        self.entities = []
        self.page.go("/")

    def _handle_route_change(self, route):
        self._render_current_route(route.route)

    def _render_current_route(self, route: str):
        self.page.views.clear()

        if route == "/" or not self.user:
            self.page.views.append(self._build_login_view())
        else:
            if not self.entities:
                self.entities = self._available_entities(self.user)
            dashboard = DashboardScreen(
                page=self.page,
                api=self.api,
                user=self.user,
                entities=self.entities,
                on_logout=self.logout,
            )
            self.page.views.append(dashboard.build(route))

        self.page.update()

    def _build_login_view(self):
        screen = LoginScreen(
            page=self.page,
            on_login=self.login,
            on_register=self.register_sucursal_admin,
            on_change_password=self.change_password,
        )
        return screen.build()

    @staticmethod
    def _extract_user(data, email: str):
        if isinstance(data, dict):
            for key in ("user", "usuario", "admin", "data"):
                value = data.get(key)
                if isinstance(value, dict):
                    return value
            user = dict(data)
            user.setdefault("email", email)
            return user
        return {"email": email}

    @staticmethod
    def _available_entities(user: dict):
        role = str(user.get("roll", user.get("rol", ""))).upper()
        is_admin = role == "ADMIN"
        return [entity for entity in ENTITY_CONFIGS if is_admin or not entity.get("admin_only")]


async def main(page: ft.Page):
    try:
        app = ManagerPeneApp(page)
        await app.initialize()
    except ApiError as exc:
        page.add(ft.Text(f"Error inicializando la app: {exc}"))


def run():
    ft.run(main)
