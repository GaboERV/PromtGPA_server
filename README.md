# PromptGPT Server — Backend IAnik

Backend asíncrono en **FastAPI (Python)** con **Arquitectura Hexagonal (Clean Architecture)**.
Gestiona usuarios, cuadernos de estudio, salas colaborativas, evaluaciones con IA (RAG), webhooks asincrónicos y telemetría de seguridad.

---

## Índice

1. [Tecnologías](#tecnologías)
2. [Estructura del proyecto](#estructura-del-proyecto)
3. [Despliegue rápido (Docker)](#despliegue-rápido-docker)
4. [Entorno de desarrollo local](#entorno-de-desarrollo-local)
5. [Variables de entorno](#variables-de-entorno)
6. [Cosas no obvias que todo desarrollador debe saber](#cosas-no-obvias-que-todo-desarrollador-debe-saber)
7. [Endpoints de la API (61)](#endpoints-de-la-api)
8. [Suite de pruebas](#suite-de-pruebas-de-integración)
9. [Git Flow](#estrategia-de-branching-git-flow)

---

## Tecnologías

| Tecnología | Uso |
|---|---|
| **FastAPI** | Framework web asíncrono |
| **SQLAlchemy 2.0** | ORM async |
| **PostgreSQL** | BD en producción/Docker |
| **SQLite + aiosqlite** | BD en desarrollo local (fallback automático) |
| **Redis 7** | Caché: rate limiting, JTI de un solo uso, audit logs, webhooks |
| **Docker Compose** | Orquestación de todos los servicios |
| **PyJWT + Bcrypt** | Autenticación JWT y hashing |
| **httpx** | Cliente HTTP async para webhooks |

---

## Estructura del Proyecto

```
promptGPT/
├── main.py                          # Punto de entrada: app FastAPI, CORS, routers
├── docker-compose.yml               # Orquestación: web + postgres + redis
├── requirements.txt
├── test_flow.py                     # Suite de integración (61 tests)
├── docker/
│   └── Dockerfile
└── src/
    ├── app/                         # CASOS DE USO (lógica de aplicación)
    │   ├── user_cases/
    │   ├── notebook_cases/
    │   ├── study_room_cases/
    │   └── assessment_cases/
    ├── domain/                      # DOMINIO (entidades, puertos, excepciones)
    │   ├── user_context/
    │   ├── notebook_context/
    │   ├── study_room_context/
    │   ├── assessment_context/
    │   └── exceptions/
    └── infrastructure/              # INFRAESTRUCTURA (adaptadores)
        ├── core/
        │   ├── database.py          # Motor SQLAlchemy + sesión async
        │   └── memory_state.py      # Redis con fallback en memoria
        ├── web/
        │   ├── routers/             # Controladores HTTP
        │   ├── interceptors/
        │   │   └── auth_interceptor.py  # Auth (Bearer/Cookie/API Key)
        │   ├── errors/
        │   │   └── error_handlers.py    # Manejo global de excepciones
        │   └── dependencies.py          # FÁBRICA DE DEPENDENCIAS
        ├── user_infra/
        ├── notebook_infra/
        ├── study_room_infra/
        └── assessment_infra/
            └── services/
                └── simulated_rag_engine.py  # Motor RAG (simulado)
```

---

## Despliegue Rápido (Docker)

```bash
docker compose up --build -d
```

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

> El esquema de BD se crea automáticamente en el startup via `Base.metadata.create_all`. No hay archivos de migración separados.

---

## Entorno de Desarrollo Local

Sin Docker, el sistema activa fallbacks automáticamente:
- Sin `DATABASE_URL` → SQLite local (`prompt_gpt.db`)
- Sin `REDIS_URL` → diccionarios Python en memoria

```bash
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Tests
IS_TESTING=true python test_flow.py
```

---

## Variables de Entorno

> ⚠️ **IMPORTANTE**: Para que la generación de contenido con IA (Chat, Resúmenes, Flashcards, Exámenes) funcione correctamente, es **estrictamente obligatorio** configurar la API Key del proveedor de LLM que elijas (`LLM_PROVIDER`), ya que sin ella el sistema devolverá respuestas simuladas (Mock).

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./prompt_gpt.db` | URI async de BD. Para Postgres: `postgresql+asyncpg://user:pass@host:port/db` |
| `REDIS_URL` | `None` (fallback memoria) | URI de Redis. Ej: `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | `prod-security-fallback-...` | **⚠️ CAMBIAR EN PRODUCCIÓN.** Clave para firmar JWT |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma JWT |
| `API_KEY_COOLDOWN_SECONDS` | `60` | Cooldown entre generaciones de API Keys por usuario |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Orígenes CORS (separados por coma). **No puede ser `*`** |
| `IS_TESTING` | `false` | Activa `NullPool` en SQLAlchemy para tests |

---

## Cosas No Obvias Que Todo Desarrollador Debe Saber

### 1. Arquitectura Hexagonal — La Regla de Oro

```
Domain  ←  App (Casos de Uso)  ←  Infrastructure (Adaptadores)
```

- El **dominio** (`src/domain/`) **nunca** importa nada de infraestructura ni de FastAPI.
- Los **casos de uso** (`src/app/`) orquestan la lógica usando interfaces (Puertos) del dominio.
- La **infraestructura** (`src/infrastructure/`) provee implementaciones concretas.

Los **Puertos** son `Protocol` de Python (no ABCs) → duck typing estructural. Si quieres cambiar de ORM o de JWT a OAuth, solo tocas `infrastructure/`. El dominio no cambia.

---

### 2. Cómo Añadir un Nuevo Módulo Completo

Para un módulo `documents`, crea:

```
src/domain/document_context/
    entities/document.py          # Entidad pura
    repositories/document_repo.py # Puerto (Protocol)

src/app/document_cases/
    document_services.py          # Caso de uso
    dto.py                        # DTOs Pydantic

src/infrastructure/document_infra/
    models/document_orm.py        # Modelo SQLAlchemy
    repositories.py               # Implementación del puerto

src/infrastructure/web/routers/
    document_router.py            # Endpoints FastAPI
```

**Registrar en dos lugares obligatorios:**

1. **`main.py`**: importar el modelo ORM (para `Base.metadata.create_all`) + `app.include_router()`
2. **`dependencies.py`**: añadir función fábrica `get_document_service()`

---

### 3. Redis con Fallback Automático en Memoria

**Archivo clave**: `src/infrastructure/core/memory_state.py`

Todas las operaciones volátiles (JTI, cooldowns, webhooks, audit logs) pasan por este módulo. Cada función sigue el patrón:

```python
async def check_and_use_jti(jti: str) -> bool:
    client = get_redis_client()
    if client:
        return await client.set(f"promptgpt:jti:{jti}", "1", ex=2592000, nx=True) is not None
    # Fallback en memoria
    if jti in used_jti_set:
        return False
    used_jti_set.add(jti)
    return True
```

**El fallback en memoria NO persiste entre reinicios y NO es distribuido** (no funciona con múltiples instancias).

**Namespace Redis** — todas las claves usan prefijo `promptgpt:`:
- `promptgpt:jti:{uuid}` — API Keys consumidas
- `promptgpt:cooldown:{user_id}` — Cooldown de generación
- `promptgpt:api_keys` — Hash con metadata de keys
- `promptgpt:webhook_subscriptions` — Hash de suscripciones
- `promptgpt:webhook_attempts` — Hash de intentos de entrega
- `promptgpt:audit_logs` — Lista LIFO (máx 1000 entradas, auto-trimmed)

---

### 4. Cliente Redis Ligado al Event Loop (Truco Crítico)

**Problema**: `redis.asyncio` crea Futures asociados a un event loop. FastAPI y `TestClient` destruyen loops entre tests → `RuntimeError: Event loop is closed`.

**Solución** en `memory_state.py`:

```python
_redis_client_by_loop = {}

def get_redis_client():
    loop = asyncio.get_running_loop()
    if loop not in _redis_client_by_loop:
        _redis_client_by_loop[loop] = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client_by_loop[loop]
```

Cada event loop obtiene su propio cliente Redis. **Si cambias la lógica de Redis, nunca caches el cliente en una variable global simple. Siempre usa `get_redis_client()`.**

---

### 5. NullPool en Tests (Obligatorio)

**Problema**: SQLAlchemy con `asyncpg` usa pool de conexiones. Al correr tests con `TestClient` (nuevo event loop por test), el pool del loop anterior queda "colgado".

**Solución** en `database.py`:

```python
IS_TESTING = os.getenv("IS_TESTING", "false").lower() == "true"
if IS_TESTING:
    engine_kwargs["poolclass"] = NullPool  # Sin pool
```

**Siempre ejecuta tests con `IS_TESTING=true`:**
```bash
IS_TESTING=true python test_flow.py
```
Sin esto, los tests contra PostgreSQL fallarán con errores de conexión.

---

### 6. Sistema de Excepciones del Dominio

Las excepciones se **lanzan desde los casos de uso** y se **capturan en los handlers globales** de `error_handlers.py`:

| Excepción de Dominio | HTTP |
|---|---|
| `UsuarioNoEncontradoError` | 404 |
| `CredencialesInvalidasError` | 401 |
| `TokenInvalidoError` | 401 |
| `CuadernoNoEncontradoError` | 404 |
| `SalaNoEncontradaError` | 404 |
| `ExamenNoEncontradoError` | 404 |
| `IntentoNoEncontradoError` | 404 |
| `PermisoDenegadoError` | 403 |

**Regla**: Los casos de uso **nunca** lanzan `HTTPException` de FastAPI. Solo excepciones de dominio. La traducción a HTTP ocurre en `error_handlers.py`.

**Para añadir una nueva excepción:**
1. Créala en `src/domain/exceptions/` heredando de `DomainException` (`base.py`)
2. Expórtala en `__init__.py`
3. Registra su handler en `error_handlers.py`

---

### 7. Autenticación: Tres Mecanismos en Paralelo

**Archivo**: `auth_interceptor.py` — tres interceptores con distintos niveles:

| Interceptor | Bearer | Cookie | X-API-Key |
|---|:---:|:---:|:---:|
| `get_current_user_id` | Prioridad 1 | Prioridad 2 | Prioridad 3 |
| `get_current_user_id_bearer_only` | Prioridad 1 | Prioridad 2 | ❌ |
| `get_current_user_id_with_api_key` | Obligatorio | = Bearer | Obligatorio (doble) |

**Flujo de prioridad en `get_current_user_id`:**
1. `Authorization: Bearer <token>` → usarlo
2. Cookie `access_token` → fallback cross-origin
3. Header `X-API-Key` → JWT de un solo uso
4. Nada → HTTP 401

La cookie se inyecta en `POST /users/login` y el navegador la envía automáticamente. Es transparente para el frontend.

---

### 8. Doble Autenticación para Operaciones Sensibles

Crear cuadernos y exámenes colaborativos requiere **dos credenciales simultáneas**:

```
POST /api-keys     → genera API Key JWT con JTI único (cooldown 60s)
POST /notebooks    → Bearer + X-API-Key (la key se consume y destruye)
```

Si reutilizas la misma API Key → `HTTP 401: API Key ya consumida`. Esto previene inyección masiva de recursos.

---

### 9. Motor RAG: Simulado vs Real

**Actualmente**: `SimulatedRAGEngineService` devuelve preguntas hardcodeadas.

**Para implementar el RAG real**, solo necesitas:

1. Crear `src/infrastructure/assessment_infra/services/real_rag_engine.py` implementando los dos métodos del Protocol:
   - `generar_flashcards_por_contexto(prompt, archivo_ids, texto_crudo, cantidad)`
   - `generar_examen_por_contexto(prompt, archivo_ids, texto_crudo)`

2. Cambiar **una línea** en `dependencies.py`:
   ```python
   # Antes:
   def get_rag_engine_service() -> SimulatedRAGEngineService:
       return SimulatedRAGEngineService()
   # Después:
   def get_rag_engine_service() -> RealRAGEngineService:
       return RealRAGEngineService()
   ```

El resto del sistema no cambia porque el contrato es el Protocol del dominio.

---

### 10. Webhooks Asincrónicos

El delivery es fire-and-forget via `asyncio.create_task()`:

```
Examen completado → buscar subscripciones → crear attempt en Redis → POST async al endpoint
```

**Si el servidor se reinicia, los tasks en vuelo se pierden.** El attempt queda en Redis como "pending". Para producción robusta, migrar a Celery + Redis.

---

### 11. Proxy de Permisos en Salas de Estudio

Los invitados **no pueden**: subir archivos, eliminar archivos, ni generar exámenes. Estas verificaciones ocurren en `StudyRoomService` → `PermisoDenegadoError` → HTTP 403.

---

### 12. CORS y Cookies Cross-Origin

```python
# main.py
app.add_middleware(CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Lista explícita, NO "*"
    allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])
```

Cookie `access_token`: `SameSite=None`, `Secure=True`, `HttpOnly=True`.

**Trampa**: En desarrollo local (HTTP), la cookie con `Secure=True` **no se guardará en el navegador**. Para testear cookies en local usa HTTPS (ej. `mkcert`) o el Bearer token desde Swagger.

---

### 13. Inyección de Dependencias — El Archivo Clave

**`src/infrastructure/web/dependencies.py`** es el **único lugar** donde se ensambla la cadena de dependencias.

- Cambiar implementación → cambiar la clase importada aquí
- Añadir servicio nuevo → crear función fábrica aquí
- Mockear en tests → `app.dependency_overrides[get_X_service] = lambda: MockX()`

---

## Endpoints de la API

### Usuarios (`/users`)

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/users/register` | Pública | Registro |
| POST | `/users/login` | Pública | Login → JWT + cookie HttpOnly |
| POST | `/users/logout` | Pública | Elimina cookie |
| GET | `/users/me` | Bearer/Cookie | Perfil |
| DELETE | `/users/me` | Bearer/Cookie | Eliminar cuenta |

### Cuadernos (`/notebooks`)

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/notebooks` | Bearer + X-API-Key | Crear cuaderno (doble auth) |
| GET | `/notebooks` | Bearer/Cookie | Listar cuadernos |
| GET | `/notebooks/{id}` | Bearer/Cookie | Detalle |
| PUT | `/notebooks/{id}` | Bearer/Cookie | Actualizar |
| DELETE | `/notebooks/{id}` | Bearer/Cookie | Eliminar con recursos |
| POST | `/notebooks/{id}/files` | Bearer/Cookie | Subir archivo |
| GET | `/notebooks/{id}/files` | Bearer/Cookie | Listar archivos |
| DELETE | `/notebooks/files/{id}` | Bearer/Cookie | Eliminar archivo |
| POST | `/notebooks/{id}/chats` | Bearer/Cookie | Crear chat IA |
| GET | `/notebooks/{id}/chats` | Bearer/Cookie | Listar chats privados |
| DELETE | `/notebooks/chats/{id}` | Bearer/Cookie | Eliminar chat |
| GET | `/notebooks/chats/{id}/messages` | Bearer/Cookie | Mensajes paginados |
| POST | `/notebooks/chats/{id}/messages` | Bearer/Cookie | Enviar mensaje |
| POST | `/notebooks/{id}/summaries` | Bearer/Cookie | Generar resumen RAG |
| GET | `/notebooks/{id}/summaries` | Bearer/Cookie | Listar resúmenes |
| DELETE | `/notebooks/summaries/{id}` | Bearer/Cookie | Eliminar resumen |

### Salas de Estudio (`/study-rooms`)

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/study-rooms` | Bearer/Cookie | Crear sala |
| POST | `/study-rooms/join` | Bearer/Cookie | Unirse via código |
| DELETE | `/study-rooms/{id}/leave` | Bearer/Cookie | Abandonar sala |
| GET | `/study-rooms/{id}/acceso` | Bearer/Cookie | Check permisos |
| GET | `/study-rooms/{id}/files` | Bearer/Cookie | Listar archivos sala |
| POST | `/study-rooms/{id}/files` | Bearer/Cookie | Subir (Solo Admin) |
| DELETE | `/study-rooms/{id}/files/{file_id}` | Bearer/Cookie | Eliminar (Solo Admin) |
| GET | `/study-rooms/{id}/chats` | Bearer/Cookie | Listar chats de la sala (Privados por usuario) |
| POST | `/study-rooms/{id}/chats/{chat_id}/messages` | Bearer/Cookie | Enviar mensaje en la sala |
| GET | `/study-rooms/{id}/chats/{chat_id}/messages` | Bearer/Cookie | Mensajes paginados (Solo propios) |
| POST | `/study-rooms/{id}/flashcards` | Bearer/Cookie | Generar flashcards |
| POST | `/study-rooms/{id}/exam` | Bearer/Cookie | Generar examen (Solo Admin) |
| GET | `/study-rooms/{id}/summaries` | Bearer/Cookie | Listar resúmenes de la sala |
| GET | `/study-rooms/creadas` | Bearer/Cookie | Salas creadas |
| GET | `/study-rooms/participa` | Bearer/Cookie | Salas donde participa |
| GET | `/study-rooms/{id}` | Bearer/Cookie | Detalle sala |
| GET | `/study-rooms/{id}/acceso` | Bearer/Cookie | Rol del usuario |

### Evaluaciones IA (`/assessments`)

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/assessments/flashcards` | Bearer/Cookie | Generar flashcards con IA |
| GET | `/assessments/flashcards/{nid}` | Bearer/Cookie | Flashcards del cuaderno |
| POST | `/assessments/exam` | Bearer/Cookie | Generar examen con IA |
| GET | `/assessments/exam/{eid}` | Bearer/Cookie | Estructura examen |
| GET | `/assessments/exam/notebook/{nid}` | Bearer/Cookie | Exámenes de cuaderno |
| GET | `/assessments/exam/sala/{sid}` | Bearer/Cookie | Exámenes de sala |
| POST | `/assessments/exam/{eid}/submit` | Bearer/Cookie | Enviar y calificar |
| GET | `/assessments/attempts` | Bearer/Cookie | Historial intentos |
| GET | `/assessments/attempts/{iid}` | Bearer/Cookie | Detalle intento |
| GET | `/assessments/attempts/exam/{eid}` | Bearer/Cookie | Intentos por examen |

### Progreso (`/progress`)

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/progress/metrics` | Bearer/Cookie | Promedio y totales |
| GET | `/progress/pending-cards` | Bearer/Cookie | Flashcards pendientes |
| GET | `/progress/daily-activity` | Bearer/Cookie | Actividad diaria |

### API Keys (`/api-keys`)

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/api-keys` | Bearer/Cookie | Generar key de un solo uso |
| GET | `/api-keys` | Bearer/Cookie | Historial de keys |
| DELETE | `/api-keys/{id}` | Bearer/Cookie | Revocar key |

### Webhooks (`/webhooks`)

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/webhooks/subscriptions` | Bearer/Cookie | Registrar URL |
| GET | `/webhooks/subscriptions/org/{id}` | Bearer/Cookie | Webhooks de sala |
| GET | `/internal/webhooks/attempts` | Pública | Log de entregas |
| POST | `/internal/webhooks/attempts/{id}/retry` | Pública | Reintentar entrega |

### Administración (`/admin`)

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/admin/classes/{id}/stats` | Bearer/Cookie | Notas promedio |
| GET | `/admin/users/{id}/audit-logs` | Bearer/Cookie | Trazas seguridad |
| GET | `/admin/users/{id}/storage` | Bearer/Cookie | Almacenamiento MB |

### Diagnósticos

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/` | Pública | Estado online |
| GET | `/health/v1` | Pública | Salud detallada |
| GET | `/health/processes` | Pública | Hilos activos |
| GET | `/health/metadata` | Pública | Versión y metadatos |

---

## Suite de Pruebas de Integración

```bash
IS_TESTING=true python test_flow.py
```

Valida 61 endpoints secuencialmente con `TestClient` (sin servidor real). Al inicio se purgan claves Redis `promptgpt:*` y se recrea la BD SQLite.

---

## 📋 Documentación de Endpoints de la API (60 Funcionales)

A continuación se detallan las 60 rutas funcionales agrupadas por módulo:

### 🔑 1. Usuarios (`/users`)
* `POST   /users/register` — Registro de cuentas de usuario.
* `POST   /users/login` — Autenticación de usuarios (Retorna un JWT Bearer Token).
* `GET    /users/me` — Consultar información de perfil del usuario autenticado (Protegido).
* `DELETE /users/me` — Eliminar cuenta de usuario (Protegido por contraseña).

### 📖 2. Cuadernos (`/notebooks`)
* `POST   /notebooks` — Crear cuaderno (Requiere doble autenticación: Bearer Token + `X-API-Key` de un solo uso para evitar inyección masiva).
* `GET    /notebooks` — Listar cuadernos del usuario.
* `GET    /notebooks/{notebook_id}` — Obtener detalle de un cuaderno.
* `PUT    /notebooks/{notebook_id}` — Actualizar título/descripción de un cuaderno.
* `DELETE /notebooks/{notebook_id}` — Eliminar cuaderno y todos sus recursos.
* `POST   /notebooks/{notebook_id}/files` — Cargar archivos (PDF, TXT, etc.) al cuaderno.
* `GET    /notebooks/{notebook_id}/files` — Listar archivos de un cuaderno.
* `DELETE /notebooks/files/{archivo_id}` — Eliminar archivo específico de la base de datos.
* `POST   /notebooks/{notebook_id}/chats` — Crear un hilo de conversación de chat con IA.
* `GET    /notebooks/{notebook_id}/chats` — Listar los chats abiertos en el cuaderno.
* `DELETE /notebooks/chats/{chat_id}` — Eliminar un hilo de chat.
* `GET    /notebooks/chats/{chat_id}/messages` — Obtener mensajes de chat paginados.
* `POST   /notebooks/chats/{chat_id}/messages` — Enviar mensaje del usuario al chat.

### 👥 3. Salas de Estudio (`/study-rooms`)
* `POST   /study-rooms` — Crear una sala colaborativa asociada a un cuaderno.
* `POST   /study-rooms/join` — Unirse a una sala de estudio utilizando un código de acceso alfanumérico.
* `GET    /study-rooms/creadas` — Listar las salas colaborativas creadas por el usuario.
* `GET    /study-rooms/participa` — Listar las salas en las que participa el usuario.
* `GET    /study-rooms/{sala_id}` — Obtener información detallada de la sala.
* `GET    /study-rooms/{sala_id}/acceso` — Verificar rol del usuario en la sala (`creador` o `invitado`).
* `POST   /study-rooms/{sala_id}/files` — Subir archivo colaborativo (Bloqueado por Proxy para `invitado`).
* `GET    /study-rooms/{sala_id}/files` — Listar archivos subidos en la sala.
* `DELETE /study-rooms/{sala_id}/files/{archivo_id}` — Eliminar un archivo (Bloqueado por Proxy para `invitado`).
* `GET    /study-rooms/{sala_id}/chats` — Listar chats colaborativos de la sala.
* `GET    /study-rooms/{sala_id}/chats/{chat_id}/messages` — Listar mensajes del chat colaborativo.
* `POST   /study-rooms/{sala_id}/chats/{chat_id}/messages` — Enviar un mensaje al chat colaborativo.
* `POST   /study-rooms/{sala_id}/flashcards` — Crear una flashcard colaborativa en la sala.
* `GET    /study-rooms/{sala_id}/flashcards` — Listar flashcards de la sala.
* `POST   /study-rooms/{sala_id}/exam` — Generar examen colaborativo (Bloqueado por Proxy para `invitado`).
* `GET    /study-rooms/{sala_id}/exams` — Listar exámenes generados en la sala de estudio.

### 🧠 4. Evaluaciones IA y RAG (`/assessments`)
* `POST   /assessments/flashcards` — Generar flashcards automáticamente con IA a partir de texto o archivo.
* `GET    /assessments/flashcards/{notebook_id}` — Consultar flashcards guardadas de un cuaderno.
* `POST   /assessments/exam` — Generar examen de opción múltiple con IA a partir del contexto del cuaderno.
* `GET    /assessments/exam/{examen_id}` — Estructura de preguntas y opciones del examen generado.
* `GET    /assessments/exam/notebook/{notebook_id}` — Obtener todos los exámenes asociados a un cuaderno.
* `GET    /assessments/exam/sala/{sala_id}` — Obtener exámenes de una sala colaborativa.
* `POST   /assessments/exam/{examen_id}/submit` — Enviar respuestas del examen para calificar y persistir el intento.
* `GET    /assessments/attempts` — Historial de intentos de exámenes resueltos por el usuario.
* `GET    /assessments/attempts/{intento_id}` — Detalle, calificación y respuestas completas de un intento.
* `GET    /assessments/attempts/exam/{examen_id}` — Intentos de examen resueltos para una plantilla de examen.

### 📈 5. Progreso e Historial (`/progress`)
* `GET    /progress/metrics` — Promedio acumulado y total de exámenes resueltos por el usuario.
* `GET    /progress/pending-cards` — Listar tarjetas de estudio (flashcards) pendientes.
* `GET    /progress/daily-activity` — Consolidado de actividad diaria basado en fecha de subida de archivos, exámenes completados y mensajes enviados.

### 🛡️ 6. API Keys de Un Solo Uso (`/api-keys`)
* `POST   /api-keys` — Generar una API Key firmada JWT con JTI único (Requiere Bearer de sesión. Límite de cooldown activo para mitigar inyecciones).
* `GET    /api-keys` — Listar historial de claves emitidas (Requiere Bearer).
* `DELETE /api-keys/{key_id}` — Invalidar/Revocar una clave antes de ser consumida (Requiere Bearer).

### 🪝 7. Webhooks (`/webhooks`)
* `POST   /webhooks/subscriptions` — Registrar una URL para recibir notificaciones HTTP POST del evento `exam.completed`.
* `GET    /webhooks/subscriptions/org/{org_id}` — Listar webhooks activos de una sala de estudio.
* `GET    /internal/webhooks/attempts` — Consultar log de intentos de entrega asíncronos en segundo plano.
* `POST   /internal/webhooks/attempts/{attempt_id}/retry` — Re-encolar un webhook de forma asíncrona tras un fallo de conexión.

### 📊 8. Administración y Telemetría (`/admin`)
* `GET    /admin/classes/{sala_id}/stats` — Notas promedio acumuladas de los alumnos en exámenes de una sala.
* `GET    /admin/users/{user_id}/audit-logs` — Obtener trazas de auditoría de seguridad del usuario (Detección de conductas sospechosas).
* `GET    /admin/users/{user_id}/storage` — Calcular dinámicamente el almacenamiento en MB que ocupan los archivos cargados por el inquilino.

### 🔍 9. Diagnósticos e Internos
* `GET    /` — Estado de salud online básico.
* `GET    /health/v1` — Detalle de salud detallado del servidor.
* `GET    /health/processes` — Monitoreo de hilos activos en segundo plano.
* `GET    /health/metadata` — Versión y metadatos del software.

---

## 🔀 Estrategia de Branching (Git Flow)

El proyecto utiliza la metodología **Git Flow** para regular los flujos de integración y despliegue continuo de forma segura:
* **`main`**: Código de producción estable. Marcas con Tag de versiones oficiales (ej. `v0.2.0`).
* **`develop`**: Rama principal de desarrollo donde se integran las nuevas funcionalidades terminadas.
* **`feature/*`**: Ramas de desarrollo de características individuales creadas desde `develop`.
* **`release/*`**: Ramas de preparación de versión creadas desde `develop` para fusionarse en `main` y sincronizarse con `develop`.
* **`hotfix/*`**: Ramas de emergencia creadas desde `main` para parches críticos de producción.
