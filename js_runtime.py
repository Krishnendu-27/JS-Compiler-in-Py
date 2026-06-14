#!/usr/bin/env python3
"""
Thunder Hackathon 2.0 — ThunderJS Runtime
A genuine JavaScript interpreter written in Python from scratch.
No JS engine, no Node.js, no subprocess — pure Python logic.

Supports:
  - let / const / var declarations
  - Primitive types: number, string, boolean, null, undefined
  - Reference types: object, array, function
  - Arithmetic, comparison, logical, assignment operators
  - if / else if / else, switch / case
  - for, while, do...while loops
  - Array & String built-in methods
  - Object creation and property access
  - Function declarations, expressions, arrow functions
  - Callbacks, closures, map/filter/reduce/find/some/every
  - Math object (floor, ceil, round, abs, max, min, pow, sqrt, random, PI, log)
  - Date object (getFullYear, getMonth, getDate, getHours, getDay, getTime)
  - Spread [...arr] and rest (...args) operators
  - typeof, type coercion, Number(), String(), Boolean() conversions
  - Ternary operator (condition ? a : b)
  - Template literals `Hello ${name}`
  - console.log()
"""

import sys
import re
import math
import random
import time
import argparse
from datetime import datetime


# ---------------------------------------------------------------------------
# JS Value helpers
# ---------------------------------------------------------------------------

UNDEFINED = object()   # sentinel for JS undefined

def js_typeof(val):
    if val is UNDEFINED:             return "undefined"
    if val is None:                  return "object"      # typeof null === "object"
    if isinstance(val, bool):        return "boolean"
    if isinstance(val, (int, float)):return "number"
    if isinstance(val, str):         return "string"
    if callable(val):                return "function"
    return "object"

def js_to_string(val):
    """Convert a Python value to its JavaScript string representation."""
    if val is UNDEFINED:             return "undefined"
    if val is None:                  return "null"
    if isinstance(val, bool):        return "true" if val else "false"
    if isinstance(val, float):
        if val != val:               return "NaN"         # NaN check
        if val == float('inf'):      return "Infinity"
        if val == float('-inf'):     return "-Infinity"
        if val.is_integer():         return str(int(val))
        return str(val)
    if isinstance(val, int):         return str(val)
    if isinstance(val, list):
        return ",".join(js_to_string(v) for v in val)
    if isinstance(val, dict):        return "[object Object]"
    return str(val)

def js_to_number(val):
    """Coerce a JS value to a number (like Number() in JS)."""
    if val is UNDEFINED:             return float('nan')
    if val is None:                  return 0
    if isinstance(val, bool):        return 1 if val else 0
    if isinstance(val, (int, float)):return val
    if isinstance(val, str):
        s = val.strip()
        if s == "":                  return 0
        try:                         return int(s, 0) if s.startswith(('0x','0o','0b')) else float(s)
        except ValueError:           return float('nan')
    return float('nan')

def js_to_bool(val):
    """Truthy/falsy following JS rules."""
    if val is UNDEFINED:             return False
    if val is None:                  return False
    if isinstance(val, bool):        return val
    if isinstance(val, (int, float)):return val != 0 and val == val  # 0 and NaN are falsy
    if isinstance(val, str):         return val != ""
    return True   # objects/arrays are truthy

def js_equals(a, b, strict=False):
    """Implement == (loose) and === (strict) equality."""
    if strict:
        if type(a) != type(b):
            # int vs float with same numeric value
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                return a == b
            return False
        if a is UNDEFINED and b is UNDEFINED: return True
        if a is None and b is None:           return True
        return a == b
    # Loose equality
    if a is None and b is None:               return True
    if a is UNDEFINED and b is UNDEFINED:     return True
    if (a is None or a is UNDEFINED) and (b is None or b is UNDEFINED): return True
    if isinstance(a, bool):                   a = js_to_number(a)
    if isinstance(b, bool):                   b = js_to_number(b)
    if isinstance(a, (int, float)) and isinstance(b, str): b = js_to_number(b)
    if isinstance(b, (int, float)) and isinstance(a, str): a = js_to_number(a)
    return a == b

def js_add(a, b):
    """JS + operator: numeric addition or string concatenation."""
    if isinstance(a, str) or isinstance(b, str):
        return js_to_string(a) + js_to_string(b)
    an, bn = js_to_number(a), js_to_number(b)
    result = an + bn
    return int(result) if isinstance(result, float) and result.is_integer() else result

def console_log_format(args):
    """Mimic console.log output: space-separated, JS-style values."""
    parts = []
    for v in args:
        if isinstance(v, list):
            parts.append("[ " + ", ".join(
                ("'" + x + "'" if isinstance(x, str) else js_to_string(x))
                for x in v
            ) + " ]" if v else "[]")
        elif isinstance(v, dict):
            items = ", ".join(f"{k}: {js_to_string(val)}" for k, val in v.items())
            parts.append("{ " + items + " }" if items else "{}")
        else:
            parts.append(js_to_string(v))
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

TK = {
    'NUM': 'NUM', 'STR': 'STR', 'BOOL': 'BOOL', 'NULL': 'NULL',
    'UNDEFINED': 'UNDEFINED', 'IDENT': 'IDENT', 'TEMPLATE': 'TEMPLATE',
    'PUNCT': 'PUNCT', 'OP': 'OP', 'EOF': 'EOF',
}

class Token:
    __slots__ = ('type', 'value', 'line')
    def __init__(self, t, v, line=0):
        self.type, self.value, self.line = t, v, line
    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"

KEYWORDS = {'let','const','var','function','return','if','else','for','while',
            'do','break','continue','new','typeof','instanceof','in','of',
            'switch','case','default','true','false','null','undefined',
            'this','class','extends','import','export','throw','try','catch',
            'finally', 'delete', 'void'}

def tokenize(src):
    tokens = []
    i, line = 0, 1
    n = len(src)
    while i < n:
        c = src[i]
        # newline
        if c == '\n':
            line += 1; i += 1; continue
        # whitespace
        if c in ' \t\r':
            i += 1; continue
        # single-line comment
        if src[i:i+2] == '//':
            while i < n and src[i] != '\n': i += 1
            continue
        # multi-line comment
        if src[i:i+2] == '/*':
            i += 2
            while i < n-1 and src[i:i+2] != '*/': 
                if src[i] == '\n': line += 1
                i += 1
            i += 2; continue
        # template literal
        if c == '`':
            i += 1; s = ''
            while i < n and src[i] != '`':
                if src[i] == '\n': line += 1
                s += src[i]; i += 1
            i += 1
            tokens.append(Token('TEMPLATE', s, line)); continue
        # string
        if c in ('"', "'"):
            q = c; i += 1; s = ''
            while i < n and src[i] != q:
                if src[i] == '\\':
                    i += 1
                    esc = {'n':'\n','t':'\t','r':'\r','\\':'\\','"':'"',"'":'\'','`':'`'}
                    s += esc.get(src[i], src[i]) if i < n else ''
                else:
                    if src[i] == '\n': line += 1
                    s += src[i]
                i += 1
            i += 1
            tokens.append(Token('STR', s, line)); continue
        # number (hex, float, int)
        if c.isdigit() or (c == '.' and i+1 < n and src[i+1].isdigit()):
            j = i
            if src[i:i+2] in ('0x','0X'):
                i += 2
                while i < n and src[i] in '0123456789abcdefABCDEF': i += 1
                tokens.append(Token('NUM', int(src[j:i], 16), line)); continue
            while i < n and (src[i].isdigit() or src[i] == '.'): i += 1
            if i < n and src[i] in ('e','E'):
                i += 1
                if i < n and src[i] in ('+','-'): i += 1
                while i < n and src[i].isdigit(): i += 1
            raw = src[j:i]
            val = float(raw) if '.' in raw or 'e' in raw or 'E' in raw else int(raw)
            tokens.append(Token('NUM', val, line)); continue
        # identifier / keyword
        if c.isalpha() or c in '_$':
            j = i
            while i < n and (src[i].isalnum() or src[i] in '_$'): i += 1
            word = src[j:i]
            if word == 'true':      tokens.append(Token('BOOL', True, line))
            elif word == 'false':   tokens.append(Token('BOOL', False, line))
            elif word == 'null':    tokens.append(Token('NULL', None, line))
            elif word == 'undefined': tokens.append(Token('UNDEFINED', UNDEFINED, line))
            else:                   tokens.append(Token('IDENT', word, line))
            continue
        # multi-char operators
        two = src[i:i+2]
        three = src[i:i+3]
        if three in ('===','!==','**=','>>>=','<<=','>>=','...'):
            tokens.append(Token('OP', three, line)); i += 3; continue
        if two in ('==','!=','<=','>=','&&','||','++','--','**','=>',
                   '+=','-=','*=','/=','%=','??','<<','>>','>>>','**'):
            tokens.append(Token('OP', two, line)); i += 2; continue
        # single-char
        tokens.append(Token('PUNCT' if c in '(){}[];,.:' else 'OP', c, line))
        i += 1
    tokens.append(Token('EOF', None, line))
    return tokens


# ---------------------------------------------------------------------------
# Parser → AST
# ---------------------------------------------------------------------------

class ParseError(Exception): pass

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self): return self.tokens[self.pos]
    def advance(self): t = self.tokens[self.pos]; self.pos += 1; return t

    def eat(self, type_or_val):
        t = self.peek()
        if isinstance(type_or_val, str):
            if t.type == type_or_val or t.value == type_or_val:
                return self.advance()
        raise ParseError(f"Expected {type_or_val!r} but got {t!r} at line {t.line}")

    def match(self, *vals):
        t = self.peek()
        return t.value in vals or t.type in vals

    def check(self, val):
        return self.peek().value == val or self.peek().type == val

    # ---- top-level ----

    def parse_program(self):
        body = []
        while not self.match('EOF'):
            body.append(self.parse_statement())
        return ('program', body)

    def parse_statement(self):
        t = self.peek()
        # semicolons
        if t.value == ';':
            self.advance(); return ('empty',)
        # blocks
        if t.value == '{':
            return self.parse_block()
        # keywords
        if t.type == 'IDENT':
            v = t.value
            if v in ('let','const','var'):       return self.parse_var_decl()
            if v == 'function':                  return self.parse_function_decl()
            if v == 'return':                    return self.parse_return()
            if v == 'if':                        return self.parse_if()
            if v == 'for':                       return self.parse_for()
            if v == 'while':                     return self.parse_while()
            if v == 'do':                        return self.parse_do_while()
            if v == 'break':
                self.advance(); self.skip_semi(); return ('break',)
            if v == 'continue':
                self.advance(); self.skip_semi(); return ('continue',)
            if v == 'switch':                    return self.parse_switch()
            if v == 'throw':
                self.advance(); e = self.parse_expr(); self.skip_semi()
                return ('throw', e)
            if v == 'try':                       return self.parse_try()
            if v == 'class':                     return self.parse_class()
        # expression statement
        expr = self.parse_expr()
        self.skip_semi()
        return ('expr_stmt', expr)

    def skip_semi(self):
        if self.peek().value == ';': self.advance()

    def parse_block(self):
        self.eat('{')
        stmts = []
        while not self.match('}', 'EOF'):
            stmts.append(self.parse_statement())
        self.eat('}')
        return ('block', stmts)

    def parse_var_decl(self):
        kind = self.advance().value  # let / const / var
        decls = []
        while True:
            name = self.eat('IDENT').value
            init = None
            if self.peek().value == '=':
                self.advance()
                init = self.parse_assign_expr()
            decls.append((name, init))
            if self.peek().value != ',': break
            self.advance()
        self.skip_semi()
        return ('var_decl', kind, decls)

    def parse_function_decl(self):
        self.eat('function')
        name = self.eat('IDENT').value
        params = self.parse_params()
        body = self.parse_block()
        return ('func_decl', name, params, body)

    def parse_params(self):
        self.eat('(')
        params = []
        while not self.match(')','EOF'):
            rest = False
            if self.peek().value == '...':
                self.advance(); rest = True
            name = self.eat('IDENT').value
            default = None
            if self.peek().value == '=':
                self.advance(); default = self.parse_assign_expr()
            params.append(('rest_param' if rest else 'param', name, default))
            if self.peek().value != ',': break
            self.advance()
        self.eat(')')
        return params

    def parse_return(self):
        self.eat('return')
        val = None
        if not self.match(';','}','EOF') and self.peek().line == self.tokens[self.pos-1].line:
            val = self.parse_expr()
        self.skip_semi()
        return ('return', val)

    def parse_if(self):
        self.eat('if'); self.eat('(')
        cond = self.parse_expr()
        self.eat(')')
        then = self.parse_statement()
        alt = None
        if self.peek().value == 'else':
            self.advance()
            alt = self.parse_statement()
        return ('if', cond, then, alt)

    def parse_for(self):
        self.eat('for'); self.eat('(')
        # for...of / for...in detection
        # peek ahead for 'of' or 'in'
        saved = self.pos
        is_of = is_in = False
        try:
            if self.peek().value in ('let','const','var'):
                kw = self.advance().value
                vname = self.eat('IDENT').value
                if self.peek().value == 'of':   is_of = True
                elif self.peek().value == 'in': is_in = True
        except: pass
        if is_of or is_in:
            kw_token = self.tokens[saved].value
            self.advance()  # skip 'of'/'in'
            iterable = self.parse_expr()
            self.eat(')')
            body = self.parse_statement()
            return ('for_of' if is_of else 'for_in', kw_token, vname, iterable, body)
        self.pos = saved
        # classic for
        init = None
        if not self.match(';'):
            if self.peek().value in ('let','const','var'):
                init = self.parse_var_decl_no_semi()
            else:
                init = ('expr_stmt', self.parse_expr())
        self.skip_semi()
        cond = None if self.match(';') else self.parse_expr()
        self.skip_semi()
        update = None if self.match(')') else self.parse_expr()
        self.eat(')')
        body = self.parse_statement()
        return ('for', init, cond, update, body)

    def parse_var_decl_no_semi(self):
        kind = self.advance().value
        decls = []
        while True:
            name = self.eat('IDENT').value
            init = None
            if self.peek().value == '=':
                self.advance(); init = self.parse_assign_expr()
            decls.append((name, init))
            if self.peek().value != ',': break
            self.advance()
        return ('var_decl', kind, decls)

    def parse_while(self):
        self.eat('while'); self.eat('(')
        cond = self.parse_expr(); self.eat(')')
        body = self.parse_statement()
        return ('while', cond, body)

    def parse_do_while(self):
        self.eat('do')
        body = self.parse_statement()
        self.eat('while'); self.eat('(')
        cond = self.parse_expr(); self.eat(')')
        self.skip_semi()
        return ('do_while', body, cond)

    def parse_switch(self):
        self.eat('switch'); self.eat('(')
        disc = self.parse_expr(); self.eat(')')
        self.eat('{')
        cases = []
        default = None
        while not self.match('}','EOF'):
            if self.peek().value == 'case':
                self.advance()
                test = self.parse_expr(); self.eat(':')
                stmts = []
                while not self.match('case','default','}','EOF'):
                    stmts.append(self.parse_statement())
                cases.append(('case', test, stmts))
            elif self.peek().value == 'default':
                self.advance(); self.eat(':')
                stmts = []
                while not self.match('case','default','}','EOF'):
                    stmts.append(self.parse_statement())
                default = stmts
            else:
                break
        self.eat('}')
        return ('switch', disc, cases, default)

    def parse_try(self):
        self.eat('try')
        body = self.parse_block()
        catch_clause = None
        finally_clause = None
        if self.peek().value == 'catch':
            self.advance()
            param = None
            if self.peek().value == '(':
                self.advance(); param = self.eat('IDENT').value; self.eat(')')
            catch_clause = (param, self.parse_block())
        if self.peek().value == 'finally':
            self.advance(); finally_clause = self.parse_block()
        return ('try', body, catch_clause, finally_clause)

    def parse_class(self):
        self.eat('class')
        name = self.eat('IDENT').value
        superclass = None
        if self.peek().value == 'extends':
            self.advance(); superclass = self.eat('IDENT').value
        self.eat('{')
        methods = []
        while not self.match('}','EOF'):
            static = False
            if self.peek().value == 'static': self.advance(); static = True
            mname = self.advance().value
            params = self.parse_params()
            body = self.parse_block()
            methods.append(('method', mname, params, body, static))
        self.eat('}')
        return ('class', name, superclass, methods)

    # ---- expressions ----

    def parse_expr(self):
        return self.parse_assign_expr()

    def parse_assign_expr(self):
        left = self.parse_ternary()
        op = self.peek().value
        if op in ('=','+=','-=','*=','/=','%=','**='):
            self.advance()
            right = self.parse_assign_expr()
            return ('assign', op, left, right)
        return left

    def parse_ternary(self):
        cond = self.parse_or()
        if self.peek().value == '?':
            self.advance()
            then = self.parse_assign_expr()
            self.eat(':')
            alt = self.parse_assign_expr()
            return ('ternary', cond, then, alt)
        return cond

    def parse_or(self):
        left = self.parse_and()
        while self.peek().value == '||':
            op = self.advance().value; right = self.parse_and()
            left = ('binop', op, left, right)
        return left

    def parse_and(self):
        left = self.parse_nullish()
        while self.peek().value == '&&':
            op = self.advance().value; right = self.parse_nullish()
            left = ('binop', op, left, right)
        return left

    def parse_nullish(self):
        left = self.parse_equality()
        while self.peek().value == '??':
            self.advance(); right = self.parse_equality()
            left = ('binop', '??', left, right)
        return left

    def parse_equality(self):
        left = self.parse_relational()
        while self.peek().value in ('==','!=','===','!=='):
            op = self.advance().value; right = self.parse_relational()
            left = ('binop', op, left, right)
        return left

    def parse_relational(self):
        left = self.parse_additive()
        while self.peek().value in ('<','>','<=','>=','instanceof','in'):
            op = self.advance().value; right = self.parse_additive()
            left = ('binop', op, left, right)
        return left

    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.peek().value in ('+','-'):
            op = self.advance().value; right = self.parse_multiplicative()
            left = ('binop', op, left, right)
        return left

    def parse_multiplicative(self):
        left = self.parse_exponent()
        while self.peek().value in ('*','/','%'):
            op = self.advance().value; right = self.parse_exponent()
            left = ('binop', op, left, right)
        return left

    def parse_exponent(self):
        left = self.parse_unary()
        if self.peek().value == '**':
            op = self.advance().value; right = self.parse_exponent()
            return ('binop', op, left, right)
        return left

    def parse_unary(self):
        op = self.peek().value
        if op == '!':  self.advance(); return ('unary', '!', self.parse_unary())
        if op == '-':  self.advance(); return ('unary', '-', self.parse_unary())
        if op == '+':  self.advance(); return ('unary', '+', self.parse_unary())
        if op == '++': self.advance(); return ('unary', 'pre++', self.parse_unary())
        if op == '--': self.advance(); return ('unary', 'pre--', self.parse_unary())
        if op == 'typeof': self.advance(); return ('typeof', self.parse_unary())
        if op == 'void':   self.advance(); self.parse_unary(); return ('literal', UNDEFINED)
        if op == 'delete': self.advance(); return ('delete', self.parse_unary())
        if op == '...':    self.advance(); return ('spread', self.parse_unary())
        return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_call()
        # Single-param bare arrow: ident => ...
        if expr[0] == 'ident' and self.peek().value == '=>':
            self.advance()
            params = [('param', expr[1], None)]
            if self.peek().value == '{':
                body = self.parse_block()
            else:
                body = ('return', self.parse_assign_expr())
            return ('arrow', params, body)
        if self.peek().value == '++': self.advance(); return ('unary', 'post++', expr)
        if self.peek().value == '--': self.advance(); return ('unary', 'post--', expr)
        return expr

    def parse_call(self):
        expr = self.parse_primary()
        while True:
            if self.peek().value == '(':
                args = self.parse_args()
                expr = ('call', expr, args)
            elif self.peek().value == '.':
                self.advance()
                prop = self.advance().value
                expr = ('member', expr, ('literal', prop), False)
            elif self.peek().value == '[':
                self.advance()
                idx = self.parse_expr()
                self.eat(']')
                expr = ('member', expr, idx, True)
            else:
                break
        return expr

    def parse_args(self):
        self.eat('(')
        args = []
        while not self.match(')','EOF'):
            if self.peek().value == '...':
                self.advance()
                args.append(('spread', self.parse_assign_expr()))
            else:
                args.append(self.parse_assign_expr())
            if self.peek().value != ',': break
            self.advance()
        self.eat(')')
        return args

    def parse_primary(self):
        t = self.peek()
        # Literals
        if t.type == 'NUM':   self.advance(); return ('literal', t.value)
        if t.type == 'STR':   self.advance(); return ('literal', t.value)
        if t.type == 'BOOL':  self.advance(); return ('literal', t.value)
        if t.type == 'NULL':  self.advance(); return ('literal', None)
        if t.type == 'UNDEFINED': self.advance(); return ('literal', UNDEFINED)
        if t.type == 'TEMPLATE':  self.advance(); return ('template', t.value)
        # Grouping / arrow function
        if t.value == '(':
            return self.parse_paren_or_arrow()
        # Array literal
        if t.value == '[':
            return self.parse_array()
        # Object literal
        if t.value == '{':
            return self.parse_object()
        # new
        if t.value == 'new':
            self.advance()
            cls = self.parse_call()
            return ('new', cls)
        # function expression
        if t.value == 'function':
            return self.parse_func_expr()
        # identifier
        if t.type == 'IDENT':
            self.advance(); return ('ident', t.value)
        raise ParseError(f"Unexpected token {t!r} at line {t.line}")

    def parse_paren_or_arrow(self):
        saved = self.pos
        try:
            self.eat('(')
            params = []
            while not self.match(')','EOF'):
                rest = False
                if self.peek().value == '...': self.advance(); rest = True
                name = self.eat('IDENT').value
                default = None
                if self.peek().value == '=':
                    self.advance(); default = self.parse_assign_expr()
                params.append(('rest_param' if rest else 'param', name, default))
                if self.peek().value != ',': break
                self.advance()
            self.eat(')')
            if self.peek().value == '=>':
                self.advance()
                if self.peek().value == '{':
                    body = self.parse_block()
                else:
                    body = ('return', self.parse_assign_expr())
                return ('arrow', params, body)
        except ParseError:
            pass
        self.pos = saved
        self.eat('(')
        expr = self.parse_expr()
        self.eat(')')
        return expr

    def parse_func_expr(self):
        self.eat('function')
        name = None
        if self.peek().type == 'IDENT': name = self.advance().value
        params = self.parse_params()
        body = self.parse_block()
        return ('func_expr', name, params, body)

    def parse_array(self):
        self.eat('[')
        elems = []
        while not self.match(']','EOF'):
            if self.peek().value == ',':
                elems.append(('literal', UNDEFINED)); self.advance(); continue
            if self.peek().value == '...':
                self.advance(); elems.append(('spread', self.parse_assign_expr()))
            else:
                elems.append(self.parse_assign_expr())
            if self.peek().value != ',': break
            self.advance()
        self.eat(']')
        return ('array', elems)

    def parse_object(self):
        self.eat('{')
        props = []
        while not self.match('}','EOF'):
            if self.peek().value == '...':
                self.advance(); props.append(('spread', self.parse_assign_expr()))
            else:
                if self.peek().type in ('IDENT','STR','NUM'):
                    key_tok = self.advance()
                    key = key_tok.value
                else:
                    key = self.advance().value
                # shorthand: {name} => {name: name}
                if self.peek().value not in (':', '('):
                    props.append(('prop', key, ('ident', key))); 
                    if self.peek().value == ',': self.advance()
                    continue
                # method shorthand: {foo() {...}}
                if self.peek().value == '(':
                    params = self.parse_params()
                    body = self.parse_block()
                    props.append(('method_prop', key, params, body))
                    if self.peek().value == ',': self.advance()
                    continue
                self.eat(':')
                val = self.parse_assign_expr()
                props.append(('prop', key, val))
            if self.peek().value != ',': break
            self.advance()
        self.eat('}')
        return ('object', props)


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

class ReturnSignal(Exception):
    def __init__(self, val): self.val = val

class BreakSignal(Exception): pass
class ContinueSignal(Exception): pass
class ThrowSignal(Exception):
    def __init__(self, val): self.val = val

class Environment:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def get(self, name):
        if name in self.vars: return self.vars[name]
        if self.parent:       return self.parent.get(name)
        return UNDEFINED

    def set(self, name, val):
        if name in self.vars:
            self.vars[name] = val; return
        if self.parent and self.parent.has(name):
            self.parent.set(name, val); return
        # global assignment creates a global var
        env = self
        while env.parent: env = env.parent
        env.vars[name] = val

    def has(self, name):
        if name in self.vars: return True
        if self.parent:       return self.parent.has(name)
        return False

    def define(self, name, val):
        self.vars[name] = val

class JSFunction:
    def __init__(self, name, params, body, closure):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure

    def __repr__(self):
        return f"[Function: {self.name or 'anonymous'}]"

class JSClass:
    def __init__(self, name, superclass, methods):
        self.name = name
        self.superclass = superclass
        self.methods = methods  # dict

class JSObject:
    def __init__(self, cls=None, props=None):
        self.cls = cls
        self.props = props or {}

    def __repr__(self):
        items = ", ".join(f"{k}: {js_to_string(v)}" for k,v in self.props.items())
        return "{" + items + "}"


class Interpreter:
    def __init__(self):
        self.output = []
        self.global_env = Environment()
        self._now = datetime.now()
        self._setup_builtins()

    def _setup_builtins(self):
        env = self.global_env

        # console
        console = {}
        console['log'] = lambda *args: self.output.append(console_log_format(list(args)))
        console['error'] = lambda *args: self.output.append(console_log_format(list(args)))
        console['warn']  = lambda *args: self.output.append(console_log_format(list(args)))
        env.define('console', console)

        # Math
        m = {
            'PI': math.pi, 'E': math.e, 'LN2': math.log(2), 'LN10': math.log(10),
            'LOG2E': math.log2(math.e), 'LOG10E': math.log10(math.e),
            'SQRT2': math.sqrt(2), 'Infinity': float('inf'), 'NaN': float('nan'),
            'floor':  lambda x: int(math.floor(js_to_number(x))),
            'ceil':   lambda x: int(math.ceil(js_to_number(x))),
            'round':  lambda x: int(math.floor(js_to_number(x) + 0.5)),
            'abs':    lambda x: abs(js_to_number(x)),
            'sqrt':   lambda x: math.sqrt(js_to_number(x)),
            'pow':    lambda x, y: js_to_number(x) ** js_to_number(y),
            'max':    lambda *a: max(js_to_number(v) for v in a),
            'min':    lambda *a: min(js_to_number(v) for v in a),
            'log':    lambda x: math.log(js_to_number(x)),
            'log2':   lambda x: math.log2(js_to_number(x)),
            'log10':  lambda x: math.log10(js_to_number(x)),
            'sin':    lambda x: math.sin(js_to_number(x)),
            'cos':    lambda x: math.cos(js_to_number(x)),
            'tan':    lambda x: math.tan(js_to_number(x)),
            'random': lambda: random.random(),
            'trunc':  lambda x: int(js_to_number(x)),
            'sign':   lambda x: (1 if js_to_number(x) > 0 else -1 if js_to_number(x) < 0 else 0),
            'hypot':  lambda *a: math.hypot(*[js_to_number(v) for v in a]),
        }
        env.define('Math', m)

        # Date constructor (simplified)
        now = self._now
        def make_date():
            d = {
                'getFullYear':    lambda: now.year,
                'getMonth':       lambda: now.month - 1,   # JS months: 0-indexed
                'getDate':        lambda: now.day,
                'getDay':         lambda: now.weekday() + 1 if now.weekday() < 6 else 0,
                'getHours':       lambda: now.hour,
                'getMinutes':     lambda: now.minute,
                'getSeconds':     lambda: now.second,
                'getTime':        lambda: int(now.timestamp() * 1000),
                'toLocaleDateString': lambda: now.strftime('%m/%d/%Y'),
                'toLocaleTimeString': lambda: now.strftime('%H:%M:%S'),
                'toISOString':    lambda: now.isoformat() + 'Z',
                'toString':       lambda: now.strftime('%a %b %d %Y %H:%M:%S'),
                '__is_date__':    True,
            }
            return d
        env.define('Date', make_date)   # new Date()

        # Type conversion builtins
        env.define('Number',   lambda v=UNDEFINED: (
            float('nan') if v is UNDEFINED else js_to_number(v)))
        env.define('String',   lambda v=UNDEFINED: "" if v is UNDEFINED else js_to_string(v))
        env.define('Boolean',  lambda v=UNDEFINED: False if v is UNDEFINED else js_to_bool(v))
        env.define('parseInt', lambda s, base=10: (
            int(str(s).strip().split('.')[0], int(js_to_number(base))) if str(s).strip() else float('nan')))
        env.define('parseFloat', lambda s: js_to_number(s))
        env.define('isNaN',    lambda v: js_to_number(v) != js_to_number(v))
        env.define('isFinite', lambda v: math.isfinite(js_to_number(v)))
        env.define('Infinity', float('inf'))
        env.define('NaN',      float('nan'))
        env.define('undefined', UNDEFINED)
        env.define('JSON', {
            'stringify': lambda v, *a: self._json_stringify(v),
            'parse':     lambda s: self._json_parse(s),
        })
        env.define('Array', {
            'isArray':  lambda v: isinstance(v, list),
            'from':     lambda v, *a: list(v) if isinstance(v, list) else [],
            'of':       lambda *a: list(a),
        })
        env.define('Object', {
            'keys':    lambda v: list(v.keys()) if isinstance(v, dict) else [],
            'values':  lambda v: list(v.values()) if isinstance(v, dict) else [],
            'entries': lambda v: [[k, val] for k, val in v.items()] if isinstance(v, dict) else [],
            'assign':  lambda t, *srcs: self._object_assign(t, srcs),
        })

    def _json_stringify(self, v):
        def cvt(x):
            if x is None: return 'null'
            if x is UNDEFINED: return 'undefined'
            if isinstance(x, bool): return 'true' if x else 'false'
            if isinstance(x, float): return str(int(x)) if x.is_integer() else str(x)
            if isinstance(x, int): return str(x)
            if isinstance(x, str): return '"' + x + '"'
            if isinstance(x, list): return '[' + ','.join(cvt(e) for e in x) + ']'
            if isinstance(x, dict): return '{' + ','.join(f'"{k}":{cvt(val)}' for k,val in x.items()) + '}'
            return str(x)
        return cvt(v)

    def _json_parse(self, s):
        import json as _json
        def obj_hook(d): return d
        return _json.loads(s, object_hook=obj_hook)

    def _object_assign(self, target, sources):
        if isinstance(target, dict):
            for src in sources:
                if isinstance(src, dict): target.update(src)
        return target

    # ---- execution ----

    def run(self, ast):
        env = self.global_env
        for stmt in ast[1]:
            self.exec_stmt(stmt, env)

    def exec_stmt(self, node, env):
        kind = node[0]
        if kind == 'empty':   return
        if kind == 'program': [self.exec_stmt(s, env) for s in node[1]]; return
        if kind == 'block':   self.exec_block(node[1], env); return
        if kind == 'expr_stmt': self.eval_expr(node[1], env); return
        if kind == 'var_decl':  self.exec_var_decl(node, env); return
        if kind == 'func_decl': self.exec_func_decl(node, env); return
        if kind == 'return':    raise ReturnSignal(self.eval_expr(node[1], env) if node[1] else UNDEFINED)
        if kind == 'if':        self.exec_if(node, env); return
        if kind == 'for':       self.exec_for(node, env); return
        if kind == 'for_of':    self.exec_for_of(node, env); return
        if kind == 'for_in':    self.exec_for_in(node, env); return
        if kind == 'while':     self.exec_while(node, env); return
        if kind == 'do_while':  self.exec_do_while(node, env); return
        if kind == 'break':     raise BreakSignal()
        if kind == 'continue':  raise ContinueSignal()
        if kind == 'switch':    self.exec_switch(node, env); return
        if kind == 'throw':
            val = self.eval_expr(node[1], env)
            raise ThrowSignal(val)
        if kind == 'try':       self.exec_try(node, env); return
        if kind == 'class':     self.exec_class(node, env); return
        raise ParseError(f"Unknown statement kind: {kind}")

    def exec_block(self, stmts, parent_env):
        env = Environment(parent_env)
        for stmt in stmts:
            self.exec_stmt(stmt, env)

    def exec_var_decl(self, node, env):
        _, kind, decls = node
        for name, init in decls:
            val = self.eval_expr(init, env) if init else UNDEFINED
            env.define(name, val)

    def exec_func_decl(self, node, env):
        _, name, params, body = node
        fn = JSFunction(name, params, body, env)
        env.define(name, fn)

    def exec_if(self, node, env):
        _, cond, then, alt = node
        if js_to_bool(self.eval_expr(cond, env)):
            self.exec_stmt(then, env)
        elif alt:
            self.exec_stmt(alt, env)

    def exec_for(self, node, env):
        _, init, cond, update, body = node
        loop_env = Environment(env)
        if init: self.exec_stmt(init, loop_env)
        while True:
            if cond and not js_to_bool(self.eval_expr(cond, loop_env)): break
            try:
                self.exec_stmt(body, loop_env)
            except BreakSignal: break
            except ContinueSignal: pass
            if update: self.eval_expr(update, loop_env)

    def exec_for_of(self, node, env):
        _, kind, varname, iterable_expr, body = node
        iterable = self.eval_expr(iterable_expr, env)
        if isinstance(iterable, str): iterable = list(iterable)
        for item in (iterable if isinstance(iterable, list) else []):
            loop_env = Environment(env)
            loop_env.define(varname, item)
            try:
                self.exec_stmt(body, loop_env)
            except BreakSignal: break
            except ContinueSignal: continue

    def exec_for_in(self, node, env):
        _, kind, varname, obj_expr, body = node
        obj = self.eval_expr(obj_expr, env)
        keys = list(obj.keys()) if isinstance(obj, dict) else list(range(len(obj))) if isinstance(obj, list) else []
        for k in keys:
            loop_env = Environment(env)
            loop_env.define(varname, str(k))
            try:
                self.exec_stmt(body, loop_env)
            except BreakSignal: break
            except ContinueSignal: continue

    def exec_while(self, node, env):
        _, cond, body = node
        while js_to_bool(self.eval_expr(cond, env)):
            try:
                self.exec_stmt(body, env)
            except BreakSignal: break
            except ContinueSignal: continue

    def exec_do_while(self, node, env):
        _, body, cond = node
        while True:
            try:
                self.exec_stmt(body, env)
            except BreakSignal: break
            except ContinueSignal: pass
            if not js_to_bool(self.eval_expr(cond, env)): break

    def exec_switch(self, node, env):
        _, disc_expr, cases, default = node
        disc = self.eval_expr(disc_expr, env)
        matched = False
        try:
            for case_kind, test_expr, stmts in cases:
                if not matched:
                    test = self.eval_expr(test_expr, env)
                    if js_equals(disc, test, strict=True):
                        matched = True
                if matched:
                    for s in stmts:
                        self.exec_stmt(s, env)
            if not matched and default:
                for s in default:
                    self.exec_stmt(s, env)
        except BreakSignal:
            pass

    def exec_try(self, node, env):
        _, body, catch_clause, finally_clause = node
        try:
            self.exec_stmt(body, env)
        except ThrowSignal as e:
            if catch_clause:
                param, catch_body = catch_clause
                catch_env = Environment(env)
                if param: catch_env.define(param, e.val)
                self.exec_stmt(catch_body, catch_env)
        except Exception as e:
            if catch_clause:
                param, catch_body = catch_clause
                catch_env = Environment(env)
                if param: catch_env.define(param, str(e))
                self.exec_stmt(catch_body, catch_env)
        finally:
            if finally_clause: self.exec_stmt(finally_clause, env)

    def exec_class(self, node, env):
        _, name, superclass_name, methods_nodes = node
        superclass = env.get(superclass_name) if superclass_name else None
        methods = {}
        for mn in methods_nodes:
            _, mname, params, body, static = mn
            methods[mname] = JSFunction(mname, params, body, env)
        cls = JSClass(name, superclass, methods)
        env.define(name, cls)

    # ---- expression evaluation ----

    def eval_expr(self, node, env):
        if node is None: return UNDEFINED
        kind = node[0]

        if kind == 'literal':  return node[1]
        if kind == 'ident':    return env.get(node[1])

        if kind == 'template':
            return self.eval_template(node[1], env)

        if kind == 'array':
            result = []
            for elem in node[1]:
                if elem[0] == 'spread':
                    v = self.eval_expr(elem[1], env)
                    if isinstance(v, list): result.extend(v)
                else:
                    result.append(self.eval_expr(elem, env))
            return result

        if kind == 'object':
            result = {}
            for prop in node[1]:
                if prop[0] == 'spread':
                    v = self.eval_expr(prop[1], env)
                    if isinstance(v, dict): result.update(v)
                elif prop[0] == 'prop':
                    result[str(prop[1])] = self.eval_expr(prop[2], env)
                elif prop[0] == 'method_prop':
                    _, mname, params, body = prop
                    result[mname] = JSFunction(mname, params, body, env)
            return result

        if kind == 'func_expr' or kind == 'arrow':
            _, *rest = node
            if kind == 'arrow':
                params, body = rest
                name = None
            else:
                name, params, body = rest
            return JSFunction(name, params, body, env)

        if kind == 'typeof':
            # avoid ReferenceError for undeclared vars
            inner = node[1]
            if inner[0] == 'ident': return js_typeof(env.get(inner[1]))
            return js_typeof(self.eval_expr(inner, env))

        if kind == 'delete':
            inner = node[1]
            if inner[0] == 'member':
                _, obj_expr, key_expr, computed = inner
                obj = self.eval_expr(obj_expr, env)
                key = self.eval_expr(key_expr, env) if computed else key_expr[1]
                if isinstance(obj, dict) and str(key) in obj:
                    del obj[str(key)]
            return True

        if kind == 'spread':
            return self.eval_expr(node[1], env)  # spread values handled at call site

        if kind == 'unary':
            _, op, operand = node
            if op == '!':
                return not js_to_bool(self.eval_expr(operand, env))
            if op == '-':
                v = self.eval_expr(operand, env)
                n = js_to_number(v)
                return int(-n) if isinstance(n, (int,float)) and float(-n).is_integer() else -n
            if op == '+':
                return js_to_number(self.eval_expr(operand, env))
            if op in ('pre++', 'pre--'):
                v = js_to_number(self.eval_expr(operand, env))
                new_v = v + (1 if op == 'pre++' else -1)
                new_v = int(new_v) if isinstance(new_v, float) and new_v.is_integer() else new_v
                self.assign_target(operand, new_v, env)
                return new_v
            if op in ('post++', 'post--'):
                v = js_to_number(self.eval_expr(operand, env))
                new_v = v + (1 if op == 'post++' else -1)
                new_v = int(new_v) if isinstance(new_v, float) and new_v.is_integer() else new_v
                self.assign_target(operand, new_v, env)
                return v

        if kind == 'binop':
            _, op, left_expr, right_expr = node
            # Short-circuit operators
            if op == '&&':
                lv = self.eval_expr(left_expr, env)
                return lv if not js_to_bool(lv) else self.eval_expr(right_expr, env)
            if op == '||':
                lv = self.eval_expr(left_expr, env)
                return lv if js_to_bool(lv) else self.eval_expr(right_expr, env)
            if op == '??':
                lv = self.eval_expr(left_expr, env)
                return lv if lv is not None and lv is not UNDEFINED else self.eval_expr(right_expr, env)
            lv = self.eval_expr(left_expr, env)
            rv = self.eval_expr(right_expr, env)
            return self.eval_binop(op, lv, rv)

        if kind == 'ternary':
            _, cond, then, alt = node
            return self.eval_expr(then, env) if js_to_bool(self.eval_expr(cond, env)) else self.eval_expr(alt, env)

        if kind == 'assign':
            _, op, target, value_expr = node
            val = self.eval_expr(value_expr, env)
            if op != '=':
                cur = self.eval_expr(target, env)
                op2 = op[:-1]
                val = self.eval_binop(op2, cur, val)
            self.assign_target(target, val, env)
            return val

        if kind == 'member':
            _, obj_expr, key_expr, computed = node
            obj = self.eval_expr(obj_expr, env)
            key = self.eval_expr(key_expr, env) if computed else key_expr[1]
            return self.get_property(obj, key)

        if kind == 'call':
            _, callee_expr, arg_exprs = node
            # Evaluate arguments (expand spreads)
            args = []
            for ae in arg_exprs:
                if ae[0] == 'spread':
                    v = self.eval_expr(ae[1], env)
                    if isinstance(v, list): args.extend(v)
                else:
                    args.append(self.eval_expr(ae, env))

            # Method call: obj.method(...)
            if callee_expr[0] == 'member':
                _, obj_expr, key_expr, computed = callee_expr
                obj = self.eval_expr(obj_expr, env)
                key = self.eval_expr(key_expr, env) if computed else key_expr[1]
                method = self.get_property(obj, key)
                return self.call_function(method, args, this=obj)
            else:
                fn = self.eval_expr(callee_expr, env)
                return self.call_function(fn, args, this=env.get('this'))

        if kind == 'new':
            _, cls_expr = node
            # Handle call inside new: new Date()
            if cls_expr[0] == 'call':
                _, inner_callee, arg_exprs = cls_expr
                args = [self.eval_expr(a, env) for a in arg_exprs]
                cls = self.eval_expr(inner_callee, env)
            else:
                args = []
                cls = self.eval_expr(cls_expr, env)
            return self.construct(cls, args, env)

        raise ParseError(f"Unknown expr kind: {kind}")

    def eval_template(self, raw, env):
        """Evaluate template literals like `Hello ${name}`."""
        result = ''
        i = 0
        while i < len(raw):
            if raw[i:i+2] == '${':
                end = raw.index('}', i+2)
                expr_src = raw[i+2:end]
                try:
                    tokens = tokenize(expr_src)
                    p = Parser(tokens)
                    expr_ast = p.parse_expr()
                    val = self.eval_expr(expr_ast, env)
                    result += js_to_string(val)
                except Exception:
                    result += raw[i:end+1]
                i = end + 1
            else:
                result += raw[i]; i += 1
        return result

    def assign_target(self, target, val, env):
        if target[0] == 'ident':
            env.set(target[1], val)
        elif target[0] == 'member':
            _, obj_expr, key_expr, computed = target
            obj = self.eval_expr(obj_expr, env)
            key = self.eval_expr(key_expr, env) if computed else key_expr[1]
            self.set_property(obj, key, val)

    def eval_binop(self, op, lv, rv):
        if op == '+':  return js_add(lv, rv)
        if op == '-':
            r = js_to_number(lv) - js_to_number(rv)
            return int(r) if isinstance(r, float) and r.is_integer() else r
        if op == '*':
            r = js_to_number(lv) * js_to_number(rv)
            return int(r) if isinstance(r, float) and r.is_integer() else r
        if op == '/':
            a, b = js_to_number(lv), js_to_number(rv)
            if b == 0: return float('inf') if a > 0 else (float('-inf') if a < 0 else float('nan'))
            r = a / b
            return int(r) if isinstance(r, float) and r.is_integer() else r
        if op == '%':
            a, b = js_to_number(lv), js_to_number(rv)
            r = math.fmod(a, b)
            return int(r) if isinstance(r, float) and r.is_integer() else r
        if op == '**':
            r = js_to_number(lv) ** js_to_number(rv)
            return int(r) if isinstance(r, float) and r.is_integer() else r
        if op == '==':  return js_equals(lv, rv, strict=False)
        if op == '!=':  return not js_equals(lv, rv, strict=False)
        if op == '===': return js_equals(lv, rv, strict=True)
        if op == '!==': return not js_equals(lv, rv, strict=True)
        if op == '<':
            if isinstance(lv, str) and isinstance(rv, str): return lv < rv
            return js_to_number(lv) < js_to_number(rv)
        if op == '>':
            if isinstance(lv, str) and isinstance(rv, str): return lv > rv
            return js_to_number(lv) > js_to_number(rv)
        if op == '<=':
            if isinstance(lv, str) and isinstance(rv, str): return lv <= rv
            return js_to_number(lv) <= js_to_number(rv)
        if op == '>=':
            if isinstance(lv, str) and isinstance(rv, str): return lv >= rv
            return js_to_number(lv) >= js_to_number(rv)
        if op == 'instanceof': return False
        if op == 'in':
            if isinstance(rv, dict): return str(lv) in rv
            if isinstance(rv, list): return js_to_number(lv) < len(rv)
            return False
        return UNDEFINED

    def get_property(self, obj, key):
        key_str = str(key)
        # Dict (object / Math / console / etc.)
        if isinstance(obj, dict):
            v = obj.get(key_str, UNDEFINED)
            if callable(v): return v
            return v
        # Array
        if isinstance(obj, list):
            return self.array_property(obj, key_str)
        # String
        if isinstance(obj, str):
            return self.string_property(obj, key_str)
        # Number property (e.g. (1.5).toFixed(2))
        if isinstance(obj, (int, float)):
            return self.number_property(obj, key_str)
        if isinstance(obj, JSFunction):
            if key_str == 'name': return obj.name or ''
            if key_str == 'length': return len(obj.params)
        return UNDEFINED

    def set_property(self, obj, key, val):
        if isinstance(obj, dict): obj[str(key)] = val
        elif isinstance(obj, list):
            try:
                idx = int(key)
                while len(obj) <= idx: obj.append(UNDEFINED)
                obj[idx] = val
            except (ValueError, TypeError):
                pass

    def array_property(self, arr, key):
        if key == 'length': return len(arr)
        try:
            idx = int(key)
            return arr[idx] if 0 <= idx < len(arr) else UNDEFINED
        except ValueError: pass

        # Array methods — return bound callables
        def push(*vals): arr.extend(vals); return len(arr)
        def pop(): return arr.pop() if arr else UNDEFINED
        def shift(): return arr.pop(0) if arr else UNDEFINED
        def unshift(*vals): 
            for v in reversed(vals): arr.insert(0, v)
            return len(arr)
        def splice(start, delete_count=None, *items):
            start = int(js_to_number(start))
            if start < 0: start = max(0, len(arr) + start)
            if delete_count is None: delete_count = len(arr) - start
            delete_count = int(js_to_number(delete_count))
            removed = arr[start:start+delete_count]
            arr[start:start+delete_count] = list(items)
            return removed
        def slice_(begin=UNDEFINED, end=UNDEFINED):
            s = 0 if begin is UNDEFINED else int(js_to_number(begin))
            e = len(arr) if end is UNDEFINED else int(js_to_number(end))
            if s < 0: s = max(0, len(arr) + s)
            if e < 0: e = max(0, len(arr) + e)
            return arr[s:e]
        def reverse(): arr.reverse(); return arr
        def sort_(fn=None):
            if fn and isinstance(fn, JSFunction):
                import functools
                def cmp(a, b):
                    r = self.call_function(fn, [a, b])
                    n = js_to_number(r)
                    return -1 if n < 0 else (1 if n > 0 else 0)
                arr.sort(key=functools.cmp_to_key(cmp))
            else:
                arr.sort(key=lambda x: js_to_string(x))
            return arr
        def join(sep=','):
            sep = js_to_string(sep)
            return sep.join(js_to_string(v) for v in arr)
        def concat(*others):
            result = arr[:]
            for o in others:
                if isinstance(o, list): result.extend(o)
                else: result.append(o)
            return result
        def includes(val, from_idx=0):
            for item in arr[int(js_to_number(from_idx)):]:
                if js_equals(item, val, strict=True): return True
            return False
        def index_of(val, from_idx=0):
            for i, item in enumerate(arr[int(js_to_number(from_idx)):], int(js_to_number(from_idx))):
                if js_equals(item, val, strict=True): return i
            return -1
        def last_index_of(val):
            for i in range(len(arr)-1, -1, -1):
                if js_equals(arr[i], val, strict=True): return i
            return -1
        def find(fn):
            for item in arr:
                if js_to_bool(self.call_function(fn, [item])): return item
            return UNDEFINED
        def find_index(fn):
            for i, item in enumerate(arr):
                if js_to_bool(self.call_function(fn, [item, i])): return i
            return -1
        def map_(fn):
            return [self.call_function(fn, [v, i, arr]) for i, v in enumerate(arr)]
        def filter_(fn):
            return [v for i, v in enumerate(arr) if js_to_bool(self.call_function(fn, [v, i, arr]))]
        def reduce_(fn, init=UNDEFINED):
            acc = init
            for i, v in enumerate(arr):
                if acc is UNDEFINED: acc = v; continue
                acc = self.call_function(fn, [acc, v, i, arr])
            return acc
        def reduce_right(fn, init=UNDEFINED):
            acc = init
            for i in range(len(arr)-1, -1, -1):
                if acc is UNDEFINED: acc = arr[i]; continue
                acc = self.call_function(fn, [acc, arr[i], i, arr])
            return acc
        def some_(fn):
            return any(js_to_bool(self.call_function(fn, [v, i, arr])) for i, v in enumerate(arr))
        def every_(fn):
            return all(js_to_bool(self.call_function(fn, [v, i, arr])) for i, v in enumerate(arr))
        def flat(depth=1):
            def _flat(a, d):
                r = []
                for x in a:
                    if isinstance(x, list) and d > 0: r.extend(_flat(x, d-1))
                    else: r.append(x)
                return r
            return _flat(arr, int(js_to_number(depth)))
        def flat_map(fn):
            result = []
            for i, v in enumerate(arr):
                r = self.call_function(fn, [v, i, arr])
                if isinstance(r, list): result.extend(r)
                else: result.append(r)
            return result
        def fill(val, start=0, end=None):
            s = int(js_to_number(start))
            e = len(arr) if end is None else int(js_to_number(end))
            for i in range(s, e): arr[i] = val
            return arr
        def at_(idx):
            i = int(js_to_number(idx))
            if i < 0: i = len(arr) + i
            return arr[i] if 0 <= i < len(arr) else UNDEFINED
        def keys_(): return list(range(len(arr)))
        def values_(): return arr[:]
        def entries_(): return [[i, v] for i, v in enumerate(arr)]
        def copy_within(target, start=0, end=None):
            t = int(js_to_number(target))
            s = int(js_to_number(start))
            e = len(arr) if end is None else int(js_to_number(end))
            arr[t:t+(e-s)] = arr[s:e]
            return arr

        methods = {
            'push': push, 'pop': pop, 'shift': shift, 'unshift': unshift,
            'splice': splice, 'slice': slice_, 'reverse': reverse, 'sort': sort_,
            'join': join, 'concat': concat, 'includes': includes, 'indexOf': index_of,
            'lastIndexOf': last_index_of, 'find': find, 'findIndex': find_index,
            'map': map_, 'filter': filter_, 'reduce': reduce_, 'reduceRight': reduce_right,
            'some': some_, 'every': every_, 'flat': flat, 'flatMap': flat_map,
            'fill': fill, 'at': at_, 'keys': keys_, 'values': values_,
            'entries': entries_, 'copyWithin': copy_within,
            'toString': lambda: ','.join(js_to_string(v) for v in arr),
            'forEach': lambda fn: [self.call_function(fn, [v, i, arr]) for i, v in enumerate(arr)],
        }
        return methods.get(key, UNDEFINED)

    def string_property(self, s, key):
        if key == 'length': return len(s)
        try:
            idx = int(key)
            return s[idx] if 0 <= idx < len(s) else UNDEFINED
        except ValueError: pass

        def char_at(i): return s[int(js_to_number(i))] if 0 <= int(js_to_number(i)) < len(s) else ''
        def char_code_at(i): 
            idx = int(js_to_number(i))
            return ord(s[idx]) if 0 <= idx < len(s) else float('nan')
        def index_of(sub, from_=0): return s.find(js_to_string(sub), int(js_to_number(from_)))
        def last_index_of(sub): return s.rfind(js_to_string(sub))
        def includes(sub): return js_to_string(sub) in s
        def starts_with(sub, pos=0): return s[int(js_to_number(pos)):].startswith(js_to_string(sub))
        def ends_with(sub, end=UNDEFINED):
            end_val = len(s) if end is UNDEFINED else int(js_to_number(end))
            return s[:end_val].endswith(js_to_string(sub))
        def split(sep=UNDEFINED, limit=UNDEFINED):
            if sep is UNDEFINED: return [s]
            sep_s = js_to_string(sep)
            if sep_s == '': parts = list(s)
            else: parts = s.split(sep_s)
            if limit is not UNDEFINED: parts = parts[:int(js_to_number(limit))]
            return parts
        def replace(search, repl):
            search_s = js_to_string(search)
            repl_s = js_to_string(repl) if not callable(repl) else None
            if callable(repl):
                m = re.search(re.escape(search_s), s)
                if m: return s[:m.start()] + js_to_string(self.call_function(repl, [m.group(), m.start(), s])) + s[m.end():]
                return s
            return s.replace(search_s, repl_s, 1)
        def replace_all(search, repl):
            search_s = js_to_string(search)
            repl_s = js_to_string(repl)
            return s.replace(search_s, repl_s)
        def slice_(start, end=UNDEFINED):
            st = int(js_to_number(start)) if start is not UNDEFINED else 0
            if st < 0: st = max(0, len(s) + st)
            if end is UNDEFINED: return s[st:]
            en = int(js_to_number(end))
            if en < 0: en = max(0, len(s) + en)
            return s[st:en]
        def substring(start, end=UNDEFINED):
            st = max(0, int(js_to_number(start)))
            en = len(s) if end is UNDEFINED else max(0, int(js_to_number(end)))
            if st > en: st, en = en, st
            return s[st:en]
        def pad_start(target_len, pad=' '):
            return js_to_string(s).rjust(int(js_to_number(target_len)), js_to_string(pad))
        def pad_end(target_len, pad=' '):
            return js_to_string(s).ljust(int(js_to_number(target_len)), js_to_string(pad))
        def repeat(n): return s * int(js_to_number(n))
        def match_(pattern):
            try: 
                matches = re.findall(js_to_string(pattern), s)
                return matches if matches else None
            except: return None
        def at_(idx):
            i = int(js_to_number(idx))
            if i < 0: i = len(s) + i
            return s[i] if 0 <= i < len(s) else UNDEFINED

        methods = {
            'length': len(s),
            'charAt': char_at, 'charCodeAt': char_code_at,
            'indexOf': index_of, 'lastIndexOf': last_index_of,
            'includes': includes, 'startsWith': starts_with, 'endsWith': ends_with,
            'split': split, 'replace': replace, 'replaceAll': replace_all,
            'slice': slice_, 'substring': substring,
            'toUpperCase': lambda: s.upper(), 'toLowerCase': lambda: s.lower(),
            'trim': lambda: s.strip(), 'trimStart': lambda: s.lstrip(), 'trimEnd': lambda: s.rstrip(),
            'padStart': pad_start, 'padEnd': pad_end,
            'repeat': repeat, 'match': match_, 'at': at_,
            'concat': lambda *args: s + ''.join(js_to_string(a) for a in args),
            'toString': lambda: s, 'valueOf': lambda: s,
            'fromCharCode': lambda code: chr(int(js_to_number(code))),
        }
        return methods.get(key, UNDEFINED)

    def number_property(self, n, key):
        def to_fixed(digits=0):
            return format(float(n), f'.{int(js_to_number(digits))}f')
        def to_string(base=10):
            base = int(js_to_number(base))
            if base == 10: return js_to_string(n)
            return format(int(n), 'b' if base==2 else ('o' if base==8 else 'x'))
        def to_precision(p):
            return format(float(n), f'.{int(js_to_number(p))-1}e')
        return {'toFixed': to_fixed, 'toString': to_string, 'toPrecision': to_precision,
                'toLocaleString': lambda: str(n)}.get(key, UNDEFINED)

    def call_function(self, fn, args, this=None):
        if fn is UNDEFINED or fn is None:
            raise ThrowSignal(f"TypeError: {fn} is not a function")
        # Native Python callable
        if callable(fn) and not isinstance(fn, JSFunction):
            try: return fn(*args)
            except TypeError: return fn(*args[:fn.__code__.co_argcount if hasattr(fn,'__code__') else len(args)])
        if isinstance(fn, JSFunction):
            fn_env = Environment(fn.closure)
            if this is not None: fn_env.define('this', this)
            # Bind parameters
            for i, param_node in enumerate(fn.params):
                ptype = param_node[0]
                pname = param_node[1]
                pdefault = param_node[2] if len(param_node) > 2 else None
                if ptype == 'rest_param':
                    fn_env.define(pname, args[i:])
                else:
                    val = args[i] if i < len(args) else UNDEFINED
                    if val is UNDEFINED and pdefault is not None:
                        val = self.eval_expr(pdefault, fn_env)
                    fn_env.define(pname, val)
            # Execute body
            try:
                body = fn.body
                if body[0] == 'block':
                    self.exec_block(body[1], fn_env)
                elif body[0] == 'return':
                    return self.eval_expr(body[1], fn_env) if body[1] else UNDEFINED
                else:
                    self.exec_stmt(body, fn_env)
            except ReturnSignal as r:
                return r.val
            return UNDEFINED
        raise ThrowSignal(f"TypeError: {fn} is not a function")

    def construct(self, cls, args, env):
        if callable(cls) and not isinstance(cls, (JSFunction, JSClass)):
            return cls(*args)
        if isinstance(cls, JSClass):
            obj = JSObject(cls)
            constructor = cls.methods.get('constructor')
            if constructor:
                obj.props['__proto__'] = cls.name
                self.call_function(constructor, args, this=obj)
            return obj
        if isinstance(cls, JSFunction):
            # function used as constructor
            obj = {}
            self.call_function(cls, args, this=obj)
            return obj
        # Fallback: treat as factory
        if callable(cls):
            return cls(*args)
        return {}


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_js(source: str):
    tokens = tokenize(source)
    parser = Parser(tokens)
    ast = parser.parse_program()
    interp = Interpreter()
    interp.run(ast)
    return '\n'.join(interp.output)


def main():
    parser = argparse.ArgumentParser(
        description='ThunderJS — Full JavaScript Interpreter in Pure Python')
    parser.add_argument('file', nargs='?', help='Path to .js file')
    parser.add_argument('-c', '--code', help='JS code string to execute directly')
    parser.add_argument('-b', '--benchmark', action='store_true',
                        help='Show execution time')
    args = parser.parse_args()

    # Get JS source
    if args.file:
        try:
            with open(args.file) as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
    elif args.code:
        source = args.code
    elif not sys.stdin.isatty():
        source = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    start = time.perf_counter()
    try:
        output = run_js(source)
        if output:
            print(output)
    except Exception as e:
        print(f"Runtime Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.benchmark:
        elapsed = (time.perf_counter() - start) * 1000
        print(f"\n[⚡ ThunderJS] Execution Time: {elapsed:.2f} ms", file=sys.stderr)


if __name__ == '__main__':
    main()