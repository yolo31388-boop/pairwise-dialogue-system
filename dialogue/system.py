"""对话剧情系统"""
from dataclasses import dataclass, field

DEFAULT_INVENTORY_CAPACITY = 20

@dataclass
class DialogueNode:
    nid: str
    text: str
    options: list = field(default_factory=list)
    condition: dict = field(default_factory=dict)

class DialogueSystem:
    def __init__(self):
        self.nodes: dict[str, DialogueNode] = {}
        self.completed: list = []
        self.choices: list = []
        self.rewarded: set = set()
        self._history: list = []

    def start_dialogue(self, nid: str, player: dict) -> bool:
        node = self.nodes.get(nid)
        if node is None:
            return False
        if nid in self.completed:
            return False
        if not node.condition:
            return False
        return self.check_condition(node.condition, player)

    def select_option(self, nid: str, option_index: int) -> str:
        node = self.nodes.get(nid)
        if node is None or not (0 <= option_index < len(node.options)):
            return ""
        option = node.options[option_index]
        self.choices.append({"nid": nid, "option": option_index})
        return option.get("next", "")

    def check_condition(self, condition: dict, player: dict) -> bool:
        if not condition:
            return False
        if "and" in condition:
            return all(self.check_condition(c, player) for c in condition["and"])
        if "or" in condition:
            return any(self.check_condition(c, player) for c in condition["or"])
        if "not" in condition:
            return not self.check_condition(condition["not"], player)
        for key, expected in condition.items():
            if key == "level":
                if player.get("level", 0) < expected:
                    return False
            elif key == "item":
                items = expected if isinstance(expected, list) else [expected]
                inventory = player.get("inventory", [])
                if any(item not in inventory for item in items):
                    return False
            elif key == "quest":
                quests = expected if isinstance(expected, dict) else {expected: "done"}
                player_quests = player.get("quest", player.get("quests", {}))
                if isinstance(player_quests, dict):
                    if any(player_quests.get(q) != status for q, status in quests.items()):
                        return False
                elif player.get("quest") != expected:
                    return False
            else:
                if player.get(key) != expected:
                    return False
        return True

    def give_reward(self, reward: dict, player: dict) -> bool:
        reward_id = reward.get("id")
        if reward_id is not None:
            if reward_id in self.rewarded:
                return False
        items = reward.get("items", [])
        if "item" in reward:
            items = items + [reward["item"]]
        inventory = player.setdefault("inventory", [])
        capacity = player.get("inventory_capacity", DEFAULT_INVENTORY_CAPACITY)
        if len(inventory) + len(items) > capacity:
            return False
        player["exp"] = player.get("exp", 0) + reward.get("exp", 0)
        player["gold"] = player.get("gold", 0) + reward.get("gold", 0)
        inventory.extend(items)
        if reward_id is not None:
            self.rewarded.add(reward_id)
        return True

    def save_history(self, nid: str, choice: int) -> None:
        self.completed.append(nid)
        self.choices.append({"nid": nid, "option": choice})
        self._history.append((nid, choice))

    def rollback(self) -> bool:
        if not self._history:
            return False
        nid, choice = self._history.pop()
        if nid in self.completed:
            self.completed.remove(nid)
        entry = {"nid": nid, "option": choice}
        if entry in self.choices:
            self.choices.remove(entry)
        return True
