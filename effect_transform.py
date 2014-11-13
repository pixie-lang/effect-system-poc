from byteplay import *
from pprint import pprint
import dis as dis
import types
from effects import *


iname = 0
SELF_NAME = "__SELF__"
RET_NAME = "__RET__"
BUILDING_NAME = "__BUILDING__"
STATE_NAME = "_K_state"

class BytecodeRewriter(object):
    def __init__(self, code):
        assert isinstance(code, list)
        self._code = code
        self._i = 0

    def set_position(self, i):
        self._i = i

    def reset(self):
        self.set_position(0)

    def insert(self, op, arg=None):
        self._code.insert(self._i, (op, arg))
        self._i += 1

    def next(self):
        self._i += 1
        return self

    def __getitem__(self, item):
        return self._code[self._i + item]

    def __setitem__(self, key, value):
        assert isinstance(value, tuple)
        self._code[self._i + key] = value

    def get_code(self):
        return self._code

    def __len__(self):
        return len(self._code)

    def inbounds(self):
        return 0 <= self._i < len(self)


def cps(f):
    global iname
    c = Code.from_code(f.func_code)

    iname += 1
    cls_name = "_K_" + str(iname) + "_class"

    code = BytecodeRewriter(c.code)
    ret_points = []
    locals = set(f.func_code.co_varnames[:f.func_code.co_argcount])

    while code.inbounds():
        nm, arg = code[0]

        print nm, arg, locals

        if nm == STORE_FAST:
            locals.add(arg)

        if nm == LOOKUP_METHOD:
            code[0] = (LOAD_ATTR, arg)

        if nm == CALL_METHOD:
            code[0] = (CALL_FUNCTION, arg)

        if nm == SETUP_LOOP:
            code[0] = (NOP, None)

        if nm == POP_BLOCK:
            code[0] = (NOP, None)

        if nm == BREAK_LOOP:
            raise AssertionError("Can't use break inside a CPS function")

        if nm == CONTINUE_LOOP:
            raise AssertionError("Can't use continue inside a CPS function")

        if nm == CALL_METHOD or nm == CALL_FUNCTION:
            op, _ = code[1]
            if op == RETURN_VALUE:
                print "SKIPPING RETURN"
                code.next().next()
                continue

            op, arg = code[- (arg + 1)]
            print op, arg
            if (op == LOAD_ATTR or op == LOAD_GLOBAL) and arg.endswith("_") and not arg.startswith("_"):
                code.next()
                code.insert(STORE_FAST, RET_NAME)
                code.insert(LOAD_GLOBAL, cls_name)
                code.insert(CALL_FUNCTION, 0)
                code.insert(STORE_FAST, BUILDING_NAME)
                code.insert(LOAD_FAST, BUILDING_NAME)
                code.insert(LOAD_CONST, len(ret_points) + 1)
                code.insert(LOAD_FAST, BUILDING_NAME)
                code.insert(STORE_ATTR, STATE_NAME)
                for x in locals:
                    code.insert(LOAD_FAST, x)
                    code.insert(LOAD_FAST, BUILDING_NAME)
                    code.insert(STORE_ATTR, "_K_" + str(iname) + "_" + x)

                code.insert(LOAD_FAST, BUILDING_NAME)
                code.insert(LOAD_CONST, handle)
                code.insert(LOAD_FAST, RET_NAME)
                code.insert(LOAD_FAST, BUILDING_NAME)
                code.insert(CALL_FUNCTION, 2)

                code.insert(RETURN_VALUE, None)

                lbl = Label()
                ret_points.append(lbl)
                code.insert(lbl, None)
                code.insert(LOAD_FAST, RET_NAME)

                for x in locals:
                    code.insert(LOAD_FAST, BUILDING_NAME)
                    code.insert(LOAD_ATTR, "_K_" + str(iname) + "_" + x)
                    code.insert(STORE_FAST, x)

                continue
                print op, arg

        if nm == RETURN_VALUE:
            code.insert(STORE_FAST, RET_NAME)
            code.insert(LOAD_CONST, answer)
            code.insert(LOAD_FAST, RET_NAME)
            code.insert(CALL_FUNCTION, 1)

        code.next()



    code.reset()
    for x in f.func_code.co_varnames[:f.func_code.co_argcount]:
        code.insert(LOAD_FAST, BUILDING_NAME)
        code.insert(LOAD_ATTR, "_K_" + str(iname) + "_" +  x)
        code.insert(STORE_FAST, x)

    state_idx = 1
    for lbl in ret_points:
        code.reset()
        code.insert(LOAD_FAST, BUILDING_NAME)
        code.insert(LOAD_ATTR, STATE_NAME)
        code.insert(LOAD_CONST, state_idx)
        code.insert(COMPARE_OP, "==")
        exit_lbl = Label()
        code.insert(POP_JUMP_IF_FALSE, exit_lbl)
        code.insert(JUMP_ABSOLUTE, lbl)
        code.insert(exit_lbl, None)

        state_idx += 1


    pprint(code.get_code())
    c = Code(code=code.get_code(), freevars=[], args=[BUILDING_NAME, RET_NAME],
             varargs=False, varkwargs=False, newlocals=True, name=f.func_code.co_name,
             filename=f.func_code.co_filename, firstlineno=f.func_code.co_firstlineno,
             docstring=f.func_code.__doc__)

    try:
        new_func = types.FunctionType(c.to_code(), f.func_globals, "step")
    except:
        print f.func_code.co_name
        pprint(code.get_code())
        raise

    dis.dis(new_func)

    f.func_globals[cls_name] = type(cls_name, (Continuation,), {"step": new_func, "_immutable_": True})

    code = [(LOAD_GLOBAL, cls_name),
            (CALL_FUNCTION, 0),
            (STORE_FAST, BUILDING_NAME),
        (LOAD_CONST, 0),
        (LOAD_FAST, BUILDING_NAME),
        (STORE_ATTR, STATE_NAME)]

    for x in range(f.func_code.co_argcount):
        code.append((LOAD_FAST, f.func_code.co_varnames[x]))
        code.append((LOAD_FAST, BUILDING_NAME))
        code.append((STORE_ATTR, "_K_" + str(iname) + "_" +  f.func_code.co_varnames[x]))

    code.append((LOAD_FAST, BUILDING_NAME))
    code.append((LOAD_ATTR, "step"))
    code.append((LOAD_CONST, None))
    code.append((CALL_FUNCTION, 1))

    code.append((RETURN_VALUE, None))


    c = Code(code=code, freevars=[], args=f.func_code.co_varnames[:f.func_code.co_argcount],
             varargs=False, varkwargs=False, newlocals=True, name=f.func_code.co_name,
             filename=f.func_code.co_filename, firstlineno=f.func_code.co_firstlineno,
             docstring=f.func_code.__doc__)
    f.func_code = c.to_code()

    return f


@cps
def test(r):
    x = invoke_(42)
    return x
