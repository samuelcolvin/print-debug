import ast
import inspect
import re
import tokenize
from io import BytesIO


def split(code):
    titer = tokenize.tokenize(BytesIO(code.encode()).readline)
    for t in titer:
        if t.type == tokenize.NAME and t.string == 'debug':
            next(titer)
            break
    args = []
    tokens = []
    parenth = 0
    for t in titer:
        # print(t)
        if not parenth and t.type == tokenize.OP and t.string in ',)':
            args.append(''.join(t.string for t in tokens).replace('\n', ''))
            # print(args[-1])
            if t.string == ')':
                break
            else:
                tokens = []
                continue
        tokens.append(t)
        if t.type == tokenize.OP:
            if t.string in '([{':
                parenth += 1
            elif t.string in ')]}':
                parenth -= 1
    return args
    # args = []
    # for chunk in chunks:
    #     print(repr(tokenize.untokenize(chunk)))
        # args.append(arg)
        # print(arg)
        # print([t.string for t in chunk])
        # print('--------------------------------')


def debug(*args, apple=1):
    curframe = inspect.currentframe()
    frames = inspect.getouterframes(curframe, context=20)
    call_frame = frames[1]
    call_lines = []
    for line in range(call_frame.index, 0, -1):
        new_line = call_frame.code_context[line]
        call_lines.append(new_line)
        if re.search('debug *\(', new_line):
            break
    call_lines.reverse()
    code = ''.join(call_lines)
    args_code = split(code)
    ast_func = ast.parse(code).body[0].value
    elements = ast_func.args
    print(f'{call_frame.filename}:{call_frame.lineno - len(call_lines)} {call_frame.function}')
    for i, arg in enumerate(args):
        el = elements[i]
        code = args_code[i]
        if isinstance(el, ast.Name):
            print(f'  {el.id}={arg} ({arg.__class__.__name__})')
        elif isinstance(el, ast.Str):
            if '\n' in arg:
                print(f'"{arg}" ({arg.__class__.__name__} len={len(arg)})')
            else:
                print(f'  {arg} ({arg.__class__.__name__} len={len(arg)})')
        elif isinstance(el, (ast.Num, ast.List, ast.Dict, ast.Set)):
            print(f'  {arg} ({arg.__class__.__name__})')
        elif isinstance(el, (ast.Call, ast.Compare)):
            # # this probably has to be replaced by a best guess ast > code method
            # end = -2
            # try:
            #     next_line, next_offset = arg_offsets[i + 1]
            #     if next_line == el.lineno:
            #         end = next_offset
            # except IndexError:
            #     pass
            # name = call_lines[el.lineno - 1][el.col_offset:end]
            # name = name.strip(' ,')
            print(f'  {code}={arg} ({arg.__class__.__name__})')
        else:
            print(ast.dump(el))
            print(f'  {arg} ({arg.__class__.__name__})')
    kw_arg_names = {}
    for kw in ast_func.keywords:
        if isinstance(kw.value, ast.Name):
            kw_arg_names[kw.arg] = kw.value.id
