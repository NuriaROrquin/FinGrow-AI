"""Router de la version 1 de la API.

Un unico lugar donde se juntan todas las rutas versionadas. Cuando exista una
v2, se agrega app/api/v2/ y ambas conviven: el backend .NET migra cuando
pueda, sin romperse.
"""

from fastapi import APIRouter

from app.api.v1.routes import categorization, message_parsing, transcription, email_parsing

api_router = APIRouter()
api_router.include_router(categorization.router)
api_router.include_router(message_parsing.router)
api_router.include_router(email_parsing.router)
api_router.include_router(transcription.router)
