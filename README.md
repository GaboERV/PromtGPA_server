# PromptGPT Server / Backend IAnik

Backend asíncrono desarrollado en **FastAPI (Python)** que implementa una **Arquitectura Hexagonal (Clean Architecture)**. Este servidor provee soporte completo para el ecosistema **IAnik**, permitiendo gestionar usuarios, cuadernos de estudio, cargas de archivos, chats grupales, salas de estudio colaborativas, diagnóstico de salud, webhooks asíncronos y evaluaciones inteligentes mediante RAG (Generación Aumentada por Recuperación) con soporte avanzado contra inyección masiva de datos.

---

## 🛠️ Tecnologías Principales

* **FastAPI**: Framework web asíncrono de alto rendimiento.
* **SQLAlchemy 2.0**: ORM asíncrono para mapeo relacional.
* **PostgreSQL** (Producción): Base de datos física relacional.
* **Redis** (Producción): Caché distribuido y almacenamiento temporal para el limitador de frecuencia (*rate limiting*) y control de consumo de claves API de un solo uso.
* **SQLite + aiosqlite** (Desarrollo local / Fallback): Base de datos ligera e in-process para desarrollo rápido.
* **Docker & Docker Compose**: Orquestación y empaquetado del entorno de base de datos, caché y servidor.
* **PyJWT & Bcrypt**: Autenticación criptográfica segura mediante JWT y hashing de contraseñas.

---

## 🏗️ Estructura del Proyecto (Arquitectura Hexagonal)

El código fuente está estructurado bajo principios de arquitectura limpia, asegurando que el núcleo de negocio sea independiente de las tecnologías de base de datos, frameworks o APIs externas:

```text
src/
├── app/                  # Casos de Uso (Lógica de Aplicación)
│   ├── notebook_cases/
│   ├── study_room_cases/
│   ├── user_cases/
│   └── assessment_cases/
├── domain/               # Capa de Dominio (Entidades de Negocio, Excepciones y Puertos)
│   ├── notebook_context/
│   ├── study_room_context/
│   ├── user_context/
│   ├── assessment_context/
│   └── exceptions/
└── infrastructure/       # Adaptadores de Infraestructura (Base de Datos, Web, Controladores)
    ├── core/             # Conexión DB, Redis, Estados Volátiles
    ├── notebook_infra/   # Repositorios y Modelos ORM de Cuadernos
    ├── study_room_infra/ # Repositorios y Modelos ORM de Salas
    ├── user_infra/       # Repositorios, Modelos ORM y Tokenizers de Usuarios
    ├── assessment_infra/ # Repositorios y Motor RAG (Simulado/Real)
    └── web/              # Controladores (Routers), Interceptores de Seguridad y Dependencias
```

---

## 🚀 Guía de Despliegue Rápido (Producción con Docker Compose)

El proyecto incluye una dockerización completa que levanta la base de datos PostgreSQL, el caché Redis y el servidor web automáticamente.

### Requisitos
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y en ejecución.

### Instrucciones
1. Abre una terminal en la raíz del proyecto.
2. Levanta los contenedores compilando la imagen de la aplicación:
   ```bash
   docker compose up --build -d
   ```
3. El servidor FastAPI estará activo en `http://localhost:8000`.
4. Puedes acceder a la documentación interactiva en **`http://localhost:8000/docs`** (Swagger) o **`http://localhost:8000/redoc`** (Redoc).

---

## 💻 Entorno de Desarrollo Local (Fallback Automático)

Para facilitar el desarrollo local sin necesidad de levantar contenedores de Postgres y Redis, el backend cuenta con un **sistema de fallback automático**:
* **Base de datos:** Si no se provee `DATABASE_URL`, el sistema utilizará SQLite local (`prompt_gpt.db`).
* **Caché y Seguridad:** Si no se provee `REDIS_URL`, el sistema utilizará diccionarios y conjuntos en memoria de Python.

### Ejecución Local
1. Crea y activa tu entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Linux/WSL
   .\venv\Scripts\activate   # En Windows
   ```
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecuta la aplicación de desarrollo:
   ```bash
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```
4. Ejecuta la suite de pruebas de integración completa para validar los endpoints:
   ```bash
   python test_flow.py
   ```

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