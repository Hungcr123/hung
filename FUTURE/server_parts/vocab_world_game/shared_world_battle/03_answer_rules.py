def shared_world_battle_answer_matches(answer: object, expected: object) -> bool:
    typed = vocab_key(clean(answer))
    want = vocab_key(clean(expected))
    if not typed or not want:
        return False
    return typed == want or re.sub(r"[^a-z0-9]+", "", typed) == re.sub(r"[^a-z0-9]+", "", want)


def shared_world_battle_question_answer_matches(answer: object, question: object) -> bool:
    row = question if isinstance(question, dict) else {}
    kind = qm_city_training_normalize_question_kind(row.get("training_kind", row.get("kind", "")))
    expected = row.get("answer", "")
    if kind in {"translate_vi", "translate_vi_speech"}:
        threshold = float(row.get("accept_percent", 70 if kind == "translate_vi" else 60) or (70 if kind == "translate_vi" else 60))
        return qm_city_training_vietnamese_answer_matches(answer, expected, max(0.1, min(1.0, threshold / 100.0)))
    return shared_world_battle_answer_matches(answer, expected)


def qm_city_training_vietnamese_answer_token_rows(value: object = "") -> list[dict]:
    rows: list[dict] = []
    for token in re.findall(r"\w+", clean(value), flags=re.UNICODE):
        raw = clean(token)
        if not raw:
            continue
        text = unicodedata.normalize("NFD", raw.lower().replace("\u0111", "d").replace("\u0110", "d"))
        norm = "".join(ch for ch in text if not unicodedata.combining(ch))
        norm = re.sub(r"[^a-z0-9]+", "", norm)
        if norm:
            rows.append({"text": raw, "norm": norm})
    return rows


def qm_city_training_vietnamese_answer_tokens(value: object = "") -> list[str]:
    return [clean(row.get("norm", "")) for row in qm_city_training_vietnamese_answer_token_rows(value) if clean(row.get("norm", ""))]


def qm_city_training_vietnamese_answer_score(answer: object, expected: object, threshold: float = 0.70) -> dict:
    typed_rows = qm_city_training_vietnamese_answer_token_rows(answer)
    want_rows = qm_city_training_vietnamese_answer_token_rows(expected)
    typed = [clean(row.get("norm", "")) for row in typed_rows if clean(row.get("norm", ""))]
    want = [clean(row.get("norm", "")) for row in want_rows if clean(row.get("norm", ""))]
    if not typed or not want:
        return {
            "correct": False,
            "matched": 0,
            "typed": len(typed),
            "expected": len(want),
            "coverage": 0.0,
            "precision": 0.0,
            "percent": 0,
            "exact": False,
            "expected_tokens": [{"text": clean(row.get("text", "")), "status": "missing"} for row in want_rows],
            "typed_tokens": [{"text": clean(row.get("text", "")), "status": "wrong"} for row in typed_rows],
        }
    typed_counts = Counter(typed)
    want_counts = Counter(want)
    matched = sum((typed_counts & want_counts).values())
    coverage = matched / max(1, len(want))
    precision = matched / max(1, len(typed))
    exact = matched == len(want) == len(typed) and typed_counts == want_counts
    typed_remaining = Counter(typed)
    expected_tokens = []
    for row in want_rows:
        norm = clean(row.get("norm", ""))
        status = "missing"
        if norm and typed_remaining.get(norm, 0) > 0:
            status = "correct"
            typed_remaining[norm] -= 1
        expected_tokens.append({"text": clean(row.get("text", "")), "status": status})
    want_remaining = Counter(want)
    typed_tokens = []
    for row in typed_rows:
        norm = clean(row.get("norm", ""))
        status = "wrong"
        if norm and want_remaining.get(norm, 0) > 0:
            status = "correct"
            want_remaining[norm] -= 1
        typed_tokens.append({"text": clean(row.get("text", "")), "status": status})
    return {
        "correct": coverage >= max(0.1, min(1.0, float(threshold or 0.70))) and precision >= 0.45,
        "matched": matched,
        "typed": len(typed),
        "expected": len(want),
        "coverage": round(coverage, 4),
        "precision": round(precision, 4),
        "percent": int(round(min(coverage, precision) * 100)),
        "exact": exact,
        "expected_tokens": expected_tokens,
        "typed_tokens": typed_tokens,
    }


def qm_city_training_vietnamese_answer_matches(answer: object, expected: object, threshold: float = 0.70) -> bool:
    return bool(qm_city_training_vietnamese_answer_score(answer, expected, threshold).get("correct"))
