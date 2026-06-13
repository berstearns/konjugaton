"""Application services: the use-case layer the UI talks to.

Services orchestrate domain + engine + state + settings. They contain no I/O of
their own beyond the learner-output logger, and no presentation logic.
"""

from __future__ import annotations

from konjugaton.services.catalog_service import AxisInfo, CatalogService
from konjugaton.services.grading import Grade, GradedResponse, Grader
from konjugaton.services.hints import generate_hint, rule_hint
from konjugaton.services.output import LearnerLogger, build_response_record
from konjugaton.services.practice import PracticeService, SessionOrder
from konjugaton.services.selection import selection_from_settings
from konjugaton.services.selfcheck import SelfCheckReport, run_selfcheck
from konjugaton.services.table_service import ConjugationTableService
from konjugaton.services.textdiff import char_diff, mistake_markup

__all__ = [
    "AxisInfo",
    "CatalogService",
    "ConjugationTableService",
    "Grade",
    "GradedResponse",
    "Grader",
    "LearnerLogger",
    "PracticeService",
    "SelfCheckReport",
    "SessionOrder",
    "build_response_record",
    "char_diff",
    "generate_hint",
    "mistake_markup",
    "rule_hint",
    "run_selfcheck",
    "selection_from_settings",
]
