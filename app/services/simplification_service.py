import time
import uuid
from typing import Tuple

from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.models.SimplificationResponse import SimplificationProgress
from app.utils.simplifier import Proofreader, LexNormalizer, ConnectivesSimplifier, \
    ExpressionsSimplifier, SentenceSplitter, NominalizationsSimplifier, VerbsSimplifier, SentenceReorganizer, Explainer


class SimplificationService:

    def __init__(self):
        self.proofreader = Proofreader()
        self.lex_normalizer = LexNormalizer()
        self.connectives_simplifier = ConnectivesSimplifier()
        self.expression_simplifier = ExpressionsSimplifier()
        self.sentences_simplifier = SentenceSplitter()
        self.nominalizations_simplifier = NominalizationsSimplifier()
        self.verbs_simplifier = VerbsSimplifier()
        self.sentence_reorganizer = SentenceReorganizer()
        self.explainer = Explainer()

        # Build workflow
        workflow = StateGraph(SimplificationProgress)

        # Add nodes
        workflow.add_node("proofreading_node", self.proofreader.simplify)
        workflow.add_node("lex_node", self.lex_normalizer.simplify)
        workflow.add_node("connectives_node", self.connectives_simplifier.simplify)
        workflow.add_node("expressions_node", self.expression_simplifier.simplify)
        workflow.add_node("sentence_splitter_node", self.sentences_simplifier.simplify)
        workflow.add_node("nominalizations_node", self.nominalizations_simplifier.simplify)
        workflow.add_node("verbs_node", self.verbs_simplifier.simplify)
        workflow.add_node("sentence_reorganizer_node", self.sentence_reorganizer.simplify)
        workflow.add_node("explain_node", self.explainer.simplify)

        # Add edges
        workflow.add_edge(START, "proofreading_node")
        workflow.add_edge("proofreading_node", "lex_node")
        workflow.add_edge("lex_node", "connectives_node")
        workflow.add_edge("connectives_node", "expressions_node")
        workflow.add_edge("expressions_node", "sentence_splitter_node")
        workflow.add_edge("sentence_splitter_node", "nominalizations_node")
        workflow.add_edge("nominalizations_node", "verbs_node")
        workflow.add_edge("verbs_node", "sentence_reorganizer_node")
        workflow.add_conditional_edges("sentence_reorganizer_node", lambda state: state.target == "common", {True: "explain_node", False: END})
        workflow.add_edge("explain_node", END)

        # Compile workflow
        self.chain = workflow.compile()

    def simplify(self, text: str, target: str) -> Tuple[str, SimplificationProgress]:
        request_id = uuid.uuid4().hex[:8]
        total_steps = 9 if target == "common" else 8

        progress = SimplificationProgress(request_id=request_id, target=target, original=text, total_steps=total_steps)

        print(f"[SIMPLIFY] request_id={request_id} started target={target} total_steps={total_steps}")
        start = time.monotonic()

        try:
            progress = self.chain.invoke(progress)
        except Exception as exc:
            elapsed = time.monotonic() - start
            completed = progress.current_step
            print(f"[SIMPLIFY] request_id={request_id} failed completed_steps={completed}/{total_steps} duration={elapsed:.2f}s error_type={type(exc).__name__}")
            raise

        elapsed = time.monotonic() - start
        completed_steps = progress.get("current_step", 0) if isinstance(progress, dict) else progress.current_step
        print(f"[SIMPLIFY] request_id={request_id} completed steps={completed_steps}/{total_steps} duration={elapsed:.2f}s")

        if target == "common":
            return progress["explain"], progress
        return progress["sentence_reorganizer"], progress
