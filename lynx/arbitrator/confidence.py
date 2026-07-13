from lynx.config import get_settings


def confidence_tier(probability: float) -> str:
    settings = get_settings()
    if probability >= settings.confidence_high_threshold:
        return "HIGH"
    if probability >= settings.confidence_medium_threshold:
        return "MEDIUM"
    if probability >= settings.confidence_low_threshold:
        return "LOW"
    return "UNCERTAIN"
