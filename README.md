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

Para correr los tests:

```powershell
python -m unittest discover -s tests
```


## Usuarios de prueba

| Rol | Email | Contraseña |
|---|---|---|
| Cliente de ejemplo | `lucas@ejemplo.com` | `clave-segura-2` |
| Administrador | `benicio@ceconsultores.com` | `admin-desarrollo-1` |

Son datos de **desarrollo**. No usar contraseñas reales en ningún lugar del proyecto.

---

## Guion de prueba (paso a paso)

Recorrido para probar la demo completa. Se hace con el servidor **recién iniciado**, porque los datos de ejemplo se cargan al arrancar. Lucas parte con el **Plan Básico** y una solicitud pendiente (#1) para pasar al **Plan Estándar**.

**1. Como cliente (Lucas)**

1. Entrar a <http://127.0.0.1:5000/login> con `lucas@ejemplo.com` / `clave-segura-2`.
2. **Mi cuenta**: se ve el Plan Básico con su descripción, costo y SLA (72 h).
3. **Solicitudes**: ya está la #1, pendiente.
4. **Nueva solicitud** → elegir el **Plan Premium**, escribir un detalle y **adjuntar un PDF, PNG o JPG** (hasta 2 MB). Queda pendiente (#2). Probar también un archivo `.txt` o uno de más de 2 MB: el sistema lo rechaza.
5. **Nueva solicitud** → elegir **Ninguno (dar de baja mi plan)**. Queda como baja (#3).
6. **Reclamos → Nuevo reclamo**: asunto «Cobro duplicado», canal Web. Se crea el reclamo #1 con un SLA de 72 h.
7. Volver a ingresar un reclamo con el **mismo asunto** (aunque cambien las mayúsculas o las tildes): no se crea otro, se **suma el mensaje al #1** y aparece la alerta de reclamo duplicado.
8. **Avisos**: el menú muestra cuántos avisos nuevos hay (recepción de la documentación, solicitudes pendientes, reclamo recibido…). Tocar **Salir**.

**2. Como administrador**

9. Entrar con `benicio@ceconsultores.com` / `admin-desarrollo-1`. El **Inicio** resume lo que necesita atención.
10. **Solicitudes**: probar los filtros por estado y por prioridad. En la #2 asignar prioridad **Alta**: sube al principio de la lista y aparece una alerta.
11. En la #2 tocar **Marcar como realizada**: el sistema avisa que **falta validar la documentación**. Tocar **Descargar**, revisar el archivo y **Validar documentación**; ahora sí se puede aprobar. Se genera la factura #1.
12. En la #1 (Plan Estándar) tocar **Marcar como realizada**: Lucas pasa al Estándar y se genera la factura #2. En la #3 (baja) también: Lucas queda **sin plan** y no se factura nada.
13. **Facturación**: en la factura #1 marcar **Simular falla** y tocar **Facturar en PagoNet**. Falla: la factura queda «Falla en PagoNet» y aparece una **alerta roja** en todas las pantallas. Tocar **Realizar devolución**: se devuelve el dinero al cliente. En la factura #2 tocar **Facturar en PagoNet** sin la casilla: queda **Pagada**. (Una factura con falla también se puede **Reintentar**.)
14. **Reclamos**: el #1 está pendiente. Tocar **Simular paso del tiempo** con **80** horas: supera el SLA de 72 h y se **escala solo**. Abrirlo, escribir una respuesta y tocar **Responder** o **Responder y resolver**.
15. **Reportes**: definir un reporte de Solicitudes, armarlo y **Descargar CSV**. Probar una fecha futura en «Desde»: el sistema informa que el **reporte está vacío**.
16. **Registro**: todos los cambios de los pasos anteriores, con quién los hizo. Probar el filtro y la búsqueda.

**3. De nuevo como cliente**

17. Entrar como Lucas: **Avisos** tiene las novedades (documentación validada, solicitudes realizadas, devolución, reclamo escalado y su respuesta). **Mi cuenta** dice que no tiene un plan contratado; desde **Pedir un plan** puede volver a pedir un alta.

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
| HU-09 (US2) | «Mi cuenta» muestra el plan vigente con descripción, costo mensual y SLA | Cliente |
| US3 | Crear una solicitud de alta o cambio de plan (nace «pendiente») | Cliente |
| US5 | Ver mis solicitudes con su estado | Cliente |
| US6 | Anular una solicitud mientras siga pendiente | Cliente |
| US4 | Panel de solicitudes: aprobar o rechazar una pendiente | Administrador |
| HU-13 | **Baja de plan**: elegir «Ninguno» en una solicitud; al aprobarla el cliente queda sin plan y no se factura | Cliente y administrador |
| HU-15 | **Adjuntar documentación** (PDF, PNG o JPG, hasta 2 MB) a una solicitud | Cliente |
| HU-16 | **Validación de la documentación**: el sistema revisa formato, tamaño y contenido; el administrador la revisa y la valida. No se puede aprobar una solicitud con documentación sin validar | Sistema y administrador |
| HU-17 | **Recepción de la documentación**: queda «recibida», el cliente recibe un aviso y el administrador puede descargarla | Sistema |
| HU-19 | **Prioridades**: el administrador asigna prioridad alta, media o baja y filtra las solicitudes por estado y prioridad | Administrador |
| HU-21 | **Facturar por PagoNet** (simulado) con un botón, sobre la factura que genera cada alta o cambio de plan | Administrador |
| HU-22 | **Alerta por falla de PagoNet** (simulada con una casilla) y gestión desde el administrador: reintentar el cobro o **realizar una devolución** al cliente | Administrador |
| HU-24 | **Ingresar un reclamo** (asunto, canal y detalle) | Cliente |
| HU-28 | **Reclamo duplicado**: si ya hay uno abierto sobre el mismo asunto no se crea otro, se suma el mensaje y se alerta | Sistema |
| HU-27 | **Respuesta del reclamo** por parte del administrador, en una conversación | Administrador |
| HU-30 | **Actualizar el estado del reclamo**: responder, resolver, escalar y reabrir | Administrador |
| HU-31 | **Notificación** al cliente de cada novedad de su reclamo | Sistema |
| HU-29 | **Escalado por SLA** (simulado): el reclamo pendiente que supera su SLA se escala solo | Sistema |
| HU-32 | **Definir un reporte**: tipo (solicitudes, reclamos o facturación), período y estado | Administrador |
| HU-33 | **Armar el reporte**: tabla y resumen, con descarga en CSV | Administrador |
| HU-34 | **Reporte vacío**: si no hay datos para lo definido, se informa | Administrador |
| HU-39 | **Registro de cambios**: quién hizo qué y cuándo, con filtro y búsqueda | Administrador |
| — | Avisos de NotiSys (simulado) con contador de avisos nuevos en el menú | Sistema y cliente |
| — | Panel de inicio del administrador y alertas visibles en todas sus pantallas | Administrador |

Las historias del tablero de Trello (US) y las del backlog del caso (HU) son las mismas funcionalidades con otro número.

### Estados

**Solicitud:** `pendiente` → `realizado` (el administrador la aprueba), `rechazada` (el administrador la rechaza) o `anulada` (la anula el cliente). Una solicitud realizada, rechazada o anulada ya no cambia.

**Factura:** `pendiente` → `pagada` (PagoNet confirma) o `fallida` (PagoNet falla). Una `fallida` puede pasar a `pagada` (reintento) o a `devuelta` (devolución al cliente).

**Reclamo:** `pendiente` → `resuelto` (lo resuelve el administrador), `escalado` (lo escala el administrador o vence el SLA) o `anulado` (lo anula el cliente). Un `escalado` puede pasar a `resuelto`, y uno `resuelto` puede reabrirse.

**Documentación:** `recibida` → `validada`.

### Reglas que conviene conocer

- Una solicitud de **alta o cambio** necesita que el plan pedido tenga **costo mensual**; si no, no se puede aprobar. Al aprobarla, el cliente pasa al plan nuevo y se genera una **factura pendiente** (todavía no se cobró).
- Una solicitud con **documentación** no se aprueba hasta que el administrador la **valide**.
- El **SLA de un reclamo** son las horas del plan del cliente (48 h si no tiene plan o su plan no define SLA). El sistema revisa los plazos antes de cada pedido.
- El **paso del tiempo es simulado**: el administrador avanza el reloj en **Reclamos → Simular paso del tiempo**.

**Pendientes:** HU-14 en adelante que no estén en la tabla, notificaciones por WhatsApp Business, reportes con AnalytixPro, sincronización con CRMMax y conectar VeriCheck, PagoNet y NotiSys reales (hoy son simuladores).

---

## Datos: qué es dinámico y qué es fijo

### Dinámicos (se crean mientras la app funciona)

- Los **clientes** que se registran por el formulario.
- Los cambios de **email y teléfono** del perfil.
- Los **planes** que crea o edita el administrador.
- Las **solicitudes** (con su prioridad y su documentación), las **facturas** y las **devoluciones**.
- Los **reclamos** y sus conversaciones.
- Los **avisos** de NotiSys y el **registro de cambios**.
- La **sesión** de quien está conectado y el **tiempo simulado**.

### Fijos (están escritos en el código)

- **Lucas Salvarrey**: cliente de ejemplo que se carga al iniciar (`datos.py`).
- **Una solicitud pendiente de ejemplo**: Lucas pide pasar al Plan Estándar (`datos.py`).
- **3 planes iniciales**: Básico, Estándar y Premium. Con los datos de ejemplo traen descripción, costo y SLA inventados (`PLANES_DEMO` en `datos.py`); con `CARGAR_DATOS=0` nacen sin costo ni SLA y el administrador los completa.
- **Padrón de VeriCheck**: la lista de personas que pueden registrarse (`vericheck.py`).

### IMPORTANTE: los datos no se guardan

Todo vive en la memoria del proceso. **Al apagar o reiniciar Flask se pierde lo que se registró o editó**, incluidos los **documentos adjuntos** y el registro de cambios. Después de reiniciar solo quedan Lucas con su solicitud de ejemplo, los 3 planes y el admin. Incluye las modificaciones que haga el admin con cada plan, ya sea, valores, descripciones, etc.

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

- **PagoNet** (`pagonet.py`, método `procesar_facturacion`): acepta facturar un monto mayor a cero. Si se le pide **simular una falla**, responde como si estuviera caído. Rechaza un monto vacío o en cero.
- **NotiSys** (`notisys.py`, métodos `enviar`, `de_cliente`, `sin_leer` y `marcar_leidos`): guarda los avisos en memoria. El cliente los ve en **Avisos** y el menú cuenta los que no leyó.
- **Reloj** (`reloj.py`): la hora de la aplicación, con horas simuladas para probar el SLA.

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
├── app.py                  Crea la app, registra los módulos y las pantallas de error
├── auth.py                 Login, logout y control de acceso por rol
├── store.py                Almacenamiento en memoria (clientes, planes, solicitudes, facturas, reclamos, registro)
├── alertas.py              Alertas del administrador y avisos sin leer del cliente
├── reloj.py                Reloj de la app, con paso del tiempo simulado
├── vericheck.py            Simulador de validación de identidad
├── pagonet.py              Simulador de facturación (PagoNet)
├── notisys.py              Simulador de notificaciones (NotiSys)
├── datos.py                Datos de ejemplo que se cargan al iniciar
├── requirements.txt        Dependencias
│
├── clientes/               Registro, perfil y avisos del cliente
├── planes/                 Catálogo de planes (formatos de montos, validaciones)
│
├── solicitudes/            Solicitudes de alta, cambio y baja de plan
│   ├── estados.py          Estados, tipos y prioridades, con sus textos
│   ├── documentos.py       Qué archivos se aceptan como documentación
│   ├── validaciones.py     Reglas del formulario de una solicitud
│   └── rutas.py            Cliente: crear, ver, anular, descargar · Administrador: filtrar,
│                           priorizar, validar documentación, aprobar y rechazar
│
├── facturacion/            Facturas, cobro por PagoNet y devoluciones
│   ├── estados.py          Los estados y sus textos
│   └── rutas.py            Listado, cobro (y reintento) y devolución
│
├── reclamos/               Reclamos, conversación, SLA y escalado
│   ├── estados.py          Estados y canales, con sus textos
│   ├── validaciones.py     Reglas de los formularios (y comparación de asuntos)
│   ├── sla.py              Vencimiento del SLA y escalado
│   └── rutas.py            Cliente: ingresar, ver, escribir, anular · Administrador:
│                           responder, escalar, reabrir y simular el tiempo
│
├── reportes/               Reportes de gestión
│   ├── validaciones.py     Qué se acepta al definir un reporte
│   ├── armado.py           Arma el reporte: filas y resumen
│   └── rutas.py            Pantalla y descarga en CSV
│
├── auditoria/              Registro de cambios
│   ├── __init__.py         La función `registrar(...)` que usan todas las pantallas
│   └── rutas.py            Pantalla del registro
│
├── inicio/                 Panel de inicio del administrador
│
├── static/style.css       Estilos de toda la aplicación
├── templates/              Páginas HTML (Jinja2)
│   ├── base.html           Encabezado, menú según el rol, alertas y mensajes
│   ├── login   registro   mi_cuenta   editar_perfil   catalogo   plan_form   avisos   error
│   ├── solicitud_form   mis_solicitudes   panel_solicitudes
│   ├── facturas
│   ├── reclamo_form   mis_reclamos   reclamo_detalle   panel_reclamos
│   └── reportes   registro_cambios   inicio_admin
│
└── tests/                  Pruebas automáticas (unittest)
    ├── ayudas.py           Bases y atajos compartidos
    ├── ayudas_gestion.py   Atajos para solicitudes, facturas y reclamos
    ├── test_registro   test_identidad   test_datos_demo   test_login   test_perfil
    ├── test_catalogo   test_plan_alta   test_plan_edicion   test_planes_login
    ├── test_solicitudes   test_baja_plan   test_documentacion   test_prioridades
    ├── test_facturacion   test_reclamos   test_reportes   test_auditoria
    └── test_alertas_inicio   test_simuladores
```

**Regla de la estructura:** en cada carpeta, `validaciones.py` decide *qué se acepta*, y `rutas.py` decide *qué pasa* cuando alguien entra a una URL. Las validaciones no saben nada de Flask.

---

## Cómo seguir construyendo

### Sí

- **Escribir tests** para lo nuevo, en `tests/`, siguiendo el estilo de los que ya existen.
- **Respetar la estructura**: validaciones en `validaciones.py`, pantallas en `rutas.py`, textos HTML en `templates/`.
- **Dejar constancia** de cada cambio con `registrar(...)` (de `auditoria`), así aparece en el registro de cambios.

### No

- **No subir al repositorio** las carpetas `venv/` ni `__pycache__/`.
- **No subir contraseñas ni claves reales.** Las de este proyecto son de prueba.
- **No cambiar un test para que pase** sin entender por qué fallaba.
- **No hacer cerrar sesión con un link.** Se hace con un botón (`POST`), porque `GET /logout` devuelve error 405.

### Tests con falla conocida

Dos tests de las primeras historias quedaron desactualizados y fallan:

- `test_identidad.ValidacionIdentidadTest.test_mi_cuenta_muestra_la_bienvenida` busca el DNI 30123456, pero el cliente de ejemplo tiene el 45786322.
- `test_registro.RegistroTest.test_email_duplicado` registra a Galo con un email distinto al de Lucas, así que no hay duplicado.

Hay que corregir los tests, no la aplicación.

---

## Limitaciones conocidas

- **Sin persistencia**: los datos y los documentos adjuntos se pierden al reiniciar.
- **Sin protección CSRF** en los formularios.
- **Sin límite de intentos** en el login.
- **Un solo administrador**, definido por configuración.
- **Los «servicios»** del contexto del TP no están modelados: por ahora solo existen los planes.
- **VeriCheck, PagoNet y NotiSys son simuladores**: no hay validaciones, cobros ni envíos reales. Los canales de un reclamo (Web, WhatsApp, Teléfono) son solo una etiqueta.
- **El tiempo del SLA es simulado** y se revisa antes de cada pedido, no en segundo plano.
- Los **documentos** se aceptan por extensión y firma del archivo (PDF, PNG, JPG), pero no se escanean en busca de virus.

Son decisiones de alcance para el TP. Si el equipo las cambia, conviene anotarlo acá.
