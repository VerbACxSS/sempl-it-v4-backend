import time

from italian_ats_evaluator import TextAnalyzer, SimplificationAnalyzer
from italian_ats_evaluator.models.SimplificationEvaluation import SimplificationEvaluation
from italian_ats_evaluator.models.TextEvaluation import TextEvaluation


class AnalysisService:
    def __init__(self):
        self.text_analyzer = TextAnalyzer()
        self.simplification_analyzer = SimplificationAnalyzer()

    def do_text_analysis(self, text: str, request_id: str | None = None) -> TextEvaluation:
        started = time.monotonic()
        result = self.text_analyzer.analyze(text)
        request_id_text = f" request_id={request_id}" if request_id is not None else ""
        print(
            f"[LOCAL_ANALYSIS]{request_id_text} operation=text_analysis "
            f"completed duration={time.monotonic() - started:.2f}s"
        )
        return result

    def do_text_comparison(self, text1: str, text2: str, request_id: str | None = None) -> SimplificationEvaluation:
        started = time.monotonic()
        result = self.simplification_analyzer.analyze(text1, text2)
        request_id_text = f" request_id={request_id}" if request_id is not None else ""
        print(
            f"[LOCAL_ANALYSIS]{request_id_text} operation=text_comparison "
            f"completed duration={time.monotonic() - started:.2f}s"
        )
        return result
