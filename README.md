# CE Consultores — Sistema de gestión de clientes y planes

Trabajo práctico grupal de **Análisis y Metodologías Ágiles**. Aplicación web hecha con **Python y Flask**, **sin base de datos**: todo se guarda en memoria mientras el servidor está prendido.

Se construye de a una funcionalidad por vez, a partir de las historias de usuario del backlog.

---

## Cómo ejecutarlo

Ejecutar Flask en la terminal de VSC con el comando flask --app  app --debug run

Abrir en el navegador: <http://127.0.0.1:5000>


## Usuarios de prueba

| Rol | Email | Contraseña |
|---|---|---|
| Cliente de ejemplo | `lucas@ejemplo.com` | `clave-segura-2` |
| Administrador | `benicio@ceconsultores.com` | `admin-desarrollo-1` |

Son datos de **desarrollo**. No usar contraseñas reales en ningún lugar del proyecto.

---

## Funcionalidades implementadas

| Historia | Qué hace | Quién |
|---|---|---|
| HU-01 / HU-01.2 | Registro de una persona y elección del plan inicial | Visitante |
| HU-02 | Validación automática de identidad en VeriCheck (simulado) | Sistema |
| HU-03 | Si VeriCheck rechaza los datos, se informa el motivo y no se crea la cuenta | Sistema |
| HU-07 | Si la identidad es válida, la cuenta queda habilitada y se muestra la bienvenida | Cliente |
| Login / logout | Ingreso con email y contraseña; salida por botón | Cliente y administrador |
| HU-04 | El cliente modifica su email y su teléfono (nombre y DNI no se editan) | Cliente |
| HU-08 | Catálogo de planes con descripción, costo mensual y SLA | Cliente y administrador |
| HU-11 | Alta de planes | Administrador |
| HU-12 | Modificación de un plan existente | Administrador |

**Pendientes:** HU-09 (ver mi plan vigente), HU-13 (baja de plan) y el flujo de solicitudes y cambios de plan (HU-14 en adelante).

---

## Datos: qué es dinámico y qué es fijo

### Dinámicos (se crean mientras la app funciona)

- Los **clientes** que se registran por el formulario.
- Los cambios de **email y teléfono** del perfil.
- Los **planes** que crea o edita el administrador.
- La **sesión** de quien está conectado.

### Fijos (están escritos en el código)

- **Lucas Salvarrey**: cliente de ejemplo que se carga al iniciar (`datos.py`).
- **3 planes iniciales**: Básico, Estándar y Premium. Nacen sin costo ni SLA y el administrador los completa.
- **Padrón de VeriCheck**: la lista de personas que pueden registrarse (`vericheck.py`).

### IMPORTANTE: los datos no se guardan

Todo vive en la memoria del proceso. **Al apagar o reiniciar Flask se pierde lo que se registró o editó.** Después de reiniciar solo quedan Lucas, los 3 planes y el admin. Incluye las modificaiones que haga el admin con cada plan, ya sea, valores, descripciones, etc.

---

## VeriCheck: quién puede registrarse

VeriCheck es un **simulador** de un servicio externo de validación de identidad. Solo acepta a estas personas, con **ese DNI y ese nombre** (no distingue tildes, mayúsculas ni el orden del nombre):

| DNI | Nombre |
|---|---|
| 45786322 | Lucas Salvarrey (ya cargado como cliente de ejemplo) |
| 28999111 | Galo Roselli |


Cualquier otro DNI es rechazado. Es lo esperado, porque así se prueba la historia HU-03.

**Para sumar más personas:** agregarlas a `PADRON_DEMO` en `vericheck.py`.

> No usar el DNI `12345678` en el padrón: los tests lo usan como ejemplo de DNI que no figura.

---

## Configuración (variables de entorno)

Todas son opcionales. Si no se definen, se usan los valores de desarrollo.

| Variable | Para qué sirve | Valor por defecto |
|---|---|---|
| `SECRET_KEY` | Firma las sesiones | `dev-solo-para-desarrollo` |
| `ADMIN_EMAIL` | Email del administrador | `benicio@ceconsultores.com` |
| `ADMIN_PASSWORD` | Contraseña del administrador | `admin-desarrollo-1` |
| `CARGAR_DATOS` | `0` para **no** cargar a Lucas al iniciar | `1` (se carga) |


---

## Estructura del proyecto

```
ce_consultores/
├── app.py                  Crea la app y registra los módulos
├── auth.py                 Login, logout y control de acceso por rol
├── store.py                Almacenamiento en memoria (clientes, admin, planes)
├── vericheck.py            Simulador de validación de identidad
├── datos.py                Datos de ejemplo que se cargan al iniciar
├── requirements.txt        Dependencias
│
├── clientes/               Registro y perfil del cliente
│   ├── __init__.py         Crea el blueprint
│   ├── validaciones.py     Qué se acepta en los formularios
│   └── rutas.py            Las pantallas
│
├── planes/                 Catálogo de planes
│   ├── __init__.py         Crea el blueprint y registra el filtro "pesos"
│   ├── formatos.py         Formato de los montos ($ 12.500,50)
│   ├── validaciones.py     Reglas del formulario de un plan
│   └── rutas.py            Catálogo, alta y edición
│
├── templates/              Páginas HTML (Jinja2)
│   ├── base.html           Estructura común y menú según el rol
│   ├── registro.html   login.html   mi_cuenta.html   editar_perfil.html
│   └── catalogo.html   plan_form.html
│
└── tests/                  Pruebas automáticas (unittest)
    ├── ayudas.py           Bases y atajos compartidos
    ├── test_registro.py    test_identidad.py    test_datos_demo.py
    ├── test_login.py       test_perfil.py
    └── test_catalogo.py    test_plan_alta.py    test_plan_edicion.py    test_planes_login.py
```

**Regla de la estructura:** en cada carpeta, `validaciones.py` decide *qué se acepta*, y `rutas.py` decide *qué pasa* cuando alguien entra a una URL. Las validaciones no saben nada de Flask.

---


- **Escribir tests** para lo nuevo, en `tests/`, siguiendo el estilo de los que ya existen.
- **Respetar la estructura**: validaciones en `validaciones.py`, pantallas en `rutas.py`, textos HTML en `templates/`.

### No

- **No subir al repositorio** las carpetas `venv/` ni `__pycache__/`.
- **No subir contraseñas ni claves reales.** Las de este proyecto son de prueba.
- **No cambiar un test para que pase** sin entender por qué fallaba.
- **No hacer cerrar sesión con un link.** Se hace con un botón (`POST`), porque `GET /logout` devuelve error 405.

---

## Limitaciones conocidas

- **Sin persistencia**: los datos se pierden al reiniciar.
- **Sin protección CSRF** en los formularios.
- **Sin límite de intentos** en el login.
- **Un solo administrador**, definido por configuración.
- **Los "servicios"** del contexto del TP no están modelados: por ahora solo existen los planes.
- **VeriCheck es un simulador** con un padrón fijo de prueba.

Son decisiones de alcance para el TP. Si el equipo las cambia, conviene anotarlo acá.

