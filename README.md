# FinGrow AI

Servicio de IA de FinGrow. Resuelve inferencia: clasificar, resumir, predecir.

## Que es y que no es

Es un servicio HTTP **stateless**: no tiene base de datos y no recuerda nada
entre requests. Cada llamada trae toda la informacion que necesita para
responder, asi se pueden levantar N copias detras de un balanceador sin que
importe a cual le cae cada request.

No es un backend de la plataforma. No modela metas, presupuestos ni permisos:
recibe datos, infiere y devuelve. Si una regla de negocio termina escrita aca
y tambien en el backend, se van a desincronizar.

**Privacidad:** no mandar datos personales (nombre, mail, CBU) si no son
imprescindibles para la inferencia. IDs y montos alcanzan.

## Arranque rapido

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (en Linux/Mac: source .venv/bin/activate)
pip install -e ".[dev]"
copy .env.example .env          # Windows  (en Linux/Mac: cp)
uvicorn app.main:app --reload --port 8000
```

- Documentacion interactiva: http://localhost:8000/docs
- Contrato OpenAPI: http://localhost:8000/openapi.json
- Tests: `pytest`
- Lint: `ruff check .` / `ruff format .`

## Estructura

| Carpeta | Que hay |
|---|---|
| `app/main.py` | Arranque de la app y cableado de las piezas |
| `app/core/` | Config (`pydantic-settings`), logging, excepciones propias |
| `app/api/` | Routers, dependencias (`Depends`), auth y manejo de errores |
| `app/schemas/` | Modelos Pydantic de request y response |
| `app/domain/` | Tipos propios del dominio de inferencia |
| `app/services/` | Casos de uso. No saben nada de HTTP |
| `app/infrastructure/` | Cliente del modelo y prompts |

**Regla de dependencias:** las capas dependen hacia adentro.
`domain/` no importa nada. `services/` no importa `api/`.
`infrastructure/` implementa contratos, no los define.

Python no impide romper esa regla: cualquier modulo puede importar cualquier
otro. La sostienen el equipo y el code review. Si en algun momento queremos
que la verifique el CI, existe [import-linter](https://import-linter.readthedocs.io/).

## Como agregar un endpoint

Siempre el mismo recorrido, de adentro hacia afuera:

1. `app/schemas/<caso>.py` -- request y response con Pydantic.
2. `app/services/<caso>_service.py` -- la logica, sin saber nada de HTTP.
3. `app/api/deps.py` -- como se construye el service.
4. `app/api/v1/routes/<caso>.py` -- la ruta, que solo traduce HTTP <-> service.
5. `app/api/v1/router.py` -- registrar el router.
6. `tests/test_<caso>.py`.

Ver `categorization` como ejemplo completo: hoy devuelve una respuesta de
relleno, pero con la forma final del contrato, para que quien consuma la API
pueda integrar en paralelo.

## Ciclos de vida

- Una funcion resuelta con `Depends()` se ejecuta **una vez por request**.
- Lo caro de construir -- clientes HTTP, modelos de ML -- se crea **una sola
  vez al arrancar**, en el `lifespan` de `main.py`, y se guarda en `app.state`.
  Cargar un modelo tarda segundos: hacerlo por request mata la API.

## `async def` vs `def`

FastAPI atiende muchos requests con un solo hilo que rota entre tareas
mientras esperan. Si una funcion `async def` bloquea -- calculo pesado, o una
libreria que no es async -- ese hilo se clava y **toda la API deja de
responder**, no solo ese request.

- Llamada a una API externa con un cliente async -> `async def`.
- Modelo local, o libreria que bloquea -> `def` a secas: FastAPI la manda sola
  a un hilo aparte.

## Convenciones

- JSON en `snake_case`.
- Todos los errores salen con la misma forma: `{"code": "...", "message": "..."}`.
  `code` es un identificador estable, pensado para que el consumidor lo mapee
  sin parsear el texto del mensaje.
- Rutas versionadas bajo `/api/v1`.
- `GET /health` va en la raiz y sin API key, para que el orquestador (Docker,
  Kubernetes) pueda chequear vida sin credenciales.
- El resto de las rutas va detras de la API key (`X-API-Key`). Si `API_KEY`
  esta vacia la validacion queda apagada: sirve para desarrollo local, en
  produccion es obligatoria.
