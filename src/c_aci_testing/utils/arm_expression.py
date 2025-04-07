#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from typing import Any, List, Callable
import json

"""
This is a bit complicated and also not fully correct (it does not handle escape
sequences in strings, does not handle member functions like
storageAccount.listKeys()), etc.  But for us it's good enough, and crucially,
easy to add more functions to should the need arise in the future.

I have attempted to find a Python implementation of the ARM expression parser,
but did not find anything satisfactory.  There is an official C# implementation
tho.
"""

debug = False

def evaluate_expr(expr: str, _handle_func: Callable[[str, List[Any]], Any]) -> Any:
    """
    For simplicity, we assume expressions are of the form:
        functionName '(' arg ',' arg ',' ... ')' [ '.' property '.' property ... ] |
        \' string \' |
        number |
        true | false | null
    i.e. no things like func(a, b).member_func(c, d) or a.func()
    We also assume strings never contains ' in them
    """

    orig_expr = expr

    expr = expr.strip()

    try:
        if expr.startswith("'") and expr.endswith("'"):
            return expr[1:-1]
        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]
        if expr == "true":
            return True
        if expr == "false":
            return False
        if expr == "null":
            return None
        if expr.isdigit():
            return int(expr)

        def _find_next_unenclosed(
            s: str, start: int, char: str, open_chars: str, close_chars: str, pair_chars: str
        ) -> int:
            """
            Find the next occurrence of char in s, starting from start, that is
            not enclosed in any pair of (open_chars, close_chars), ignoring occurrence within pair_chars.

            Example:
                _find_next_unenclosed("a(b(c,'d))',e),f), g", 1, "), "(", ")", "'") == 16
            """
            depth = 0
            pair_opened = False
            for i in range(start, len(s)):
                if s[i] == char and depth == 0 and not pair_opened:
                    return i
                elif s[i] in pair_chars:
                    pair_opened = not pair_opened
                elif s[i] in open_chars and not pair_opened:
                    depth += 1
                elif s[i] in close_chars and not pair_opened:
                    depth -= 1
            return -1

        assert _find_next_unenclosed("a(b(c,'d))',e),f), g", 2, ")", "(", ")", "'") == 16

        result = None
        if "(" in expr:
            # do function call
            param_start = expr.find("(")
            param_end = _find_next_unenclosed(expr, param_start + 1, ")", "(", ")", "'")
            if param_end == -1:
                raise ValueError(f"Failed to find matching ')' for function call")
            function_name = expr[:param_start]
            if not function_name.isalnum():
                raise ValueError(f"Invalid function name: {function_name}")
            param_list_str = expr[param_start + 1 : param_end]
            param_list = []
            i = 0
            while i < len(param_list_str):
                next_comma = _find_next_unenclosed(param_list_str, i, ",", "(", ")", "'")
                if next_comma == -1:
                    param_list.append(param_list_str[i:].strip())
                    break
                param_list.append(param_list_str[i:next_comma].strip())
                i = next_comma + 1
            result = _handle_func(function_name, [evaluate_expr(p, _handle_func) for p in param_list])
            expr = expr[param_end + 1 :].strip()
        else:
            raise ValueError(f"Expected to find a function call at expression root")

        # Handle property access
        while expr.startswith("."):
            prop_end = expr.find(".", 1)
            if prop_end == -1:
                prop_end = len(expr)
            prop_name = expr[1:prop_end]
            if not prop_name:
                raise ValueError(f"Failed to parse property access")
            assert isinstance(result, dict)
            result = result.get(prop_name)
            expr = expr[prop_end + 1 :].strip()

        if expr:
            raise ValueError(f"Unexpected trailing string: {expr}")

        if debug:
            print(f"Evaluated expression '{orig_expr}' to {json.dumps(result)}", flush=True)
        return result
    except Exception as e:
        raise ValueError(f"Failed to parse expression '{orig_expr}': {e}")
