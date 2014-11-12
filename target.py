class Object(object):
    _immutable_ = True

class Answer(Object):
    _immutable_ = True
    def __init__(self, val):
        self._val = val

    def val(self):
        return self._val

class Fn(Object):
    _immutable_ = True
    def invoke(self, args):
        raise NotImplementedError()

class HandlerFn(Object):
    _immutable_ = True
    def handle(self, effect, k):
        raise NotImplementedError()


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
    return x.with_env(env).interpret()


def thunk(expr, env):
    return ThunkFn(expr, env)

class ThunkFn(Fn):
    _immutable_ = True
    def __init__(self, expr, env):
        self._expr = expr
        self._env = env

    def invoke(self, args):
        return interpret(self._expr, self._env)

def interpret_effect(x, env):
    assert isinstance(x, Syntax) and isinstance(env, Env)
    f = thunk(x, env)
    while True:
        x = f.invoke([])
        if isinstance(x, Fn):
            f = x
            continue
        return x

## End Interpret and Thunks

## Handle With

def handle_with(handler, effect, k):
    rec = HandleRecFn(handler, k)
    if isinstance(effect, Fn):
        return CallEffectFn(rec, effect)
    else:
        val = handler.handle(effect, k)
        if val:
            return val
        else:
            raise NotImplementedError

class CallEffectFn(Fn):
    _immutable_ = True
    def __init__(self, rec, effect):
        self._rec = rec
        self._effect = effect

    def invoke(self, args):
        return self._rec.invoke([self._effect.invoke([])])


class HandleRecFn(Fn):
    _immutable_ = True
    def __init__(self, handler, k):
        self._handler = handler
        self._k = k

    def invoke(self, args):
        return handle_with(self._handler, args[0], self._k)

## End Handle With

## Default Handler

class DefaultHandler(HandlerFn):
    _immutable_ = True
    def handle(self, effect, k):
        if isinstance(effect, Answer):
            return DefaultHandlerFn(k, effect.val())

default_handler = DefaultHandler()

class DefaultHandlerFn(Fn):
    _immutable_ = True
    def __init__(self, k, val):
        self._val = val
        self._k = k

    def invoke(self, args):
        return self._k.invoke([self._val])

## End Default Handler

def handle(effect, k):
    return handle_with(default_handler, effect, k)

class Env(Object):
    _immutable_ = True
    def __init__(self, locals, globals):
        self._locals = locals
        self._globals = globals

    def lookup_local(self, nm):
        return self._locals.get(nm, None)

def lookup(env, sym):
    val = env.lookup_local(sym)
    if val is not None:
        return Answer(val)
    raise NotImplementedError()


class Syntax(Object):
    _immutable_ = True
    def interpret(self):
        raise NotImplementedError()

class Constant(Syntax):
    _immutable_ = True
    def __init__(self, value):
        self._val = value

    def with_env(self, env):
        return self

    def interpret(self):
        return Answer(self._val)

class Lookup(Syntax):
    _immutable_ = True
    def __init__(self, name, env = None):
        self._name = name
        self._env = env

    def with_env(self, env):
        return Lookup(self._name, env)

    def interpret(self):
        return lookup(self._env, self._name)

## If Syntax

class If(Syntax):
    _immutable_ = True
    def __init__(self, w_test, w_then, w_else, w_env = None):
        self._w_test = w_test
        self._w_then = w_then
        self._w_else = w_else
        self._w_env = w_env

    def with_env(self, env):
        return If(self._w_test, self._w_then, self._w_else, env)

    def interpret(self):
        return handle(thunk(self._w_test, self._w_env),
                      IfHandler(self._w_then, self._w_else, self._w_env))


class IfHandler(Fn):
    _immutable_ = True
    def __init__(self, *args):
        self._args = args

    def invoke(self, args):
        then, els, env = self._args
        return thunk(then if not (args[0] is nil or args[0] is false) else els, env)

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

    for x in range(100000):
        print interpret_effect(ast, Env({"x": false}, None)).val()

def entry_point(argv):
    run(argv)
    return 0

def target(*args):
    return entry_point, None

if __name__ == "__main__":
    import sys
    #run([1])

def foo(x, y, env):
    if effect(y(x), 4):
        return x

from byteplay import *
from pprint import pprint
c = Code.from_code(foo.func_code)
pprint(c.code)