from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import Currency, ExpenseCategory, Language

MAX_MONTHS = 48
MAX_GOALS = 20
MAX_GOAL_NAME_LENGTH = 150
RECOMMENDATION_COUNT = 3
MAX_TITLE_LENGTH = 80
MAX_BODY_LENGTH = 320


class RecommendationKind(StrEnum):
    POSITIVE = "positive"
    WARNING = "warning"
    TIP = "tip"


class RecommendationAction(StrEnum):
    BUDGETS = "budgets"
    GOALS = "goals"
    TRANSACTIONS = "transactions"
    EDUCATION = "education"
    NONE = "none"


class GoalStatus(StrEnum):
    ACTIVE = "active"
    ACHIEVED = "achieved"


class CategoryAmount(BaseModel):
    category: ExpenseCategory
    amount: Decimal = Field(ge=0)


class MonthSummary(BaseModel):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="AAAA-MM.")
    is_reference: bool = Field(
        default=False,
        description="True si el mes es anterior al periodo elegido y solo sirve para comparar.",
    )
    income: Decimal = Field(ge=0)
    expenses: Decimal = Field(ge=0)
    savings: Decimal = Field(description="Ingresos menos gastos, contando ahorro_inversion como ahorro.")
    expenses_by_category: list[CategoryAmount] = Field(default_factory=list, max_length=len(ExpenseCategory))


class BudgetLimit(BaseModel):
    category: ExpenseCategory
    limit: Decimal = Field(gt=0)
    spent: Decimal = Field(ge=0)


class GoalSummary(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_GOAL_NAME_LENGTH)
    status: GoalStatus
    target_amount: Decimal = Field(gt=0)
    current_amount: Decimal = Field(ge=0)
    monthly_commitment: Decimal = Field(ge=0)
    deadline: date


class RecommendationsRequest(BaseModel):
    language: Language = Language.ES
    currency: Currency
    period_start: date
    period_end: date
    months: list[MonthSummary] = Field(min_length=1, max_length=MAX_MONTHS)
    budget_limits: list[BudgetLimit] = Field(default_factory=list, max_length=len(ExpenseCategory))
    goals: list[GoalSummary] = Field(default_factory=list, max_length=MAX_GOALS)

    @model_validator(mode="after")
    def _period_is_ordered(self) -> "RecommendationsRequest":
        if self.period_end < self.period_start:
            raise ValueError("El fin del periodo no puede ser anterior al inicio.")

        return self


class Recommendation(BaseModel):
    kind: RecommendationKind
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    body: str = Field(min_length=1, max_length=MAX_BODY_LENGTH)
    action: RecommendationAction


class RecommendationsResponse(BaseModel):
    recommendations: list[Recommendation] = Field(min_length=1, max_length=RECOMMENDATION_COUNT)
    model: str = Field(description="Modelo que produjo el resultado, para trazabilidad.")
