"""对话系统 - 带7个bug"""
from dataclasses import dataclass, field

@dataclass
class DialogueNode:
    id: str
    text: str
    options: list = field(default_factory=list)
    condition: str = None

class DialogueSystem:
    def __init__(self):
        self.variables = {}
        self.history = []  # bug3: 不记录分支选择
        self.callbacks = []

    def evaluate_condition(self, condition):
        # bug5: 用eval
        return eval(condition, {}, self.variables)

    def show_options(self, node):
        # bug1: 条件只检查一次
        valid = []
        for opt in node.options:
            if opt.get("condition") is None or self.evaluate_condition(opt["condition"]):
                valid.append(opt)
        return valid

    def substitute_vars(self, text):
        # bug2: 朴素子串替换
        for key, val in self.variables.items():
            text = text.replace("{" + key + "}", str(val))
        return text

    def select_option(self, node, option_idx):
        opt = node.options[option_idx]
        self.history.append(node.id)  # bug3: 只记节点不记选择
        return opt.get("next")

    def on_dialogue_end(self, callback):
        # bug6: 不去重
        self.callbacks.append(callback)

    def end_dialogue(self):
        for cb in self.callbacks:
            cb()

    def skip(self):
        pass  # bug7: 不触发跳过事件
