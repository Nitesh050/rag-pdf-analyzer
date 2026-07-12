from .detector import IntentDetector
from .intent import Intent


class IntentRouter:

    def __init__(self):
        self.detector = IntentDetector()

    def route(
        self,
        question: str,
    ) -> Intent:

        return self.detector.detect(question)