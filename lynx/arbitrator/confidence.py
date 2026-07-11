def confidence_tier(probability: float) -> str:
    if probability >= 0.85:
        return "HIGH"
    if probability >= 0.65:
        return "MEDIUM"
    if probability >= 0.45:
        return "LOW"
    return "UNCERTAIN"
