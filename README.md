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

## Endpoints

| Ruta | Que hace |
|---|---|
| `POST /api/v1/categorization/transactions` | Categoriza un lote de gastos (sync de Mercado Pago) |
| `POST /api/v1/message-parsing/transactions` | Interpreta un mensaje de chat ("Gaste $500 en el super") como un movimiento: tipo, monto, moneda, categoria, descripcion, medio de pago y fecha (HU-13) |
| `POST /api/v1/transcription/audio` | Transcribe una nota de voz (multipart, campo `file`) a texto, para despues interpretarlo con `message-parsing` (T-21) |
| `POST /api/v1/receipt-scanning/receipts` | Lee un ticket o factura (multipart, campo `file`) y devuelve comercio, total, moneda, fecha, categoria, medio de pago y confianza (HU-12) |

| `POST /api/v1/email-parsing/bills` | Decide si un mail es una factura o un consumo y extrae empresa, total, moneda, vencimiento y categoria (HU-06, sync de Gmail) |

`message-parsing` devuelve un `status`: `parsed` (trae `transaction`), `missing_amount`,
`not_a_transaction` o `multiple_transactions`. Los tres ultimos no traen movimiento: el backend
repregunta. El monto nunca se estima; si el texto no lo dice, la respuesta es `missing_amount`.
`payment_method` y `occurred_on` vienen en `null` cuando el mensaje no los menciona. Para
resolver "ayer" o "el lunes" el backend manda `today` (la fecha de hoy en Argentina); si no la
manda, se usa la del servidor en hora argentina. Con un periodo vago ("la semana pasada") la
fecha es una estimacion y `occurred_on_is_estimate` viene en `true`, para que el backend la
marque como estimada en la propuesta. Que hacer con una fecha que falta o que cae en
el futuro lo decide el backend.

`email-parsing` solo toma como factura la de un servicio que se paga periodicamente (luz, gas,
agua, internet, telefonia, prepagas, impuestos, expensas): viajes, compras y resumenes de tarjeta
son `not_a_bill` aunque traigan un total. Devuelve `bill` (trae `bill`), `missing_amount` (es una factura pero el mail no
dice el total, por ejemplo cuando solo ofrece descargarla) o `not_a_bill`. Acepta reenvios: la
empresa sale del cuerpo, no del remitente. `due_date` viene en `null` si el mail no lo dice o
no se pudo leer; el backend lo usa para no proponer dos veces la misma factura.

Con `LLM_PROVIDER` distinto de `anthropic`, el stub responde con el primer elemento de
`examples` del JSON Schema que recibe, si lo trae: asi cada endpoint nuevo define su propia
respuesta de relleno junto a su schema.

`transcription` no usa Claude: la API de Anthropic no acepta audio. Usa OpenAI
(`gpt-4o-mini-transcribe`) con `TRANSCRIPTION_PROVIDER=openai` y `TRANSCRIPTION_API_KEY`; con
`stub` (el default) responde siempre el mismo texto, para integrar sin gastar. El audio viaja a
OpenAI: es lo minimo imprescindible para transcribirlo, no se manda nada mas del empleado.

- Formatos: ogg (las notas de voz de WhatsApp y Telegram, tambien como `.opus`), mp3, mp4, m4a,
  wav, webm y flac. El
  formato sale del `Content-Type` de la parte (`audio/ogg; codecs=opus` incluido) y, si no es de
  audio, de la extension del archivo.
- Devuelve `text`, `language` (`TRANSCRIPTION_LANGUAGE`, `es` por defecto) y `model`.
- Errores propios: `audio_not_understood` (422: audio vacio, danado o sin ninguna frase
  reconocible), `unsupported_audio` (415) y `audio_too_large` (413, por encima de
  `TRANSCRIPTION_MAX_AUDIO_BYTES`, 20 MB por defecto). Si OpenAI no responde, `model_unavailable`
  (503). El backend traduce los tres primeros en el aviso de HU-14 de repetir el audio o cargarlo
  por texto.

`receipt-scanning` lee el comprobante con Amazon Textract (`AnalyzeExpense`) y usa Claude solo
para limpiar el nombre del comercio y elegir la categoria. Con `OCR_PROVIDER=textract` hacen falta
`OCR_AWS_REGION`, `OCR_AWS_ACCESS_KEY_ID` y `OCR_AWS_SECRET_ACCESS_KEY` (un usuario IAM con permiso
solo para `textract:AnalyzeExpense`); con `stub` (el default) devuelve siempre el mismo ticket de
supermercado, para integrar sin gastar.

- Formatos: JPG, PNG y PDF de una pagina, hasta `OCR_MAX_DOCUMENT_BYTES` (5 MB, el maximo que
  Textract acepta en bytes). El formato sale del `Content-Type` y, si no es uno de esos, de la
  extension; los primeros bytes tienen que coincidir con el tipo declarado.
- Campo opcional `default_currency` (`ARS` por defecto): la moneda cuando el ticket no dice otra.
- Devuelve un `status`: `parsed` (trae `receipt`), `missing_amount` (se leyo algo pero no un total)
  o `unreadable` (el OCR no encontro nada). El monto nunca se estima.
- Monto y fecha los interpreta el codigo, no el modelo: los importes aceptan `1.250,50` y
  `1,250.50`, y las fechas van con el dia primero (`14/10/26`, `14 oct 2026`). Una fecha que no se
  puede leer viene en `null` y el backend decide cual usar.
- El medio de pago sale de buscar en el texto del ticket palabras como "debito", "cuotas", "QR" o
  "efectivo"; si no aparece ninguna viene en `null`.
- `confidence` es la menor entre la confianza del OCR para monto, fecha y comercio. Un campo que
  no se pudo leer cuenta como 0.5, asi que un ticket sin fecha o sin comercio nunca tiene confianza
  alta.
- Al modelo solo le llegan el nombre del comercio y los productos: el resto del ticket (CUIT,
  ultimos digitos de la tarjeta, nombre del cliente) no sale del servicio.
- Errores propios: `unsupported_document` (415: otro formato, o un PDF de mas de una pagina),
  `document_too_large` (413) y `document_not_readable` (422: archivo vacio o danado). Si Textract
  no responde o rechaza las credenciales, `model_unavailable` (503).
- Costo de referencia: USD 0,01 por pagina; las cuentas nuevas de AWS tienen 100 paginas por mes
  gratis durante tres meses.

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
