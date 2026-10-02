"""对话剧情系统 - 含5个bug"""
from dataclasses import dataclass, field

@dataclass
class DialogueNode:
    nid: str
    text: str
    options: list = field(default_factory=list)
    condition: dict = field(default_factory=dict)

class DialogueSystem:
    def __init__(self):
        self.nodes: dict[str, DialogueNode] = {}
        self.completed: list = []  # bug1: 不防重复
        self.choices: list = []  # bug2: 不记录选择

    def start_dialogue(self, nid: str, player: dict) -> bool:
        # bug1: 不检查条件，不防重复
        if nid in self.nodes:
            return True
        return False

    def select_option(self, nid: str, option_index: int) -> str:
        # bug2: 不记录选择，所有选项跳同一节点
        node = self.nodes.get(nid)
        if node and option_index < len(node.options):
            return node.options[0].get("next", "")
        return ""

    def check_condition(self, condition: dict, player: dict) -> bool:
        # bug3: 只看等级，不支持组合
        return player.get("level", 0) >= condition.get("level", 0)

    def give_reward(self, reward: dict, player: dict) -> bool:
        # bug4: 只给经验金币，不检查背包
        player["exp"] = player.get("exp", 0) + reward.get("exp", 0)
        return True

    def save_history(self, nid: str, choice: int) -> None:
        # bug5: 不保存选择
        self.completed.append(nid)
