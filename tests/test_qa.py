from __future__ import annotations

from app.qa import evaluate_spoken_answer, parse_qa_note


def test_parse_qa_note():
    sample_text = """
Questions & Answers

Specialization and Trade
Division of Labor & Self-Sufficiency
Question: How does the division of labor increase productivity, and why does Adam Smith argue that self-sufficiency leads to economic inefficiency?

Key Points:
Definition of Specialization: How dividing production tasks allows individuals to focus on what they do best.
Real-World Examples: The assembly line model like a pizza restaurant.
The Problem with Self-Sufficiency: What happens if one person had to do everything alone.

Comparative Advantage vs. Absolute Advantage
Question: If a country can produce more of every product than its neighbor, why is it beneficial to trade?

Key Concepts to Cover:
Absolute vs. Comparative Advantage: Define absolute advantage versus comparative advantage.
Opportunity Cost Mechanism: Walk through an example to show opportunity cost.
Mutually Beneficial Exchange: Explain how trading leaves both parties with more goods.
"""
    questions = parse_qa_note(sample_text)
    assert len(questions) == 2
    assert questions[0]["topic"] == "Specialization and Trade"
    assert questions[0]["subtopic"] == "Division of Labor & Self-Sufficiency"
    assert "division of labor increase productivity" in questions[0]["question"]
    assert len(questions[0]["key_points"]) == 3
    assert questions[0]["key_points"][0]["title"] == "Definition of Specialization"

    assert questions[1]["subtopic"] == "Comparative Advantage vs. Absolute Advantage"
    assert len(questions[1]["key_points"]) == 3


def test_evaluate_spoken_answer():
    question = {
        "id": "q1",
        "question": "How does specialization increase productivity?",
        "key_points": [
            {"title": "Division of Labor", "description": "Dividing production tasks allows workers to focus on what they do best."},
            {"title": "Assembly Line Example", "description": "Like in a pizza restaurant or car manufacturing."},
            {"title": "Self-Sufficiency Problem", "description": "One person cannot make everything efficiently."},
        ],
    }

    spoken = (
        "Specialization works by dividing production tasks so workers can focus on what they do best, "
        "like on an assembly line. When individuals attempt self-sufficiency, they cannot make everything efficiently."
    )

    eval_result = evaluate_spoken_answer(question, spoken, duration_sec=12.0)
    assert eval_result["coverage_pct"] >= 75
    assert eval_result["word_count"] > 15
    assert eval_result["wpm"] > 100
    assert eval_result["covered_count"] >= 2


def test_speaking_api_endpoints():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res = client.get("/api/speaking/qa")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    res_s = client.get("/api/speaking/sentences")
    assert res_s.status_code == 200
    assert isinstance(res_s.json(), list)
