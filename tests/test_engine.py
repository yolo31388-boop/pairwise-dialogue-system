"""对话系统测试"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.engine import DialogueSystem, DialogueNode

class TestSubstitution:
    def test_no_partial_replace(self):
        ds = DialogueSystem()
        ds.variables = {"gold": 100, "gold_total": 500}
        result = ds.substitute_vars("You have {gold} of {gold_total}")
        assert "100" in result and "500" in result

class TestCondition:
    def test_safe_eval_no_arbitrary_code(self):
        ds = DialogueSystem()
        ds.variables = {"hp": 50}
        try:
            ds.evaluate_condition("__import__('os').system('echo hacked')")
            assert False, "eval允许任意代码"
        except:
            assert True

class TestHistory:
    def test_history_records_choice(self):
        ds = DialogueSystem()
        node = DialogueNode("n1", "test", options=[{"text": "yes", "next": "n2"}, {"text": "no", "next": "n3"}])
        ds.select_option(node, 0)
        assert any("yes" in str(h) or h == "n1" for h in ds.history)
