# CE Consultores — Sistema de gestión de clientes y planes

Trabajo práctico grupal de **Análisis y Metodologías Ágiles**. Aplicación web hecha con **Python y Flask**, **sin base de datos**: todo se guarda en memoria mientras el servidor está prendido.

Se construye de a una funcionalidad por vez, a partir de las historias de usuario del backlog.

---

## Cómo ejecutarlo

Desde la carpeta del proyecto, instalar las dependencias y ejecutar Flask:

```powershell
python -m pip install -r requirements.txt
python -m flask --app app --debug run
```

Abrir en el navegador: <http://127.0.0.1:5000>


## Usuarios de prueba

| Rol | Email | Contraseña |
|---|---|---|
| Cliente de ejemplo | `lucas@ejemplo.com` | `clave-segura-2` |
| Administrador | `benicio@ceconsultores.com` | `admin-desarrollo-1` |

Son datos de **desarrollo**. No usar contraseñas reales en ningún lugar del proyecto.

---

## Guion de prueba (paso a paso)

Recorrido para probar la demo completa. Se hace con el servidor recién iniciado, porque los datos de ejemplo se cargan al arrancar.

**Como cliente**

1. Entrar a <http://127.0.0.1:5000/login> con `lucas@ejemplo.com` / `clave-segura-2`.
2. En **Mi cuenta** se ve el **Plan Básico**, con su descripción, costo mensual y SLA.
3. Ir a **Solicitudes** (menú). Ya hay una solicitud de ejemplo (#1, al Plan Estándar) en estado **Pendiente**.
4. Tocar **Nueva solicitud**, elegir el **Plan Premium**, escribir un detalle y enviar. Aparece como **Pendiente** (#2) y llega un aviso de NotiSys. El Premium no tiene costo definido a propósito, para el paso 9.
5. Crear otra solicitud (al Plan Estándar) y tocar **Anular solicitud**: pasa a **Anulada** y no genera aviso.
6. Tocar **Salir**.

**Como administrador**

7. Entrar con `benicio@ceconsultores.com` / `admin-desarrollo-1` y tocar **Solicitudes**.
8. Se ven las solicitudes de Lucas, las pendientes primero. En la #1 (Plan Estándar) tocar **Marcar como realizada**: PagoNet acepta la facturación y pasa a **Realizado**.
9. En la #2 (Plan Premium) tocar **Marcar como realizada**: PagoNet la **rechaza** porque el Premium no tiene costo definido, y queda **Rechazada** con el motivo. (El botón **Rechazar** también la rechaza, sin pasar por PagoNet.)
10. Tocar **Salir** y volver a entrar como Lucas: en **Mi cuenta** el plan ahora es el **Plan Estándar** y en **Solicitudes** se ven la solicitud realizada, la rechazada con su motivo y los avisos de NotiSys.
11. Para que el Premium se pueda facturar, el administrador entra a **Planes**, edita el Premium y le carga costo y SLA; después Lucas puede volver a pedirlo.

Para repetir el guion desde cero, apagar y volver a iniciar Flask.

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
| HU-09 (US2) | "Mi cuenta" muestra el plan vigente con descripción, costo mensual y SLA | Cliente |
| US3 | Crear una solicitud de cambio de plan (plan y detalle obligatorios; nace «pendiente») | Cliente |
| US5 | Ver mis solicitudes con su estado | Cliente |
| US6 | Anular una solicitud mientras siga pendiente | Cliente |
| US4 | Panel de solicitudes: ver todas y aprobar una pendiente (pasa a «realizado» y el cliente cambia de plan) | Administrador |
| — | Rechazar una solicitud pendiente | Administrador |
| — | Al aprobar, se factura el plan nuevo en PagoNet (simulado); si lo rechaza, la solicitud queda «rechazada» | Sistema |
| — | Avisos de NotiSys (simulado) cuando la solicitud queda pendiente, realizada o rechazada | Sistema y cliente |

Las historias del tablero de Trello (US) y las del backlog del caso (HU) son las mismas funcionalidades con otro número.

**Estados de una solicitud:** `pendiente` → `realizado` (el administrador la aprueba y PagoNet acepta la facturación), `pendiente` → `rechazada` (el administrador la rechaza o PagoNet rechaza la facturación) o `pendiente` → `anulada` (la anula el cliente). Una solicitud realizada, rechazada o anulada ya no cambia.

**Pendientes:** HU-13 (baja de plan) y lo que quedó en el Slice 2: reclamos y mensajería, notificaciones por WhatsApp Business, reportes con AnalytixPro, sincronización con CRMMax y conectar PagoNet y NotiSys reales (hoy son simuladores).

---

## Datos: qué es dinámico y qué es fijo

### Dinámicos (se crean mientras la app funciona)

- Los **clientes** que se registran por el formulario.
- Los cambios de **email y teléfono** del perfil.
- Los **planes** que crea o edita el administrador.
- Las **solicitudes** que crean los clientes y su estado (pendiente, realizado, rechazada o anulada).
- Las **facturas** que se registran al aprobar una solicitud, y los **avisos** de NotiSys.
- La **sesión** de quien está conectado.

### Fijos (están escritos en el código)

- **Lucas Salvarrey**: cliente de ejemplo que se carga al iniciar (`datos.py`).
- **Una solicitud pendiente de ejemplo**: Lucas pide pasar al Plan Estándar (`datos.py`).
- **3 planes iniciales**: Básico, Estándar y Premium. Con los datos de ejemplo el Básico y el Estándar traen descripción, costo y SLA inventados (`PLANES_DEMO` en `datos.py`); el Premium nace sin costo ni SLA para poder ver el rechazo de PagoNet. Con `CARGAR_DATOS=0` los tres nacen vacíos y el administrador los completa.
- **Padrón de VeriCheck**: la lista de personas que pueden registrarse (`vericheck.py`).

### IMPORTANTE: los datos no se guardan

Todo vive en la memoria del proceso. **Al apagar o reiniciar Flask se pierde lo que se registró o editó.** Después de reiniciar solo quedan Lucas con su solicitud de ejemplo, los 3 planes y el admin. Incluye las modificaciones que haga el admin con cada plan, ya sea, valores, descripciones, etc.

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

## PagoNet y NotiSys (simulados)

Igual que VeriCheck, no hacen llamadas de red. Cuando existan los servicios reales, alcanza con reemplazar cada clase por otra con los mismos métodos.

- **PagoNet** (`pagonet.py`, método `procesar_facturacion`): acepta facturar un plan con costo mensual mayor a cero y rechaza si el plan no tiene costo definido.
- **NotiSys** (`notisys.py`, métodos `enviar` y `de_cliente`): guarda los avisos en memoria. El cliente ve sus últimos avisos en **Solicitudes**.

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
├── pagonet.py              Simulador de facturación (PagoNet)
├── notisys.py              Simulador de notificaciones (NotiSys)
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
├── solicitudes/            Solicitudes de cambio de plan
│   ├── __init__.py         Crea el blueprint y registra el filtro "estado_solicitud"
│   ├── estados.py          Los estados y sus textos
│   ├── validaciones.py     Reglas del formulario de una solicitud
│   └── rutas.py            Crear, ver las propias, anular y panel del administrador
│
├── templates/              Páginas HTML (Jinja2)
│   ├── base.html           Estructura común y menú según el rol
│   ├── registro.html   login.html   mi_cuenta.html   editar_perfil.html
│   ├── catalogo.html   plan_form.html
│   └── solicitud_form.html   mis_solicitudes.html   panel_solicitudes.html
│
└── tests/                  Pruebas automáticas (unittest)
    ├── ayudas.py           Bases y atajos compartidos
    ├── test_registro.py    test_identidad.py    test_datos_demo.py
    ├── test_login.py       test_perfil.py
    ├── test_catalogo.py    test_plan_alta.py    test_plan_edicion.py    test_planes_login.py
    ├── test_solicitudes.py
    └── test_simuladores.py
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
- **VeriCheck, PagoNet y NotiSys son simuladores**: no hay validaciones, cobros ni envíos reales.

Son decisiones de alcance para el TP. Si el equipo las cambia, conviene anotarlo acá.
