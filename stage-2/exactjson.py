"""Stack-based JSON operations and compact, exact finite decimal values.

No binary floats or recursion enter the accepted-value lifetime.
"""
import json
import re
import sys
from dataclasses import dataclass
from functools import total_ordering

sys.set_int_max_str_digits(0)
NUMBER = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')


@total_ordering
@dataclass(frozen=True, eq=False)
class Number:
    sign: int
    digits: str
    exponent: int

    @classmethod
    def parse(cls, raw):
        raw = str(raw)
        if not NUMBER.fullmatch(raw):
            raise ValueError('Not a finite JSON number')
        sign = -1 if raw.startswith('-') else 1
        raw = raw.lstrip('-')
        parts = re.split('[eE]', raw)
        exponent = int(parts[1]) if len(parts) == 2 else 0
        mantissa = parts[0]
        if '.' in mantissa:
            left, right = mantissa.split('.')
            exponent -= len(right)
            mantissa = left + right
        digits = mantissa.lstrip('0')
        if not digits:
            return cls(0, '0', 0)
        tail = len(digits) - len(digits.rstrip('0'))
        return cls(sign, digits.rstrip('0'), exponent + tail)

    @property
    def integral(self):
        return self.sign == 0 or self.exponent >= 0

    def compare(self, other):
        if type(other) is int:
            other = Number.parse(other)
        if not isinstance(other, Number):
            return NotImplemented
        if self.sign != other.sign:
            return (self.sign > other.sign) - (self.sign < other.sign)
        if not self.sign:
            return 0
        a, b = len(self.digits) + self.exponent, len(other.digits) + other.exponent
        if a != b:
            return self.sign * ((a > b) - (a < b))
        size = max(len(self.digits), len(other.digits))
        a, b = self.digits.ljust(size, '0'), other.digits.ljust(size, '0')
        return self.sign * ((a > b) - (a < b))

    def __eq__(self, other):
        return self.compare(other) == 0

    def __lt__(self, other):
        c = self.compare(other)
        return NotImplemented if c is NotImplemented else c < 0

    def __hash__(self):
        return hash((self.sign, self.digits, self.exponent))

    def small_int(self, maximum):
        if not self.integral or self < 0 or self > maximum:
            raise ValueError('Integer outside conversion range')
        return self.sign * int(self.digits) * 10 ** self.exponent

    def text(self):
        if self.sign == 0:
            return '0'
        prefix = '-' if self.sign < 0 else ''
        if 0 <= self.exponent <= 15:
            return prefix + self.digits + '0' * self.exponent
        return prefix + self.digits + 'e' + str(self.exponent)


@dataclass(frozen=True)
class ZeroRun:
    count: int


@total_ordering
@dataclass(frozen=True, eq=False)
class IntegerSum:
    """Two positive integer coefficients separated by a compact zero span.

    This response-only value never enters persisted state or request identity.
    Comparing it takes time proportional to supplied coefficient text, not to
    the distance between exponents. Serialization alone expands the zero span.
    """
    high: str
    gap: int
    low: str
    exponent: int

    def compare(self, other):
        if type(other) is int:
            other = Number.parse(other)
        if not isinstance(other, Number):
            return NotImplemented
        if other.sign <= 0:
            return 1
        width = len(self.high) + self.gap + len(self.low)
        magnitude = width + self.exponent
        theirs = len(other.digits) + other.exponent
        if magnitude != theirs:
            return (magnitude > theirs) - (magnitude < theirs)
        position = 0
        for part in (self.high, ZeroRun(self.gap), self.low):
            size = part.count if isinstance(part, ZeroRun) else len(part)
            right = other.digits[position:position + size]
            if isinstance(part, ZeroRun):
                if right.strip('0'):
                    return -1
            else:
                left = part[:len(right)]
                if left != right:
                    return (left > right) - (left < right)
                if part[len(right):].strip('0'):
                    return 1
            position += size
        return -1 if other.digits[position:].strip('0') else 0

    def __eq__(self, other):
        return self.compare(other) == 0

    def __lt__(self, other):
        result = self.compare(other)
        return NotImplemented if result is NotImplemented else result < 0


def add_digits(left, right):
    """Linear decimal addition without converting an unbounded coefficient."""
    pieces, carry, offset = [], 0, 0
    while offset < max(len(left), len(right)):
        def block(text):
            end = max(0, len(text) - offset)
            return int(text[max(0, end - 9):end] or '0')
        carry, digit = divmod(block(left) + block(right) + carry, 1_000_000_000)
        pieces.append(f'{digit:09d}')
        offset += 9
    if carry:
        pieces.append(str(carry))
    return ''.join(reversed(pieces)).lstrip('0') or '0'


def add_integers(left, right):
    left = left if isinstance(left, Number) else Number.parse(left)
    right = right if isinstance(right, Number) else Number.parse(right)
    if not (left.integral and right.integral and left > 0 and right > 0):
        raise ValueError('Expected positive integer operands')
    if left.exponent < right.exponent:
        left, right = right, left
    gap = left.exponent - right.exponent - len(right.digits)
    if gap > 65536:
        return IntegerSum(left.digits, gap, right.digits, right.exponent)
    # Overlapping/nearby coefficient spans are bounded by the input size plus
    # this small representation threshold. It does not cap the accepted value.
    digits = add_digits(left.digits + '0' * (left.exponent - right.exponent), right.digits)
    return Number.parse(digits + 'e' + str(right.exponent))


def loads(raw):
    s = raw.decode('utf-8') if isinstance(raw, bytes) else raw
    i, n, stack, root, complete = 0, len(s), [], None, False

    def ws(pos):
        while pos < n and s[pos] in ' \t\r\n':
            pos += 1
        return pos

    def atom(pos):
        if pos >= n:
            raise ValueError('Missing JSON value')
        c = s[pos]
        if c == '"':
            value, end = json.decoder.scanstring(s, pos + 1, True)
            return value, end, None
        if c == '{':
            return {}, pos + 1, 'key0'
        if c == '[':
            return [], pos + 1, 'value0'
        for word, value in [('true', True), ('false', False), ('null', None)]:
            if s.startswith(word, pos):
                return value, pos + len(word), None
        match = NUMBER.match(s, pos)
        if match:
            return Number.parse(match.group()), match.end(), None
        raise ValueError('Invalid JSON value')

    while True:
        i = ws(i)
        if not stack:
            if complete:
                if i != n:
                    raise ValueError('Trailing JSON data')
                return root
            root, i, mode = atom(i)
            complete = True
            if mode:
                stack.append([root, mode, None])
            continue
        frame = stack[-1]
        target, mode, key = frame
        if mode in ('key0', 'key'):
            if mode == 'key0' and i < n and s[i] == '}':
                stack.pop(); i += 1; continue
            if i >= n or s[i] != '"':
                raise ValueError('Expected object key')
            frame[2], i = json.decoder.scanstring(s, i + 1, True)
            i = ws(i)
            if i >= n or s[i] != ':':
                raise ValueError('Expected colon')
            i += 1; frame[1] = 'objectvalue'; continue
        if mode in ('value0', 'value', 'objectvalue'):
            if mode == 'value0' and i < n and s[i] == ']':
                stack.pop(); i += 1; continue
            value, i, child = atom(i)
            if type(target) is dict:
                target[key] = value
            else:
                target.append(value)
            frame[1] = 'after'
            if child:
                stack.append([value, child, None])
            continue
        end = '}' if type(target) is dict else ']'
        if i < n and s[i] == end:
            stack.pop(); i += 1; continue
        if i >= n or s[i] != ',':
            raise ValueError('Expected comma or container end')
        i += 1
        frame[1] = 'key' if type(target) is dict else 'value'


def chunks(value, canonical=False, sparse=False):
    stack = [('value', value)]
    while stack:
        kind, obj = stack.pop()
        if kind == 'literal':
            yield obj
        elif obj is None:
            yield 'null'
        elif type(obj) is bool:
            yield 'true' if obj else 'false'
        elif isinstance(obj, Number):
            yield obj.text()
        elif isinstance(obj, IntegerSum):
            yield obj.high
            if sparse:
                yield ZeroRun(obj.gap)
            else:
                count = obj.gap
                zeros = '0' * 65536
                while count:
                    size = min(count, len(zeros))
                    yield zeros[:size]
                    count -= size
            yield obj.low
            if obj.exponent:
                yield 'e' + str(obj.exponent)
        elif type(obj) is int:
            yield Number.parse(obj).text()
        elif type(obj) is str:
            yield json.dumps(obj, ensure_ascii=True)
        elif type(obj) is list:
            yield '['
            stack.append(('literal', ']'))
            for j in range(len(obj) - 1, -1, -1):
                stack.append(('value', obj[j]))
                if j:
                    stack.append(('literal', ','))
        elif type(obj) is dict:
            yield '{'
            stack.append(('literal', '}'))
            keys = sorted(obj) if canonical else list(obj)
            for j in range(len(keys) - 1, -1, -1):
                key = keys[j]
                if type(key) is not str:
                    raise ValueError('JSON object key must be string')
                stack.extend([('value', obj[key]), ('literal', ':'), ('value', key)])
                if j:
                    stack.append(('literal', ','))
        else:
            raise ValueError('Not a JSON value')


def dumps(value, canonical=False):
    return ''.join(chunks(value, canonical)).encode('ascii')


def clone(value):
    if type(value) not in (dict, list):
        return value
    result = {} if type(value) is dict else []
    stack = [(value, result)]
    while stack:
        source, target = stack.pop()
        entries = source.items() if type(source) is dict else enumerate(source)
        for key, child in entries:
            copied = {} if type(child) is dict else [] if type(child) is list else child
            if type(target) is dict:
                target[key] = copied
            else:
                target.append(copied)
            if type(child) in (dict, list):
                stack.append((child, copied))
    return result


def equal(left, right):
    pending = [(left, right)]
    while pending:
        a, b = pending.pop()
        if isinstance(a, Number) or type(a) is int:
            if not (isinstance(b, Number) or type(b) is int) or a != b:
                return False
        elif type(a) is not type(b):
            return False
        elif type(a) is dict:
            if a.keys() != b.keys():
                return False
            pending.extend((v, b[k]) for k, v in a.items())
        elif type(a) is list:
            if len(a) != len(b):
                return False
            pending.extend(zip(a, b))
        elif a != b:
            return False
    return True
