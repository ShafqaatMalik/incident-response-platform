def dedupe_evidence(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
