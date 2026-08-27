"""Router de la version 1 de la API.

Un unico lugar donde se juntan todas las rutas versionadas. Cuando exista una
v2, se agrega app/api/v2/ y ambas conviven: el backend .NET migra cuando
pueda, sin romperse.
"""

from fastapi import APIRouter

from app.api.v1.routes import categorization

api_router = APIRouter()
api_router.include_router(categorization.router)
