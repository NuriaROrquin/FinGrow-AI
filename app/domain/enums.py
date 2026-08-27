"""Tipos del dominio de IA.

OJO con el limite: aca van solo los tipos que esta API necesita para razonar
(que categorias existe, que nivel de confianza hay). Las reglas de negocio
financiero -- metas, presupuestos, permisos -- viven en FinGrow.Domain, del
lado .NET. Si una regla aparece escrita de los dos lados, se van a
desincronizar.
"""

from enum import StrEnum


class ExpenseCategory(StrEnum):
    """Categorias de gasto que el modelo puede asignar.

    Tiene que estar alineada con el enum equivalente de FinGrow.Domain/Enums.
    """

    ALIMENTOS = "alimentos"
    TRANSPORTE = "transporte"
    VIVIENDA = "vivienda"
    SERVICIOS = "servicios"
    SALUD = "salud"
    EDUCACION = "educacion"
    ENTRETENIMIENTO = "entretenimiento"
    INDUMENTARIA = "indumentaria"
    AHORRO_INVERSION = "ahorro_inversion"
    OTROS = "otros"
