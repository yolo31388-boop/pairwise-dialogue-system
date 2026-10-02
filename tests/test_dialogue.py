"""对话剧情系统 - 红态测试"""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dialogue.system import DialogueSystem, DialogueNode

class TestDialogueCondition:
    def test_cannot_start_without_condition(self):
        ds = DialogueSystem()
        ds.nodes["d1"] = DialogueNode("d1", "test")
        result = ds.start_dialogue("d1", {"level": 1})
        assert result == False

class TestChoiceRecording:
    def test_choice_is_recorded(self):
        ds = DialogueSystem()
        ds.nodes["d1"] = DialogueNode("d1", "test", options=[{"next":"d2"},{"next":"d3"}])
        ds.select_option("d1", 1)
        assert len(ds.choices) == 1

class TestConditionCombination:
    def test_condition_supports_and(self):
        ds = DialogueSystem()
        cond = {"level": 10, "quest": "done"}
        player = {"level": 10, "quest": "done"}
        assert ds.check_condition(cond, player) == True

class TestItemReward:
    def test_item_reward_given(self):
        ds = DialogueSystem()
        player = {"inventory": []}
        ds.give_reward({"item": "sword"}, player)
        assert "sword" in player["inventory"]

class TestHistoryChoice:
    def test_history_saves_choice(self):
        ds = DialogueSystem()
        ds.save_history("d1", 2)
        assert ds.completed[-1] == "d1"
