"""Focused regressions for answer completion and math OCR routing.

The production module is a Windows Tk application, so extract only the pure
functions under test instead of importing its GUI and platform dependencies.
"""

import ast
import json
from pathlib import Path
import re
import typing
import unittest


SOURCE_PATH = Path(__file__).resolve().parents[1] / "TA_Grader.py"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def extracted_function(name, namespace):
    node = next(
        item for item in TREE.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name
    )
    module = ast.Module(body=[node], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(SOURCE_PATH), "exec"), namespace)
    return namespace[name]


_namespace = {"json": json, "re": re, "Any": typing.Any, "Optional": typing.Optional}
extract_answer = extracted_function("extract_answer", _namespace)
_namespace["extract_answer"] = extract_answer
clean_question_text = extracted_function("clean_question_text", _namespace)
assess_ocr_quality = extracted_function("assess_ocr_quality", _namespace)

llm_node = next(
    item for item in TREE.body
    if isinstance(item, ast.ClassDef) and item.name == "LLMClient"
)
completion_method = next(
    item for item in llm_node.body
    if isinstance(item, ast.FunctionDef) and item.name == "_complete_answer"
)
completion_class = ast.ClassDef(
    name="ExtractedLLMClient",
    bases=[],
    keywords=[],
    body=[completion_method],
    decorator_list=[],
)
completion_namespace = {"json": json, "re": re, "extract_answer": extract_answer}
exec(
    compile(
        ast.fix_missing_locations(ast.Module(body=[completion_class], type_ignores=[])),
        str(SOURCE_PATH),
        "exec",
    ),
    completion_namespace,
)
LLMClient = completion_namespace["ExtractedLLMClient"]


class AnswerCompletionTests(unittest.TestCase):
    def test_partial_json_answer_is_rejected(self):
        self.assertFalse(LLMClient._complete_answer('{"answer":"B) Four'))

    def test_complete_json_answer_is_accepted(self):
        self.assertTrue(LLMClient._complete_answer('{"answer":"B) Four"}'))

    def test_numeric_answer_is_accepted(self):
        self.assertTrue(LLMClient._complete_answer('{"answer":"7"}'))


class MathOcrRegressionTests(unittest.TestCase):
    def test_numeric_subtraction_line_break_is_preserved(self):
        question = "Evaluate 3-\n2."
        self.assertIn("3-\n2", clean_question_text(question))

    def test_rational_numbers_lesson_routes_to_vision(self):
        # High OCR confidence and complete option labels route to vision when math mode is opt-in enabled
        text = (
            "Rational Numbers: Which expression is equivalent to 3/4?\n"
            "A) 6/8\nB) 3/8\nC) 4/3\nD) 7/4"
        )
        usable, _reason = assess_ocr_quality(
            text,
            98.0,
            {"ocr_min_confidence": 75.0, "ocr_min_option_markers": 3, "enable_math_mode": True},
        )
        self.assertFalse(usable, "fraction math should trigger the vision-first path when math mode is enabled")

    def test_math_mode_disabled_by_default_keeps_text_ocr(self):
        text = (
            "Rational Numbers: Which expression is equivalent to 3/4?\n"
            "A) 6/8\nB) 3/8\nC) 4/3\nD) 7/4"
        )
        usable, _reason = assess_ocr_quality(
            text,
            98.0,
            {"ocr_min_confidence": 75.0, "ocr_min_option_markers": 3, "enable_math_mode": False},
        )
        self.assertTrue(usable, "text OCR should remain usable when math mode is turned off")

    def test_absolute_value_inequalities_lesson_routes_to_vision(self):
        text = (
            "5 — Absolute Value Inequalities\n"
            "LEARNING OBJECTIVE: Solve an absolute value inequality.\n"
            "Solve the following absolute value inequality:\n"
            "|2x+3| >= 5\n"
            "a) x <= -4 or x >= 1\n"
            "b) -4 < x < 1\n"
            "c) x <= -1 or x >= 4\n"
            "d) -1 <= x <= 4\n"
        )
        usable, reason = assess_ocr_quality(
            text,
            95.0,
            {"ocr_min_confidence": 75.0, "ocr_min_option_markers": 3, "enable_math_mode": True},
        )
        self.assertFalse(usable, "absolute value inequalities should trigger vision-first path")
        self.assertEqual(reason, "math notation requires visual verification")

    def test_arithmetic_sequence_routes_to_vision(self):
        text = (
            "1 — Introduction to Arithmetic Sequences\n"
            "If the formula for an arithmetic sequence is a_n = 11 + 6(n - 1), then what term is 107?\n"
            "a.) 18th term\n"
            "b.) 16th term\n"
            "c.) 15th term\n"
            "d.) 17th term\n"
        )
        usable, reason = assess_ocr_quality(
            text,
            95.0,
            {"ocr_min_confidence": 75.0, "ocr_min_option_markers": 3, "enable_math_mode": True},
        )
        self.assertFalse(usable, "arithmetic sequence should trigger vision-first path")
        self.assertEqual(reason, "math notation requires visual verification")


if __name__ == "__main__":
    unittest.main()
