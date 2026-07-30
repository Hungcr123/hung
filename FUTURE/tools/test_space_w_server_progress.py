import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from FUTURE import server_app as app


def make_record(node_count: int, node_index: int, **state_values) -> dict:
    state = {
        "nodeCount": node_count,
        "index": node_index,
        "activeRun": True,
        "runId": "run-new",
        "savedAt": "2026-07-19T10:00:00Z",
        **state_values,
    }
    return {
        "nodeCount": node_count,
        "nodeIndex": node_index,
        "runId": "run-new",
        "savedAt": "2026-07-19T10:00:00Z",
        "updatedAt": "2026-07-19T10:00:00Z",
        "completedRuns": 1,
        "state": state,
    }


active = make_record(2, 0)
active["state"].update({"rootNodeCount": 2, "sentenceCount": 4, "normalSentenceCount": 2, "trainSentenceCount": 2})
assert app.space_w_progress_work_counts(active) == (0, 4)
active_summary = app.build_lesson_progress_summary(active, "Space_W")
assert (active_summary["done"], active_summary["total"], active_summary["percent"]) == (0, 4, 0)
assert active_summary["completed"] is False
assert active_summary["previously_completed"] is True
assert active_summary["runId"] == "run-new"
assert active_summary["root_node_total"] == 2
assert (active_summary["sentenceCount"], active_summary["normalSentenceCount"], active_summary["trainSentenceCount"]) == (4, 2, 2)

sentence_breakdown = app.lesson_payload_sentence_breakdown({
    "k": "ftg",
    "n": [
        {"q": "A", "e": "A", "xp": [{"q": "A1", "e": "A1"}, {"q": "A2", "e": "A2"}]},
        {"q": "B", "e": "B"},
    ],
})
assert sentence_breakdown == {"sentences": 5, "normal_sentences": 2, "train_sentences": 3}

review = make_record(2, 1, reviewing=True, reviewModeActive=True, reviewMastered=[0])
assert app.space_w_progress_work_counts(review) == (3, 4)

# A finished root pass is only stage 1; it must not create a lifetime run.
stage_one = make_record(
    2,
    1,
    nodeProgress={
        "0": {"nextPanelCanShow": True, "speakStepCompleted": True},
        "1": {"nextPanelCanShow": True, "speakStepCompleted": True},
    },
)
stage_one.pop("completedRuns", None)
assert app.server_database_progress_completion_summary(stage_one, "Space_W")["current_run_complete"] is False
assert app.space_progress_completion_marker(stage_one, "Space_W") is False

stage_two_complete = make_record(2, 1, activeRun=False, reviewFinished=True)
assert app.server_database_progress_completion_summary(stage_two_complete, "Space_W")["current_run_complete"] is True

trained = make_record(5, 2, spaceWTrainModeExpanded=True)
assert app.space_w_progress_work_counts(trained) == (2, 10)

complete = make_record(5, 4, activeRun=False, reviewFinished=True)
assert app.space_w_progress_work_counts(complete) == (10, 10)

print("space_w_server_progress=ok stage1_not_complete review_same_run stage2_complete new=0/4 review=3/4 train=2/10")
