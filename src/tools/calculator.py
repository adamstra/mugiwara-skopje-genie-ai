import ast
import operator
import math

class SafeCalculator:
    """Safely evaluates mathematical expressions using AST to avoid LLM calculation errors."""

    # Allowed operators
    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    @classmethod
    def evaluate(cls, expression: str) -> float:
        """Evaluates a math expression string safely."""
        clean_expr = expression.strip().replace(",", "")
        try:
            tree = ast.parse(clean_expr, mode='eval')
            return cls._eval_node(tree.body)
        except Exception as e:
            raise ValueError(f"Cannot evaluate expression '{expression}': {e}")

    @classmethod
    def _eval_node(cls, node):
        if isinstance(node, ast.Constant):  # e.g. numbers
            return node.value
        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            op = cls._OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op)}")
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand)
            op = cls._OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op)}")
            return op(operand)
        elif isinstance(node, ast.Call):
            # Support basic math functions
            func_name = getattr(node.func, 'id', None)
            args = [cls._eval_node(arg) for arg in node.args]
            if func_name == "round":
                return round(*args)
            elif func_name == "abs":
                return abs(*args)
            elif func_name == "sum":
                return sum(args)
            elif func_name == "sqrt":
                return math.sqrt(args[0])
            raise ValueError(f"Unsupported function call: {func_name}")
        else:
            raise ValueError(f"Unsupported AST node: {type(node)}")
