import inspect
import re
import tokenize
from collections import namedtuple
from functools import partial
from io import BytesIO
from textwrap import indent, wrap

from pygments import highlight
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.lexers.data import JsonLexer

import click

ArgumentInfo = namedtuple('ArgumentInfo', ['code', 'interesting'])
ValueInfo = namedtuple('ValueInfo', ['display', 'description'])


def style(s, pad=0, limit=1000, **kwargs):
    return click.style(str(s).rjust(pad)[:limit], **kwargs)


green = partial(style, fg='green')
blue = partial(style, fg='blue')
magenta = partial(style, fg='magenta')
cyan = partial(style, fg='cyan')
yellow = partial(style, fg='yellow')
dim = partial(style, fg='white', dim=True)


class Debug:
    def __init__(self):
        self._formatter = Terminal256Formatter(style='vim')
        self._lexer = JsonLexer()

    def __call__(self, *args, **kwargs):
        curframe = inspect.currentframe()
        frames = inspect.getouterframes(curframe, context=20)
        call_frame = frames[1]
        code_lines = []
        for line in range(call_frame.index, 0, -1):
            new_line = call_frame.code_context[line]
            code_lines.append(new_line)
            # TODO escape multiline strings incase they include "debug("
            if re.search(' *debug\(', new_line):
                # TODO cope with failure and assume one line debug
                break

        code_lines.reverse()

        position = f'{call_frame.filename}:{call_frame.lineno - len(code_lines)}'
        print(f'{yellow(position)} {green(call_frame.function)}')
        for i, code_arg, arg in zip(range(1000), self._parse_code(code_lines), self._format_arg(args)):
            # TODO truncate code
            key = code_arg.code if code_arg.interesting else f'arg {i + 1}'
            descr = ' '.join(f'{blue(k)}{dim("=")}{cyan(v)}' for k, v in arg.description)
            print(f'  {green(key)} {descr}')
            print(self._highlight(indent(arg.display, prefix=' ' * 4)))

    def _highlight(self, s):
        # is this slow?
        return highlight(s, self._lexer, self._formatter).rstrip('\n')

    def _parse_code(self, code_lines):
        code = ''.join(code_lines)
        titer = tokenize.tokenize(BytesIO(code.encode()).readline)
        for t in titer:
            if t.type == tokenize.NAME and t.string == 'debug':
                next(titer)
                break
        tokens, interesting = [], False
        parenth = 0
        for t in titer:
            # print(t)
            if not parenth and t.type == tokenize.OP and t.string in ',)':
                code = ''.join(t.string for t in tokens).replace('\n', '')
                yield ArgumentInfo(code, interesting)
                if t.string == ')':
                    break
                tokens, interesting = [], False
                continue
            tokens.append(t)
            if t.type == tokenize.NAME or (t.type == tokenize.STRING and t.string.startswith('f')):
                interesting = True
            elif t.type == tokenize.OP:
                if t.string in '([{':
                    parenth += 1
                elif t.string in ')]}':
                    parenth -= 1

    def _format_arg(self, args):
        for arg in args:
            if isinstance(arg, str) and '\n' in arg:
                display = f'"""{arg}"""'
            else:
                # format dicts, sets lists, ordered dicts like JSON
                # code with django querysets, numpy arrays, pandas
                display = repr(arg)
            descr = [('type', arg.__class__.__name__)]
            if hasattr(arg, '__len__'):
                descr.append(('len', len(arg)))
            # TODO indent
            yield ValueInfo(display, descr)


start_end = {
    list: ('[', ']'),
    tuple: ('(', ')'),
    set: ('{', '}'),
}


def priter(v, depth=0, suffix='', step=4):
    # print(repr(v), depth, repr(suffix))
    if isinstance(v, (list, tuple, set)):
        start, end = start_end[type(v)]
        yield start, depth
        for v_ in v:
            yield from priter(v_, depth + step, ',', step)
        yield end + suffix, depth
    elif isinstance(v, dict):
        yield '{', depth
        for k, v_ in v.items():
            pv = priter(v_, depth + step, ',', step)
            yield f'{k!r}: {next(pv)[0]}', depth + step
            yield from pv
        yield '}' + suffix, depth
    elif isinstance(v, str) and ('\n' in v or len(v) > 70):
        yield '(', depth
        for line in v.split('\n'):
            for line_ in wrap(line):
                # TODO add newline to all but last
                yield repr(line_), depth + step
        yield ')' + suffix, depth
    else:
        # TODO ints and floats in key range to dates
        # code with django querysets, numpy arrays, pandas
        yield f'{v!r}' + suffix, depth


def pretty(v):
    output = []
    for v_, depth in priter(v):
        output.append(indent(v_, ' ' * depth))
    return '\n'.join(output)


debug = Debug()
