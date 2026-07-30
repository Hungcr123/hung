from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


APP_DIR = Path(r"C:\programe\write_html")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Future Question .Space_Q file from a JSON spec.")
    parser.add_argument("--spec", required=True, help="Path to the Space_Q JSON spec.")
    parser.add_argument("--output", required=True, help="Output .Space_Q path.")
    args = parser.parse_args()

    sys.path.insert(0, str(APP_DIR))
    import future_question_builder_gui as q  # noqa: WPS433

    spec_path = Path(args.spec)
    output_path = Path(args.output)
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    nodes = spec.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise SystemExit("Spec must contain a non-empty nodes list.")

    logs: list[str] = []
    worker = q.BuildQuestionWorker(
        nodes=nodes,
        title=str(spec.get("title") or output_path.stem),
        order=str(spec.get("order") or "sequence"),
        output_path=output_path,
        direct_payload=bool(spec.get("direct_payload", False)),
        reward_config=spec.get("rewards") if isinstance(spec.get("rewards"), dict) else None,
    )
    worker.log_message.connect(lambda message: logs.append(str(message)))
    failures: list[str] = []
    finished: list[tuple[str, int]] = []
    worker.failed.connect(lambda message: failures.append(str(message)))
    worker.finished_ok.connect(lambda path, count: finished.append((str(path), int(count))))
    worker.run()
    if logs:
        print("\n".join(logs))
    if failures:
        raise SystemExit(failures[-1])
    if not finished:
        raise SystemExit("Build did not report success.")

    payload = q.decode_space_q_payload(output_path)
    built_nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    total_questions = sum(
        len((node.get("cards") if isinstance(node, dict) else {}).get("questions", []) or [])
        for node in built_nodes
        if isinstance(node, dict)
    )
    audio_cards = sum(
        1
        for node in built_nodes
        if isinstance(node, dict)
        and isinstance(node.get("cards"), dict)
        and isinstance(node["cards"].get("audio"), dict)
    )
    print(f"BUILT={finished[-1][0]}")
    print(f"NODES={len(built_nodes)}")
    print(f"QUESTIONS={total_questions}")
    print(f"AUDIO_CARDS={audio_cards}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
