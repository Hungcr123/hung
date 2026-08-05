from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = (ROOT / "FUTURE/web/js_parts/17_vocab_to_pdf_bootstrap.js").read_text(encoding="utf-8")
CLIENT = (ROOT / "FUTURE/web/js_parts/19_pdf_speak_chrome.js").read_text(encoding="utf-8")
PAGE = (ROOT / "FUTURE/web/js_parts/20_pdf_page_progress.js").read_text(encoding="utf-8")


def function_slice(source: str, marker: str, next_marker: str, limit: int = 12000) -> str:
    start = source.index(marker)
    end = source.find(next_marker, start + len(marker))
    return source[start:end if end >= 0 else start + limit]


assert "var pdfAiQuestionAudioToken = 0;" in BOOTSTRAP
assert "var pdfAiQuestionFeedbackAudio = null;" in BOOTSTRAP
assert "var pdfAiNoticeAudioToken = 0;" in BOOTSTRAP

RETURN_TO_VAULT = function_slice(BOOTSTRAP, "const returnToServerFileSelection", "const retryCompletionSync")
assert RETURN_TO_VAULT.index("stopPdfAiAssistRuntimeAudio();") < RETURN_TO_VAULT.index("beginLessonExitGateTransition")
assert RETURN_TO_VAULT.index("resetPdfMode();") > RETURN_TO_VAULT.index('updateFutureAppRoute("lesson_vault"')

assert "const stopPdfAiQuestionRuntimeAudio" in CLIENT
assert "const stopPdfAiNoticeRuntimeAudio" in CLIENT
assert "const stopPdfAiAssistRuntimeAudio" in CLIENT
assert "window.__ftStopPdfAiAssistRuntimeAudio = stopPdfAiAssistRuntimeAudio" in CLIENT

QUESTION_GATE = function_slice(CLIENT, "const playPdfAiQuestionGateVoice", "const pdfAiQuestionAnimationOwnerKey")
assert "const requestToken = ++pdfAiQuestionAudioToken" in QUESTION_GATE
assert "requestToken !== pdfAiQuestionAudioToken || !pdfModeActive" in QUESTION_GATE

QUESTION_PATH = function_slice(CLIENT, "const playPdfAiQuestionAudioPath", "const playPdfAiQuestionAnswerAudio")
assert "!pdfModeActive" in QUESTION_PATH
assert "expectedToken !== pdfAiQuestionAudioToken" in QUESTION_PATH

FEEDBACK = function_slice(CLIENT, "const playPdfAiQuestionFeedbackFx", "const playPdfAiQuestionGeneratedFeedbackVoice")
assert "pdfAiQuestionFeedbackAudio = audio" in FEEDBACK
assert 'audio.addEventListener("ended", release' in FEEDBACK

GENERATED = function_slice(CLIENT, "const playPdfAiQuestionGeneratedFeedbackVoice", "const renderPdfAiQuestion")
assert "scheduledToken !== pdfAiQuestionAudioToken" in GENERATED

NOTICE = function_slice(CLIENT, "const playPdfAiNoticeVoice", "const pausePdfAiNoticeFireball")
assert "!pdfModeActive" in NOTICE
assert "repairToken === pdfAiNoticeAudioToken" in NOTICE
assert "playToken === pdfAiNoticeAudioToken" in NOTICE
assert 'fetchAuthJson("/space-pdf/ai-region-notices?client_source=pdf_ai_notice_audio_repair"' in CLIENT
assert 'fetchAuthJson("/pdf/speak?client_source=pdf_speak"' in CLIENT

RESET = function_slice(CLIENT, "const resetPdfMode", "const enterPdfMode")
assert RESET.index("stopPdfAiAssistRuntimeAudio();") < RESET.index("hidePdfAiNoticeFireball")

PAGE_CHANGE = function_slice(PAGE, "const pdfGoToPage", "const pdfCanvasPoint")
assert PAGE_CHANGE.index("stopPdfAiAssistRuntimeAudio();") < PAGE_CHANGE.index("pdfPendingPage = page")

LOCAL_IMAGE = function_slice(CLIENT, "const openPdfLocalImageSlot", "const pdfPinnedRegionsStorageKey")
assert LOCAL_IMAGE.count("stopPdfAiAssistRuntimeAudio();") >= 2

print("pdf_ai_audio_navigation_contract=ok notice=true question=true delayed_fence=true page=true exit=true")
