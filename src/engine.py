"""对话系统"""
import ast
import operator
import re
from dataclasses import dataclass, field


@dataclass
class DialogueNode:
    id: str
    text: str
    options: list = field(default_factory=list)
    condition: str = None


_COMPARE_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}

_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _eval_condition_node(node, variables):
    """白名单求值：只允许常量、变量查找、比较/布尔/算术运算。"""
    if isinstance(node, ast.Expression):
        return _eval_condition_node(node.body, variables)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (bool, int, float, str)):
            return node.value
        raise ValueError(f"不允许的常量: {node.value!r}")
    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise NameError(f"未定义的变量: {node.id}")
        return variables[node.id]
    if isinstance(node, ast.BoolOp):
        values = [_eval_condition_node(v, variables) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
        raise ValueError(f"不允许的布尔运算: {type(node.op).__name__}")
    if isinstance(node, ast.UnaryOp):
        operand = _eval_condition_node(node.operand, variables)
        if isinstance(node.op, ast.Not):
            return not operand
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        raise ValueError(f"不允许的一元运算: {type(node.op).__name__}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_condition_node(node.left, variables)
        right = _eval_condition_node(node.right, variables)
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.Compare):
        left = _eval_condition_node(node.left, variables)
        for op, comparator in zip(node.ops, node.comparators):
            op_type = type(op)
            if op_type not in _COMPARE_OPS:
                raise ValueError(f"不允许的比较运算: {op_type.__name__}")
            right = _eval_condition_node(comparator, variables)
            if not _COMPARE_OPS[op_type](left, right):
                return False
            left = right
        return True
    raise ValueError(f"条件表达式包含不允许的语法: {type(node).__name__}")


class DialogueSystem:
    INDENT_STEP = 2

    def __init__(self):
        self.variables = {}
        self.history = []
        self.callbacks = []
        self.ended = False
        self.skipped = False

    def evaluate_condition(self, condition):
        tree = ast.parse(condition, mode="eval")
        return bool(_eval_condition_node(tree, self.variables))

    def show_options(self, node):
        # 每次显示前都重新评估条件，不缓存结果
        valid = []
        for opt in node.options:
            if opt.get("condition") is None or self.evaluate_condition(opt["condition"]):
                valid.append(opt)
        return valid

    def substitute_vars(self, text):
        # 按占位符整体解析，未知占位符原样保留
        return _PLACEHOLDER_RE.sub(
            lambda m: str(self.variables[m.group(1)])
            if m.group(1) in self.variables
            else m.group(0),
            text,
        )

    def select_option(self, node, option_idx):
        opt = node.options[option_idx]
        condition = opt.get("condition")
        if condition is not None and not self.evaluate_condition(condition):
            raise ValueError(f"选项条件已不满足: {condition}")
        self.history.append({
            "node_id": node.id,
            "choice_index": option_idx,
            "choice_text": opt.get("text"),
            "variables": dict(self.variables),
        })
        return opt.get("next")

    def render_options(self, node, depth=0, width=40, scroll_offset=0, max_visible=None):
        """相对布局缩进（按宽度钳制）+ 滚动窗口，深层嵌套不溢出。"""
        options = self.show_options(node)
        indent = " " * min(depth * self.INDENT_STEP, max(width - 4, 0))
        lines = []
        for opt in options:
            line = indent + self.substitute_vars(str(opt.get("text", "")))
            if len(line) > width:
                line = line[: width - 1] + "…"
            lines.append(line)
        if max_visible is None:
            return lines[scroll_offset:]
        return lines[scroll_offset: scroll_offset + max_visible]

    def on_dialogue_end(self, callback):
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def end_dialogue(self):
        if self.ended:
            return
        self.ended = True
        for cb in list(self.callbacks):
            cb()

    def skip(self):
        # 跳过触发与正常结束相同的完成事件，并标记为跳过
        self.skipped = True
        self.end_dialogue()

    def reset(self):
        self.ended = False
        self.skipped = False
