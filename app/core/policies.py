from dataclasses import dataclass


@dataclass(frozen=True)
class SpendingPolicy:
    category: str
    limit: float
    description: str


DEFAULT_POLICY = SpendingPolicy(
    category="other",
    limit=1_000.0,
    description="General business expense limit",
)

SPENDING_POLICIES = {
    "travel": SpendingPolicy("travel", 5_000.0, "Business travel limit"),
    "meals": SpendingPolicy("meals", 500.0, "Business meals limit"),
    "accommodation": SpendingPolicy("accommodation", 3_000.0, "Accommodation limit"),
    "equipment": SpendingPolicy("equipment", 10_000.0, "Equipment purchase limit"),
    "training": SpendingPolicy("training", 2_500.0, "Training and development limit"),
    "other": DEFAULT_POLICY,
}


def get_spending_policy(category: str) -> SpendingPolicy:
    normalized = category.strip().lower()
    return SPENDING_POLICIES.get(normalized, DEFAULT_POLICY)


def evaluate_spending_policy(category: str, amount: float) -> tuple[bool, float, str]:
    policy = get_spending_policy(category)
    flagged = amount > policy.limit
    if flagged:
        reason = (
            f"{policy.category} expense exceeds the policy limit of "
            f"{policy.limit:.2f}"
        )
    else:
        reason = "Expense is within the category policy limit"
    return flagged, policy.limit, reason
