"""Stone pack: calc_core — a real expression calculator engine.

Pure data: the mason loader builds Piece/Slot/Schematic objects from PACK.
Templates are stones (code with __H_<hole>__ chisel-points); each slot's
"request" is real code executed in place next to the stones already set.
Pipeline: text -> tokenize -> to_rpn (shunting-yard) -> eval_rpn -> calc().
"""

PACK = {
    "name": "calc",
    "pieces": {
        "tokenizer": {
            "shape": "lexer",
            "holes": ["OPS"],
            "template": """
def tokenize(text):
    ops = set('__H_OPS__')
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c in ops:
            tokens.append(c)
            i += 1
        elif c.isdigit() or c == '.':
            j = i
            dots = 0
            while j < n and (text[j].isdigit() or text[j] == '.'):
                if text[j] == '.':
                    dots += 1
                j += 1
            num = text[i:j]
            if dots > 1 or num == '.':
                raise ValueError('bad number: ' + num)
            tokens.append(float(num) if dots else int(num))
            i = j
        else:
            raise ValueError('bad character: ' + repr(c))
    return tokens
""",
        },
        "parser": {
            "shape": "shunting-yard",
            "holes": ["PREC"],
            "template": """
PRECEDENCE = __H_PREC__

def to_rpn(tokens):
    out = []
    stack = []
    for tok in tokens:
        if isinstance(tok, (int, float)):
            out.append(tok)
        elif tok in PRECEDENCE:
            while stack and stack[-1] != '(' and PRECEDENCE[stack[-1]] >= PRECEDENCE[tok]:
                out.append(stack.pop())
            stack.append(tok)
        elif tok == '(':
            stack.append(tok)
        elif tok == ')':
            while stack and stack[-1] != '(':
                out.append(stack.pop())
            if not stack:
                raise ValueError('unbalanced parentheses')
            stack.pop()
        else:
            raise ValueError('unknown token: ' + repr(tok))
    while stack:
        op = stack.pop()
        if op == '(':
            raise ValueError('unbalanced parentheses')
        out.append(op)
    return out
""",
        },
        "evaluator": {
            "shape": "rpn-machine",
            "template": """
def eval_rpn(rpn):
    stack = []
    for tok in rpn:
        if isinstance(tok, (int, float)):
            stack.append(tok)
            continue
        if len(stack) < 2:
            raise ValueError('malformed expression')
        b = stack.pop()
        a = stack.pop()
        if tok == '+':
            stack.append(a + b)
        elif tok == '-':
            stack.append(a - b)
        elif tok == '*':
            stack.append(a * b)
        elif tok == '/':
            if b == 0:
                raise ValueError('division by zero')
            stack.append(a / b)
        else:
            raise ValueError('unknown operator: ' + repr(tok))
    if len(stack) != 1:
        raise ValueError('malformed expression')
    return stack[0]
""",
        },
        "calculator": {
            "shape": "facade",
            "template": """
def calc(text):
    return eval_rpn(to_rpn(tokenize(text)))
""",
        },
    },
    # An "empty sphere" evaluator: same name and signature, but it never pops
    # the stack and always answers 0. The evaluator slot's request rejects it.
    "stubs": {
        "evaluator": {
            "shape": "rpn-machine",
            "template": """
def eval_rpn(rpn):
    stack = []
    for tok in rpn:
        stack.append(tok)
    return 0  # TODO: never reduces the stack, never divides, never raises
""",
        },
    },
    "schematics": {
        "calc_core": {
            "out": "calc_core.py",
            "slots": [
                {
                    "name": "tokenizer",
                    "piece": "tokenizer",
                    "fills": {"OPS": "+-*/()"},
                    "request": (
                        "assert tokenize('2+3*4') == [2, '+', 3, '*', 4]\n"
                        "assert tokenize('7-3') == [7, '-', 3], 'subtraction operator must tokenize'\n"
                        "assert tokenize(' (10 / 2.5) ') == ['(', 10, '/', 2.5, ')']\n"
                        "t = tokenize('3.5')\n"
                        "assert isinstance(t[0], float) and t[0] == 3.5\n"
                        "assert isinstance(tokenize('42')[0], int)\n"
                        "try:\n"
                        "    tokenize('2+$')\n"
                        "    raise AssertionError('garbage char must raise')\n"
                        "except ValueError:\n"
                        "    pass\n"
                        "try:\n"
                        "    tokenize('1.2.3')\n"
                        "    raise AssertionError('double dot must raise')\n"
                        "except ValueError:\n"
                        "    pass"
                    ),
                },
                {
                    "name": "parser",
                    "piece": "parser",
                    "fills": {"PREC": "{'+': 1, '-': 1, '*': 2, '/': 2}"},
                    "request": (
                        "assert to_rpn([2, '+', 3, '*', 4]) == [2, 3, 4, '*', '+']\n"
                        "assert to_rpn(['(', 2, '+', 3, ')', '*', 4]) == [2, 3, '+', 4, '*']\n"
                        "assert to_rpn([8, '-', 2, '-', 1]) == [8, 2, '-', 1, '-']\n"
                        "assert to_rpn([10, '/', 2]) == [10, 2, '/'], 'division operator must parse'\n"
                        "assert to_rpn(tokenize('1/2+3*4')) == [1, 2, '/', 3, 4, '*', '+']\n"
                        "assert to_rpn(tokenize('1+(2*(3+4))')) == [1, 2, 3, 4, '+', '*', '+']\n"
                        "try:\n"
                        "    to_rpn(['(', 2, '+', 3])\n"
                        "    raise AssertionError('unbalanced parens must raise')\n"
                        "except ValueError:\n"
                        "    pass"
                    ),
                },
                {
                    "name": "evaluator",
                    "piece": "evaluator",
                    "request": (
                        "assert eval_rpn([2, 3, '+']) == 5\n"
                        "assert eval_rpn([2, 3, 4, '*', '+']) == 14\n"
                        "assert eval_rpn([10, 4, '/']) == 2.5\n"
                        "assert eval_rpn([8, 2, '-', 1, '-']) == 5\n"
                        "try:\n"
                        "    eval_rpn([1, 0, '/'])\n"
                        "    raise AssertionError('division by zero must raise ValueError')\n"
                        "except ValueError:\n"
                        "    pass\n"
                        "# anti-cheat probe: random operands, exact arithmetic — no lookup table can pass\n"
                        "import random\n"
                        "for _ in range(10):\n"
                        "    a, b = random.randint(1, 99), random.randint(1, 99)\n"
                        "    assert eval_rpn([a, b, '+']) == a + b\n"
                        "    assert eval_rpn([a, b, '*']) == a * b\n"
                        "    assert eval_rpn([a, b, '-']) == a - b\n"
                        "    assert eval_rpn([a, b, '/']) == a / b"
                    ),
                },
                {
                    "name": "calculator",
                    "piece": "calculator",
                    "request": (
                        "assert calc('2+3*4') == 14\n" "assert calc('(2+3)*4') == 20\n" "assert calc('10/4') == 2.5"
                    ),
                },
            ],
            "integration": (
                "assert calc('2+3*4') == 14, calc('2+3*4')\n"
                "assert calc('(2+3)*4') == 20, calc('(2+3)*4')\n"
                "assert calc('10/4') == 2.5, calc('10/4')\n"
                "assert calc('((1+2)*(3+4))-1') == 20, calc('((1+2)*(3+4))-1')\n"
                "assert calc('2*(3+(4-1))') == 12\n"
                "assert calc('100 - 10 * 5') == 50\n"
                "assert calc('8-2-1') == 5, 'subtraction must be left-associative'\n"
                "assert calc('1.5*4') == 6.0\n"
                "assert calc('20/8') == 2.5\n"
                "try:\n"
                "    calc('1/0')\n"
                "    raise AssertionError('division by zero must raise ValueError')\n"
                "except ValueError:\n"
                "    pass\n"
                "try:\n"
                "    calc('2+$3')\n"
                "    raise AssertionError('garbage input must raise ValueError')\n"
                "except ValueError:\n"
                "    pass\n"
                "try:\n"
                "    calc('(1+2')\n"
                "    raise AssertionError('unbalanced parens must raise ValueError')\n"
                "except ValueError:\n"
                "    pass"
            ),
        },
    },
}
