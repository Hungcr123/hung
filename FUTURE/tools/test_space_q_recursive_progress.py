import ast
from pathlib import Path


SOURCE = Path(__file__).parents[1] / "server_parts" / "server_data_pdf_qmdict" / "02_lesson_study_progress.py"


def load_functions():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    names = {
        "lesson_payload_guidance_node_count",
        "lesson_payload_question_breakdown",
        "lesson_payload_question_count",
        "lesson_payload_direct_question_count",
        "lesson_payload_question_total_count",
    }
    body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"clean": lambda value: str(value or "").strip()}
    exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])), str(SOURCE), "exec"), namespace)
    return namespace


def main():
    funcs = load_functions()
    payload = {
        "k": "ftq",
        "n": [
            {"cards": {"questions": [
                {"question": "q1", "guidance_tree": {"items": [
                    {"text": "a", "children": [{"title": "1"}, {"title": "2"}, {"title": "3"}]},
                    {"text": "b", "children": [{"title": "1"}, {"title": "2"}, {"title": "3"}]},
                ]}},
                {"question": "q2", "guidance_tree": {"items": [
                    {"text": "a", "children": [{"title": "1"}, {"title": "2"}, {"title": "3"}]},
                    {"text": "b", "children": [{"title": "1"}, {"title": "2"}]},
                ]}},
            ]}},
            {"cards": {"questions": [{"question": "q3"}]}},
        ],
    }
    breakdown = funcs["lesson_payload_question_breakdown"](payload)
    assert breakdown == {"topics": 2, "direct": 3, "recursive": 18, "total": 20}, breakdown
    assert funcs["lesson_payload_direct_question_count"](payload) == 3
    assert funcs["lesson_payload_question_count"](payload) == 18
    assert funcs["lesson_payload_question_total_count"](payload) == 20
    print("space_q_recursive_progress=ok topics=2 questions=3 recursive=18 total=20")


if __name__ == "__main__":
    main()
