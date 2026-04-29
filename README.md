 ManGen Desktop App

Aplicación de escritorio para gestión integral de stock, ventas y operaciones comerciales, basada en la API GenMan.

 Descripción general

La aplicación permite administrar:

Materias primas
Productos
Pedidos
Ventas
Usuarios
Sucursales

Trabaja sobre un modelo multi-sucursal, donde cada usuario solo puede operar sobre los datos de su propia sucursal.

Toda la lógica de negocio y persistencia se delega a la API REST (incluida en este proyecto), utilizando autenticación JWT.

 Sistema de autenticación

La aplicación cuenta con tres flujos principales:

1. Inicio de sesión
Email + contraseña
Consume:
POST /auth/login
Guarda el JWT para futuras requests
2. Cambio de contraseña
Requiere:
Email
Contraseña actual
Nueva contraseña
Consume:
POST /auth/change-password?email=...&password=...&newPassword=...
3. Creación de sucursal (registro inicial)
Permite crear:
Una nueva sucursal
Un usuario ADMIN asociado
Consume:
POST /auth/register-sucursal-admin

Body:

{
  "nombreSucursal": "Empresa",
  "nombreAdmin": "Admin",
  "emailAdmin": "admin@mail.com",
  "passwordAdmin": "1234"
}
 Roles y permisos
ADMIN

Puede:

Gestionar usuarios
Gestionar sucursales
Acceder a todas las entidades
Crear y administrar datos de su sucursal
USER

Puede:

Gestionar entidades operativas (productos, ventas, etc.)
No puede ver usuarios ni sucursales
Modelo de datos (según MER)

Relaciones principales:

Producto ↔ Materia Prima (con cantidad)
Pedido ↔ Producto (con cantidad)
Venta ↔ Producto (con cantidad)
Usuario → Sucursal
Todas las entidades pertenecen a una sucursal
Panel principal

Luego del login, el usuario accede a un dashboard con:

Acceso a entidades según rol
Navegación modular por cada entidad
Acciones CRUD completas
 Gestión de entidades

Cada entidad tiene:

 Crear

Formulario con:

Atributos propios
Relaciones (según MER)
Cantidades en relaciones
 Visualización

Cada registro muestra:

Sus atributos
Sus relaciones solo en un sentido:

Ejemplos:

Producto → muestra materias primas
Materia prima → ❌ no muestra productos
Pedido → muestra productos
Producto → ❌ no muestra pedidos
Venta → muestra productos
Editar

Permite:

Modificar atributos
Modificar relaciones
Ajustar cantidades asociadas
❌ Eliminar
Eliminación directa del registro
Filtros

Todas las entidades permiten filtrar por:

Nombre
Fecha
Estado
Otros atributos relevantes

⚠️ No se muestran IDs en ningún caso.

 Lógica de ventas y stock
Venta desde cero
Se crean productos asociados manualmente
Opción:
✔ afectar stock
❌ no afectar stock

Si afecta stock:

Se descuenta:
Stock del producto
Stock de materias primas asociadas
Venta desde pedido

Endpoints:

POST /apiManGen/Ventas/desde-pedido/{id}
POST /apiManGen/Ventas/desde-pedido/{id}/con-stock

Comportamiento:

Marca el pedido como Terminado
Puede opcionalmente afectar stock
 Importante
Pedidos NO afectan stock
Solo las ventas pueden modificar stock
 Integración con API

Base URL:

http://localhost:8080/apiManGen

Autenticación:

Authorization: Bearer <token>

Todas las operaciones del frontend consumen endpoints definidos en la API incluida.

 Arquitectura esperada del cliente
Cliente desacoplado de backend
Manejo de estado con JWT
Separación por módulos (entidades)
Formularios dinámicos para relaciones

 Objetivo

Proveer una solución escalable para negocios que necesiten:

Control de stock automatizado
Gestión de ventas y pedidos
Multi-sucursal con aislamiento de datos
Control de usuarios y permisos