
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

def clone_append(arr, itm):
    new_array = [None] * (len(arr) + 1)
    x = 0
    while x < len(arr):
        new_array[x] = arr[x]
        x += 1
    new_array[x] = itm
    return new_array

@cps
def interpret_items_(args_w, env):
    new_args = []
    idx = 0

    while idx < len(args_w):
        result = args_w[idx].interpret_(env)
        new_args = clone_append(new_args, result)
        idx += 1

    return new_args


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
        return self._locals.get(nm)

    def lookup_(self, nm):
        return Answer(self._locals[nm])

    def with_locals(self, names, values):
        locals = self._locals.copy()
        for x in range(len(names)):
            locals[names[x]] = values[x]

        return Env(locals, self._globals)

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
    def __init__(self, name):
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
        ret = None
        if not (tst is nil or tst is false):
            return self._w_then.interpret_(env)
        else:
            return self._w_else.interpret_(env)

class Do(Syntax):
    _immutable_ = True
    def __init__(self, exprs):
        self._exprs_w = exprs

    @cps
    def interpret_(self, env):
        x = 0
        result = nil
        while x < len(self._exprs_w):
            result = self._exprs_w[x].interpret_(env)
            x += 1

        return result

class Call(Syntax):
    _immutable_ = True
    def __init__(self, fn, args):
        self._w_fn = fn
        self._args_w = args

    @cps
    def interpret_(self, env):
        fn = self._w_fn.interpret_(env)
        args_w = self._args_w
        itms = interpret_items_(args_w, env)
        return fn.invoke_(itms)

class RecurHandler(Handler):
    def __init__(self, f, env):
        pass

    def handle(self, effect, k):
        pass



class Add(Fn):
    def __index__(self):
        pass

    def invoke_(self, args):
        return Answer(Integer(args[0].int_val() + args[1].int_val()))


class EQ(Fn):
    def __index__(self):
        pass

    def invoke_(self, args):
        result = args[0].int_val() == args[1].int_val()
        return Answer(true if result else false)

class FnLiteral(Syntax):
    def __init__(self, fn):
        self._w_fn = fn

    def interpret_(self, env):
        return Answer(self._w_fn.with_env(env))

class PixieFunction(Fn):
    _immutable_ = True
    def __init__(self, name, arg_names, code, env = None):
        self._w_code = code
        self._arg_names = arg_names
        self._env = env
        self._name = name

    def with_env(self, env):
        return PixieFunction(self._name, self._arg_names, self._w_code, env)


    def invoke_(self, args):
        new_env = self._env.with_locals(self._arg_names, args)
        new_env = new_env.with_locals([self._name], [self])
        return self._w_code.interpret_(new_env)


class Bind(Syntax):
    def __init__(self, nm, ast, body):
        self._nm = nm
        self._w_ast = ast
        self._w_body = body

    @cps
    def interpret_(self, env):
        result = self._w_ast.interpret_(env)
        new_env = env.with_locals([self._nm], [result])
        result = self._w_body.interpret_(new_env)
        return result

## End If Syntax

eq = EQ()
add = Add()

literal = PixieFunction("countup", ["x"],
                        If(Call(Constant(eq), [Lookup("x"), Constant(Integer(10))]),
                           Lookup("x"),
                           Call(Lookup("countup"),
                                [Call(Constant(add), [Lookup("x"), Constant(Integer(1))])])))

env = Env({}, None)

ast1 = Call(Constant(add), [If(Lookup("x"),
             Do([Constant(Integer(42)),
                Constant(Integer(1))]),
             Do([Constant(nil),
                 Constant(nil)])),
                    Constant(Integer(1))])

ast2 = Bind("countup", FnLiteral(literal),
            Call(Lookup("countup"), [Constant(Integer(0))]))

ast1 = If(Lookup("x"),
             Do([Constant(Integer(42)),
                 Constant(Integer(1))]),
             Do([Constant(nil),
                 Constant(nil)]))

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
    for x in range(1):
        result = interpret_effect(ast, env)
    print result.val().int_val()

def entry_point(argv):
    run(argv)
    return 0

def target(*args):
    return entry_point, None

if __name__ == "__main__":
    import sys
    run([1])
