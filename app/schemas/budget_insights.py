from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import Currency, ExpenseCategory, Language
from app.schemas.financial_insights import CategoryAmount

MAX_BUDGET_MONTHS = 12


class BudgetCategoryUsage(BaseModel):
    category: ExpenseCategory
    limit: Decimal = Field(gt=0)
    spent: Decimal = Field(ge=0)


class BudgetMonth(BaseModel):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="AAAA-MM.")
    is_current: bool = Field(
        default=False,
        description="True si es el mes en curso: lo gastado todavia no es el total del mes.",
    )
    limits: list[BudgetCategoryUsage] = Field(min_length=1, max_length=len(ExpenseCategory))
    unbudgeted_expenses: list[CategoryAmount] = Field(
        default_factory=list,
        max_length=len(ExpenseCategory),
        description="Gasto del mes en categorias que no tienen tope en el presupuesto.",
    )


class BudgetRecommendationsRequest(BaseModel):
    language: Language = Language.ES
    currency: Currency
    months: list[BudgetMonth] = Field(min_length=1, max_length=MAX_BUDGET_MONTHS)

    @model_validator(mode="after")
    def _months_are_unique(self) -> "BudgetRecommendationsRequest":
        if len({month.month for month in self.months}) != len(self.months):
            raise ValueError("Cada mes puede venir una sola vez.")

        if sum(month.is_current for month in self.months) > 1:
            raise ValueError("Solo un mes puede ser el mes en curso.")

        return self
