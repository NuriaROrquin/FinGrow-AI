from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import Language


class FinancialConcern(StrEnum):
    """Preocupaciones que el backend detecta con reglas sobre los puntajes de salud financiera.

    Es contrato con FinGrow-BE (`CompanyConcern`): que cuenta como cada una lo decide el backend.
    """

    LOW_SAVINGS = "low_savings"
    THIN_CUSHION = "thin_cushion"
    BUDGET_OVERRUNS = "budget_overruns"
    MISSED_GOAL_CONTRIBUTIONS = "missed_goal_contributions"


class ConcernSummary(BaseModel):
    concern: FinancialConcern
    affected_employees: int = Field(gt=0)
    evaluated_employees: int = Field(gt=0)
    percentage: Decimal = Field(ge=0, le=100)

    @model_validator(mode="after")
    def _affected_are_evaluated(self) -> "ConcernSummary":
        if self.affected_employees > self.evaluated_employees:
            raise ValueError("No puede haber mas afectados que evaluados.")

        return self


class CompanyRecommendationsRequest(BaseModel):
    language: Language = Language.ES
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="AAAA-MM del mes analizado.")
    measured_employees: int = Field(gt=0, description="Empleados con puntaje de salud financiera en el mes.")
    average_score: Decimal | None = Field(
        default=None, ge=0, le=100, description="Puntaje promedio de 0 a 100, si se puede mostrar."
    )
    participation_rate: Decimal | None = Field(
        default=None, ge=0, le=100, description="Porcentaje de empleados activos que usaron FinGrow."
    )
    concerns: list[ConcernSummary] = Field(default_factory=list, max_length=len(FinancialConcern))

    @model_validator(mode="after")
    def _concerns_are_consistent(self) -> "CompanyRecommendationsRequest":
        if len({summary.concern for summary in self.concerns}) != len(self.concerns):
            raise ValueError("Cada preocupacion puede venir una sola vez.")

        if any(summary.evaluated_employees > self.measured_employees for summary in self.concerns):
            raise ValueError("Una preocupacion no puede evaluar mas empleados que los medidos.")

        return self
