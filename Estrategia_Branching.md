# Estrategia de Control de Versiones: Git Flow para PromptGPT / IAnik

Este documento detalla la estrategia de control de versiones y el flujo de trabajo (branching strategy) adoptado para el desarrollo integrado del sistema **IAnik (PromptGPT)**, el cual está compuesto por un ecosistema desacoplado de dos aplicaciones principales: un **Frontend** desarrollado en Next.js y un **Backend** desarrollado en FastAPI.

---

## 1. Introducción

El éxito de una arquitectura moderna basada en microservicios o frontend/backend desacoplados reside no solo en el diseño de su código, sino en la metodología utilizada para coordinar el trabajo de desarrollo de forma concurrente, segura y escalable. 

Para este ecosistema, se ha adoptado la metodología **Git Flow** como estándar de control de versiones en ambos repositorios. A continuación, se desarrollan y justifican de forma pormenorizada los siguientes temas:
* **Justificación de la Estrategia:** Razones técnicas y metodológicas para elegir Git Flow en un entorno multi-repositorio.
* **Explicación de los Repositorios y Ramas:** Descripción detallada de los repositorios de Frontend y Backend, la correspondencia de sus ramas y el propósito de cada una bajo el estándar Git Flow.
* **Implementación Práctica de la Estrategia:** Guía técnica detallada con los comandos Git específicos necesarios para llevar a cabo el ciclo completo de características (Features), lanzamientos (Releases) y parches rápidos de producción (Hotfixes).
* **Enlaces a los Repositorios:** Direcciones SSH y HTTPS oficiales para acceder a los repositorios de Frontend y Backend.

---

## 2. Justificación de la Estrategia de Branching (Git Flow)

Coordinar dos aplicaciones independientes (Frontend en Next.js/TypeScript y Backend en FastAPI/Python) que se comunican mediante HTTP REST requiere un orden metodológico estricto para evitar incoherencias en los despliegues (por ejemplo, desplegar un cambio visual en el Frontend que dependa de un endpoint del Backend que aún no ha sido subido a producción). 

La elección de **Git Flow** se justifica técnicamente por los siguientes beneficios:

### A. Aislamiento Absoluto de Tareas (Feature Branching)
Evita que el código inestable o incompleto de una nueva funcionalidad contamine el flujo principal de trabajo. Cada programador trabaja en una rama `feature/*` independiente. El código solo se integra en el flujo común (`develop`) tras pasar revisiones o pruebas de integración.

### B. Separación Clara entre Estado de Desarrollo y Producción
* La rama `develop` actúa como el punto de integración diario, reuniendo todas las nuevas funcionalidades terminadas.
* La rama `main` (o `master`) se reserva **exclusivamente** para código 100% probado, auditado y listo para ser utilizado por los usuarios finales.

### C. Lanzamientos Seguros y Previsibles (Releases)
El uso de ramas `release/*` permite "congelar" el conjunto de características que formarán la siguiente versión (ej. `v0.1.0`). Durante esta fase, se realizan las pruebas de integración final, asegurando que el Frontend se comunica perfectamente con el Backend. Los desarrolladores pueden seguir trabajando en el desarrollo de la versión `v0.2.0` en `develop` sin alterar las pruebas del release.

### D. Soporte Inmediato en Producción (Hotfixes)
Si surge un error crítico en producción (por ejemplo, un fallo en la validación de tokens JWT), Git Flow permite abrir una rama de emergencia `hotfix/*` directamente desde `main`. Esto permite corregir el error y desplegarlo en producción inmediatamente sin tener que arrastrar código inacabado de la rama `develop`.

---

## 3. Explicación de los Repositorios y sus Ramas

El ecosistema de la aplicación está dividido en dos repositorios específicos para facilitar la separación de responsabilidades:

### 3.1. Repositorio Backend: `PromtGPA_server`
* **Tecnologías Principales:** FastAPI (Python), SQLAlchemy 2.0 (ORM Asíncrono), SQLite (Base de datos local con soporte `aiosqlite`), PyJWT (Tokens de autenticación) y Bcrypt (Cifrado asíncrono no bloqueante).
* **Ubicación en GitHub:** [PromtGPA_server](https://github.com/GaboERV/PromtGPA_server)

### 3.2. Repositorio Frontend: `Front_IAnik`
* **Tecnologías Principales:** Next.js 16 (React 19, App Router), TypeScript, Tailwind CSS v4 (PostCSS) y Axios (Cliente HTTP para conectar con FastAPI).
* **Ubicación en GitHub:** [Front_IAnik](https://github.com/shynzx/Front_IAnik)

---

### 3.3. Estructura y Propósito de las Ramas según Git Flow

Ambos repositorios están estructurados bajo el mismo estándar de nomenclatura, con un conjunto de ramas remotas que cumplen propósitos definidos:

| Rama | Tipo | Tiempo de Vida | Propósito Técnico |
| :--- | :--- | :--- | :--- |
| `main` | Principal | Infinito | Código de producción estable. Cada commit en esta rama representa una versión pública lista para desplegarse, marcada con un Tag (ej. `v0.1.0`, `v0.1.1`). |
| `develop` / `Develop` | Principal | Infinito | Rama de integración activa. Aquí se recopila el desarrollo de todas las nuevas funcionalidades del equipo. Es la base para preparar los siguientes lanzamientos. |
| `feature/*` / `Feature` | Soporte | Efímero | Ramas creadas para desarrollar una funcionalidad específica. Nacen de `develop` y se vuelven a fusionar en ella al terminar. Nunca interactúan con `main`. |
| `release/*` / `Realese` | Soporte | Efímero | Ramas de preparación de versión. Sirven para probar y corregir pequeños bugs del lanzamiento. Nacen de `develop` y se fusionan en `main` y en `develop` al finalizar. |
| `hotfix/*` / `Hotfix` | Soporte | Efímero | Ramas de parche rápido en caliente. Sirven para solucionar fallos urgentes en producción. Nacen de `main` y se fusionan de vuelta en `main` y en `develop`. |
| `QA` | Validación | Permanente | Rama utilizada por el equipo del frontend para desplegar pre-lanzamientos en un entorno de control de calidad (Quality Assurance) para pruebas manuales y automatizadas. |

---

## 4. Cómo se Implementa la Estrategia de Branching

A continuación se presenta la guía de comandos específicos de Git para operar bajo esta metodología en el día a día.

### A. Ciclo de Vida de una Característica (Feature)
Cuando vayas a crear una nueva funcionalidad (por ejemplo, la lógica de creación de cuadernos en el backend):

1. **Crear la rama partiendo de `develop`:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/notebook-creation
   ```
2. **Desarrollar y hacer commits incrementales:**
   ```bash
   git commit -am "feat(domain): define notebook entity and interface"
   ```
3. **Integrar la característica en `develop` (usando `--no-ff` para preservar el historial):**
   ```bash
   git checkout develop
   git merge --no-ff feature/notebook-creation -m "merge: integrate notebook creation feature"
   ```
4. **Eliminar la rama local:**
   ```bash
   git branch -d feature/notebook-creation
   ```

---

### B. Ciclo de Lanzamiento de una Versión (Release)
Cuando el conjunto de features en `develop` está completo y es hora de publicar la versión `v1.0.0`:

1. **Crear la rama de release desde `develop`:**
   ```bash
   git checkout develop
   git checkout -b release/v1.0.0
   ```
2. **(Opcional) Corregir detalles menores o subir números de versión. Luego, fusionar en `main` y etiquetar:**
   ```bash
   git checkout main
   git merge --no-ff release/v1.0.0 -m "merge: release version 1.0.0"
   git tag -a v1.0.0 -m "Version 1.0.0 Release"
   ```
3. **Fusionar los posibles fixes aplicados de vuelta en `develop`:**
   ```bash
   git checkout develop
   git merge --no-ff release/v1.0.0 -m "merge: sync release v1.0.0 changes"
   ```
4. **Eliminar la rama de release:**
   ```bash
   git branch -d release/v1.0.0
   ```

---

### C. Ciclo de Parche Crítico en Producción (Hotfix)
Si se detecta un fallo de seguridad crítico en producción (por ejemplo, en la versión `v1.0.0`):

1. **Crear la rama de hotfix partiendo de `main`:**
   ```bash
   git checkout main
   git checkout -b hotfix/v1.0.1
   ```
2. **Corregir el bug y confirmar cambios:**
   ```bash
   # ... corregir código ...
   git commit -am "fix(prod): correct jwt token expiration boundary error"
   ```
3. **Fusionar en `main` y etiquetar la nueva versión corregida (`v1.0.1`):**
   ```bash
   git checkout main
   git merge --no-ff hotfix/v1.0.1 -m "merge: apply hotfix v1.0.1 to production"
   git tag -a v1.0.1 -m "Release version 1.0.1 (Hotfix)"
   ```
4. **Fusionar en `develop` para sincronizar el parche con las características futuras:**
   ```bash
   git checkout develop
   git merge --no-ff hotfix/v1.0.1 -m "merge: sync hotfix v1.0.1 changes"
   ```
5. **Eliminar la rama del hotfix:**
   ```bash
   git branch -d hotfix/v1.0.1
   ```

---

## 5. Enlaces a los Repositorios

Los repositorios oficiales se encuentran alojados en GitHub. Puedes acceder a ellos mediante los siguientes enlaces:

### 5.1. Repositorio Backend (FastAPI / Server)
* **URL Web (HTTPS):** [https://github.com/GaboERV/PromtGPA_server](https://github.com/GaboERV/PromtGPA_server)
* **Dirección de Clonación SSH:** `git@github.com:GaboERV/PromtGPA_server.git`

### 5.2. Repositorio Frontend (Next.js / Client)
* **URL Web (HTTPS):** [https://github.com/shynzx/Front_IAnik](https://github.com/shynzx/Front_IAnik)
* **Dirección de Clonación SSH:** `git@github.com:shynzx/Front_IAnik.git`
