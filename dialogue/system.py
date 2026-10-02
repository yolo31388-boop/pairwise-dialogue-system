"""对话剧情系统"""
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
        self.completed: list = []
        self.choices: list = []
        self.history: list = []
        self.rewarded: set = set()
        self.current: str | None = None

    # ------------------------------------------------------------------
    # 对话开始：检查条件 + 防重复
    # ------------------------------------------------------------------
    def start_dialogue(self, nid: str, player: dict) -> bool:
        node = self.nodes.get(nid)
        if node is None:
            return False
        if nid in self.completed:
            return False
        if not node.condition:
            return False
        if not self.check_condition(node.condition, player):
            return False
        self.current = nid
        return True

    def is_completed(self, nid: str) -> bool:
        return nid in self.completed

    # ------------------------------------------------------------------
    # 选项：跳转到各自节点并记录选择
    # ------------------------------------------------------------------
    def select_option(self, nid: str, option_index: int) -> str:
        node = self.nodes.get(nid)
        if node is None or not isinstance(option_index, int):
            return ""
        if option_index < 0 or option_index >= len(node.options):
            return ""
        option = node.options[option_index]
        next_nid = option.get("next", "")
        self.choices.append(
            {"nid": nid, "option": option_index, "next": next_nid}
        )
        return next_nid

    def get_choice(self, nid: str):
        for record in reversed(self.choices):
            if record["nid"] == nid:
                return record["option"]
        return None

    # ------------------------------------------------------------------
    # 条件：等级 / 任务 / 物品 / 属性 / 选择，支持 and / or / not 组合
    # ------------------------------------------------------------------
    def check_condition(self, condition, player: dict) -> bool:
        if not condition:
            return False
        if isinstance(condition, list):
            return all(self.check_condition(c, player) for c in condition)
        if not isinstance(condition, dict):
            return bool(condition)

        if "and" in condition:
            return all(self.check_condition(c, player) for c in condition["and"])
        if "or" in condition:
            return any(self.check_condition(c, player) for c in condition["or"])
        if "not" in condition:
            return not self.check_condition(condition["not"], player)

        for key, expected in condition.items():
            if key == "quest_status":
                continue
            if not self._check_single(key, expected, condition, player):
                return False
        return True

    def _check_single(self, key, expected, condition, player):
        if key == "level":
            return player.get("level", 0) >= expected
        if key in ("item", "has_item"):
            return self._has_item(player, expected)
        if key == "items":
            names = expected if isinstance(expected, (list, tuple)) else [expected]
            return all(self._has_item(player, name) for name in names)
        if key == "quest":
            return self._quest_ok(expected, condition.get("quest_status"), player)
        if key in ("choice", "chose"):
            required = expected if isinstance(expected, dict) else {}
            return all(self.get_choice(nid) == idx for nid, idx in required.items())
        if key in ("attr", "attrs", "attributes") and isinstance(expected, dict):
            attrs = player.get("attributes", player.get("attrs", {}))
            for name, value in expected.items():
                if not self._compare(attrs.get(name, player.get(name)), value):
                    return False
            return True
        return self._compare(player.get(key), expected)

    @staticmethod
    def _compare(actual, expected) -> bool:
        if actual is None:
            return False
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            return isinstance(actual, (int, float)) and actual >= expected
        if isinstance(expected, (list, tuple, set)):
            return actual in expected
        return actual == expected

    @staticmethod
    def _has_item(player, item_name) -> bool:
        for entry in player.get("inventory", []):
            if isinstance(entry, str):
                if entry == item_name:
                    return True
            elif isinstance(entry, dict):
                name = entry.get("name") or entry.get("item") or entry.get("id")
                if name == item_name:
                    return True
        return False

    @staticmethod
    def _quest_ok(quest, status, player) -> bool:
        quests = player.get("quests", {})
        current = quests.get(quest)
        if current is None and player.get("quest") == quest:
            current = quest
        if status is not None:
            return current == status
        return current is not None and current not in (
            "locked", "not_started", "unavailable",
        )

    # ------------------------------------------------------------------
    # 奖励：经验 / 金币 / 物品，检查背包空间，防重复
    # ------------------------------------------------------------------
    def give_reward(self, reward: dict, player: dict, nid: str | None = None) -> bool:
        if not reward:
            return False
        if nid is not None and nid in self.rewarded:
            return False

        wanted = self._reward_items(reward)
        inventory = player.setdefault("inventory", [])
        capacity = self._capacity(player)
        if capacity is not None:
            stack_names = {
                entry.get("name") or entry.get("item") or entry.get("id")
                for entry in inventory
                if isinstance(entry, dict)
                and any(k in entry for k in ("count", "qty", "amount"))
            }
            extra_slots = sum(
                qty if name not in stack_names else 0 for name, qty in wanted
            )
            if len(inventory) + extra_slots > capacity:
                return False

        player["exp"] = player.get("exp", 0) + reward.get("exp", 0)
        gold = reward.get("gold", reward.get("coins", reward.get("money", 0)))
        if gold:
            player["gold"] = player.get("gold", 0) + gold
        for name, qty in wanted:
            self._add_item(inventory, name, qty)

        if nid is not None:
            self.rewarded.add(nid)
        return True

    @staticmethod
    def _capacity(player):
        for key in (
            "capacity", "inventory_capacity", "max_inventory",
            "bag_capacity", "inventory_limit",
        ):
            if key in player:
                return player[key]
        return None

    @staticmethod
    def _reward_items(reward):
        items = []
        if reward.get("item"):
            items.append((reward["item"], 1))
        raw = reward.get("items")
        if isinstance(raw, dict):
            items.extend((name, qty) for name, qty in raw.items())
        elif isinstance(raw, list):
            for entry in raw:
                if isinstance(entry, str):
                    items.append((entry, 1))
                else:
                    items.append((
                        entry.get("name") or entry.get("item") or entry.get("id"),
                        entry.get("count", entry.get("qty", 1)),
                    ))
        return items

    @staticmethod
    def _add_item(inventory, name, qty):
        for entry in inventory:
            if isinstance(entry, dict):
                entry_name = entry.get("name") or entry.get("item") or entry.get("id")
                if entry_name == name:
                    count_key = next(
                        (k for k in ("count", "qty", "amount") if k in entry), None
                    )
                    if count_key is not None:
                        entry[count_key] += qty
                        return
        for _ in range(qty):
            inventory.append(name)

    # ------------------------------------------------------------------
    # 历史：保存选择 + 支持回滚重选
    # ------------------------------------------------------------------
    def save_history(self, nid: str, choice: int) -> None:
        self.history.append({"nid": nid, "choice": choice})
        if nid not in self.completed:
            self.completed.append(nid)

    def rollback(self, nid: str | None = None) -> bool:
        if not self.history:
            return False
        if nid is None:
            record = self.history.pop()
        else:
            for index in range(len(self.history) - 1, -1, -1):
                if self.history[index]["nid"] == nid:
                    record = self.history.pop(index)
                    break
            else:
                return False

        target = record["nid"]
        for index in range(len(self.choices) - 1, -1, -1):
            if self.choices[index]["nid"] == target:
                del self.choices[index]
                break

        if not any(item["nid"] == target for item in self.history):
            if target in self.completed:
                self.completed.remove(target)
            self.rewarded.discard(target)
        if self.current == target:
            self.current = None
        return True

    undo = rollback
