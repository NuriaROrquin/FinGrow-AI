# FinGrow · AI

Servicio de IA de FinGrow (Python, FastAPI). Es uno de tres repos: FinGrow-FE (Next.js),
FinGrow-BE (.NET 10, reglas de negocio y datos) y **FinGrow-AI** (este). El `README.md` de este
repo ya documenta en detalle arquitectura, capas, ciclo de vida y convenciones — leelo primero.
Acá solo lo que no está ahí o conviene tener presente antes de tocar código.

## Comandos

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
pytest
ruff check .
ruff format .
```

## Lo que no se deduce leyendo el código

**Este servicio es stateless y no conoce reglas de negocio financiero.** Metas, presupuestos y
permisos viven en FinGrow.Domain (.NET). Si una regla de negocio termina escrita acá y también
en el backend, se desincronizan — ver el aviso en `app/domain/enums.py`.

**`ExpenseCategory` (`app/domain/enums.py`) es un contrato con FinGrow-BE.** Los diez valores
tienen que coincidir uno a uno, en texto y en castellano (`ahorro_inversion`, no
`AhorroInversion`), con el enum equivalente de `FinGrow.Domain/Enums` en FinGrow-BE. Un test del
lado de BE rompe el build si las dos listas se separan: si cambiás uno, cambiá el otro.

**No mandar datos personales** (nombre, mail, CBU) en requests ni en prompts si no son
imprescindibles para la inferencia — el README ya lo marca, pero es de las cosas fáciles de
romper sin querer al armar un payload nuevo.

## Convenciones ya cubiertas en README.md

Capas hacia adentro (`domain` no importa nada, `services` no importa `api`), cómo agregar un
endpoint, `async def` vs `def` según si la tarea bloquea, forma de los errores (`{"code",
"message"}`), rutas bajo `/api/v1` y `API_KEY` por header salvo `/health`. No se repite acá para
no tener dos versiones de lo mismo desincronizándose entre sí.
