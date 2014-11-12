
from effect_transform import cps
from effects import *

## Object System

class Bool(Object):
    _immutable_ = True
    def __init__(self):
        pass

true = Bool()
false = Bool()

class Integer(Object):
    _immutable_ = True
    def __init__(self, int_val):
        self._int_val = int_val

    def int_val(self):
        return self._int_val


class Nil(Object):
    _immutable_ = True
    def __init__(self):
        pass

nil = Nil()


## End Object System

## Interpret and Thunks

def interpret(x, env):
    assert isinstance(x, Syntax)
    jitdriver.jit_merge_point(ast=x, env=env)
    return x.interpret_(env)


def thunk(expr, env):
    return ThunkFn(expr, env)

class ThunkFn(Thunk):
    _immutable_ = True
    def __init__(self, expr, env):
        self._expr = expr
        self._env = env

    def execute_thunk(self):
        return interpret(self._expr, self._env)

def interpret_effect(x, env):
    f = thunk(x, env)
    while True:
        x = f.execute_thunk()
        if isinstance(x, Thunk):
            f = x
            continue
        if isinstance(x, Answer):
            return x



## End Interpret and Thunks

class Env(Object):
    _immutable_ = True
    def __init__(self, locals, globals):
        self._locals = locals
        self._globals = globals

    def lookup_local(self, nm):
        return self._locals.get(nm, None)

    def lookup_(self, nm):
        return Answer(self._locals.get(nm, None))

def lookup_(env, sym):
    val = env.lookup_local(sym)
    if val is not None:
        return Answer(val)
    raise NotImplementedError()


class Syntax(Object):
    _immutable_ = True
    def interpret_(self, env):
        raise NotImplementedError()

class Constant(Syntax):
    _immutable_ = True
    def __init__(self, value):
        self._val = value

    def interpret_(self, env):
        return Answer(self._val)

class Lookup(Syntax):
    _immutable_ = True
    def __init__(self, name, env = None):
        self._name = name

    @cps
    def interpret_(self, env):
        nm = self._name
        result = env.lookup_(nm)
        return result

## If Syntax

class If(Syntax):
    _immutable_ = True
    def __init__(self, w_test, w_then, w_else):
        self._w_test = w_test
        self._w_then = w_then
        self._w_else = w_else

    @cps
    def interpret_(self, env):
        tst = self._w_test.interpret_(env)
        if not (tst is nil or tst is false):
            ret = self._w_then.interpret_(env)
            return ret
        else:
            ret = self._w_else.interpret_(env)
            return ret

## End If Syntax

ast1 = If(Lookup("x"),
             Constant(Integer(42)),
             Constant(nil))

ast2 = If(Lookup("x"),
             Constant(Integer(43)),
             Constant(nil))

## JIT stuff

from rpython.rlib.jit import JitDriver
jitdriver = JitDriver(greens=['ast'],
        reds=['env'])

def jitpolicy(driver):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()


def run(argv):
    ast = [ast1, ast2][len(argv)]

    result = None
    for x in range(10000):
        result = interpret_effect(ast, Env({"x": true}, None))
    print result

def entry_point(argv):
    run(argv)
    return 0

def target(*args):
    return entry_point, None

if __name__ == "__main__":
    import sys
    run([1])
