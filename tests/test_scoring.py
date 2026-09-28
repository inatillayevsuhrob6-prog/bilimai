from app.services.scoring import simple_match, local_evaluate


def test_simple_match():
    assert simple_match("Diskriminant", "diskriminant")
    assert not simple_match("hello", "world")


def test_local_evaluate_perfect():
    qs = [{"order_index": i, "correct_answer": f"ans{i}"} for i in range(1, 11)]
    ua = {i: f"ans{i}" for i in range(1, 11)}
    r = local_evaluate(qs, ua)
    assert r["score"] == 10
    assert r["percentage"] == 100.0
