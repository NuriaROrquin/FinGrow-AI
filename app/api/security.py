"""Autenticacion entre servicios.

Esta API no autentica usuarios finales: de eso se encarga el backend .NET.
Lo unico que valida aca es que quien llama sea el backend, con un secreto
compartido en un header.
"""

import secrets

from fastapi import Header, HTTPException, status

from app.api.deps import SettingsDep


async def require_api_key(
    settings: SettingsDep,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if not settings.auth_enabled:
        # Sin API_KEY configurada la validacion queda apagada, para poder
        # levantar la API en local sin friccion. En produccion es obligatoria.
        return

    # compare_digest en vez de == : compara en tiempo constante y no filtra
    # informacion sobre el secreto por cuanto tarda en fallar.
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key invalida o ausente.",
        )
