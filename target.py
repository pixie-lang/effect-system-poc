
from rpython.rlib.jit import JitDriver
import rpython.rlib.jit as jit
from effect_transform import cps
from effects import *
from rpython.rlib.debug import debug_flush

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

@jit.unroll_safe
def clone_append(arr, itm):
    new_array = [None] * (len(arr) + 1)
    x = 0
    while x < len(arr):
        new_array[x] = arr[x]
        x += 1
    new_array[x] = itm
    return new_array

class ItemsArray(Object):
    def __init__(self, items_w):
        self._items_w = items_w

    def items(self):
        return self._items_w

@cps
def interpret_items_(args_w, env):
    new_args = []
    idx = 0

    while idx < len(args_w):
        expr = args_w[idx]
        result = thunk_(expr, env)
        new_args = clone_append(new_args, result)
        idx += 1

    wrapped = ItemsArray(new_args)
    return wrapped


def interpret(x, env):
    assert isinstance(x, Syntax)
    return x.interpret_(env)


def thunk_(expr, env):
    return ThunkFn(expr, env)

class ThunkFn(Thunk):
    _immutable_ = True
    def __init__(self, expr, env):
        self._expr = expr
        self._env = env

    def execute_thunk(self):
        return interpret(self._expr, self._env)

    def get_loc(self):
        return (self._expr, self._env)

def thunk_tailcall_(expr, env):
    return TailCallThunkFn(expr, env)

class TailCallThunkFn(Thunk):
    _immutable_ = True
    def __init__(self, expr, env):
        self._expr = expr
        self._env = env

    def execute_thunk(self):
        return interpret(self._expr, self._env)

def interpret_effect(ast, env):
    f = thunk_(ast, env)


    while True:
        (ast, env) = f.get_loc()
        if ast:
            jitdriver.jit_merge_point(ast=ast, thunk=f, env=env)
        result = f.execute_thunk()
        if isinstance(result, Thunk):
            f = result
            continue
        if isinstance(result, Answer):
            return result
        assert False




## End Interpret and Thunks

class Name(Object):
    def __init__(self, name):
        self._name = name

interned_names = {}

def intern(nm):
    val = interned_names.get(nm, None)
    if val is None:
        val = Name(nm)
        interned_names[nm] = val

    return val


class Locals(Object):
    _immutable_ = True
   # _virtualizable_ = ["_names[*]", "_vals[*]"]

    def __init__(self, names=[], vals=[]):
        self = jit.hint(self, access_directly=True, fresh_virtualizable=True)
        self._names = names
        self._vals = vals

    @jit.unroll_safe
    def name_idx(self, nm):
        x = 0
        while x < len(self._names):
            val = self._names[x]
            if nm is val:
                return x
            x += 1
        raise NotImplementedError()

    def lookup_local(self, nm):
        idx = self.name_idx(nm)
        if idx == -1:
            return None
        return self._vals[idx]

    def lookup_(self, nm):
        return Answer(self.lookup_local(nm))

    @jit.unroll_safe
    def with_locals(self, name, val):
        idx = 0
        while idx < len(self._names):
            if self._names[idx] is name:
                break
            idx += 1

        if idx == len(self._names):
            new_size = idx + 1
        else:
            new_size = len(self._names)

        new_names = [None] * new_size
        new_vals = [None] * new_size

        x = 0
        while x < len(self._names):
            new_names[x] = self._names[x]
            new_vals[x] = self._vals[x]
            x += 1

        new_names[idx] = name
        new_vals[idx] = val

        return Locals(new_names, new_vals)

def lookup_(env, sym):
    val = env.lookup_local(sym)
    if val is not None:
        return Answer(val)
    raise NotImplementedError()


class Syntax(Object):
    _immutable_ = True
    def interpret_(self, env):

        return self.interpret_inner_(env)

    def interpret_inner_(self, env):
        raise NotImplementedError()

class Constant(Syntax):
    _immutable_ = True
    def __init__(self, value):
        self._val = value

    def interpret_inner_(self, env):
        return Answer(self._val)

class Lookup(Syntax):
    _immutable_ = True
    def __init__(self, name):
        self._name = name

    @cps
    def interpret_inner_(self, env):
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
    def interpret_inner_(self, env):
        tst = self._w_test.interpret_(env)
        ret = None
        if not (tst is nil or tst is false):
            expr = self._w_then
        else:
            expr = self._w_else
        return thunk_(expr, env)

class Do(Syntax):
    _immutable_ = True
    def __init__(self, exprs):
        self._exprs_w = exprs

    @cps
    def interpret_inner_(self, env):
        x = 0
        result = nil
        while x < len(self._exprs_w):
            expr = self._exprs_w[x]
            result = thunk_(expr, env)
            x += 1

        return result

class Call(Syntax):
    _immutable_ = True
    def __init__(self, fn, args):
        self._w_fn = fn
        self._args_w = args

    @cps
    def interpret_inner_(self, env):
        expr = self._w_fn
        fn = thunk_(expr, env)
        args_w = self._args_w
        itms = interpret_items_(args_w, env)
        unwrapped = itms.items()
        return fn.invoke_(unwrapped)

class Add(Fn):
    _immutable_ = True
    def __index__(self):
        pass

    def invoke_(self, args):
        return Answer(Integer(args[0].int_val() + args[1].int_val()))


class EQ(Fn):
    _immutable_ = True
    def __index__(self):
        pass

    def invoke_(self, args):
        result = args[0].int_val() == args[1].int_val()
        return Answer(true if result else false)

class FnLiteral(Syntax):
    _immutable_ = True
    def __init__(self, fn):
        self._w_fn = fn

    def interpret_inner_(self, env):
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

    @jit.unroll_safe
    def invoke_(self, args):
        new_env = self._env
        x = 0
        while x < len(args):
            new_env = new_env.with_locals(self._arg_names[x], args[x])
            x += 1
        new_env = new_env.with_locals(self._name, self)
        ast = self._w_code
        return thunk_tailcall_(ast, new_env)


class Bind(Syntax):
    _immutable_ = True
    def __init__(self, nm, ast, body):
        self._nm = nm
        self._w_ast = ast
        self._w_body = body

    @cps
    def interpret_inner_(self, env):
        expr = self._w_ast
        result = thunk_(expr, env)
        new_env = env.with_locals(self._nm, result)
        expr = self._w_body
        result = thunk_(expr, new_env)
        return result

## End If Syntax

eq = EQ()
add = Add()
x = intern("x")
countup = intern("countup")
inc = intern("inc")
inc_fn = PixieFunction(inc)

literal = PixieFunction(countup, [x],
                        If(Call(Constant(eq), [Lookup(x), Constant(Integer(10000))]),
                           Lookup(x),
                           Call(Lookup(countup),
                                [Call(Constant(add), [Lookup(x), Constant(Integer(1))])])))

ast1 = Call(Constant(add), [If(Lookup(x),
             Do([Constant(Integer(42)),
                Constant(Integer(1))]),
             Do([Constant(nil),
                 Constant(nil)])),
                    Constant(Integer(1))])

ast2 = Bind(countup, FnLiteral(literal),
            Call(Lookup(countup), [Constant(Integer(0))]))

## JIT stuff

def get_printable_location(ast):
    return str(ast)

jitdriver = JitDriver(greens=['ast'],
        reds=['env', 'thunk'],
       # virtualizables=['env'],
        get_printable_location=get_printable_location
)

from rpython.jit.codewriter.policy import JitPolicy
from rpython.rlib.jit import JitHookInterface, Counters
from rpython.annotator.policy import AnnotatorPolicy

class DebugIFace(JitHookInterface):
    def on_abort(self, reason, jitdriver, greenkey, greenkey_repr, logops, operations):
        print "Aborted Trace, reason: ", Counters.counter_names[reason], logops, greenkey_repr

import sys, pdb

class Policy(JitPolicy, AnnotatorPolicy):
    def __init__(self):
        JitPolicy.__init__(self, DebugIFace())

def jitpolicy(driver):
    return JitPolicy(jithookiface=DebugIFace())


from rpython.rtyper.lltypesystem import lltype
from rpython.jit.metainterp import warmspot

def run_child(glob, loc):
    interp = loc['interp']
    graph = loc['graph']
    interp.malloc_check = False

    def returns_null(T, *args, **kwds):
        return lltype.nullptr(T)
    interp.heap.malloc_nonmovable = returns_null     # XXX

    from rpython.jit.backend.llgraph.runner import LLGraphCPU
    #LLtypeCPU.supports_floats = False     # for now
    apply_jit(interp, graph, LLGraphCPU)


def apply_jit(interp, graph, CPUClass):
    print 'warmspot.jittify_and_run() started...'
    policy = Policy()
    warmspot.jittify_and_run(interp, graph, [], policy=policy,
                             listops=True, CPUClass=CPUClass,
                             backendopt=True, inline=True)

def run_debug(argv):
    from rpython.rtyper.test.test_llinterp import get_interpreter

    # first annotate and rtype
    try:
        interp, graph = get_interpreter(entry_point, [], backendopt=False,
                                        #config=config,
                                        #type_system=config.translation.type_system,
                                        policy=Policy())
    except Exception, e:
        print '%s: %s' % (e.__class__, e)
        pdb.post_mortem(sys.exc_info()[2])
        raise

    # parent process loop: spawn a child, wait for the child to finish,
    # print a message, and restart
    #unixcheckpoint.restartable_point(auto='run')

    from rpython.jit.codewriter.codewriter import CodeWriter
    CodeWriter.debug = True
    run_child(globals(), locals())

def run(argv):
    ast = [ast1, ast2][len(argv)]

    result = None
    result = interpret_effect(ast, Locals())
    print result

def entry_point(argv):
    run(argv)
    return 0

def target(*args):
    return entry_point, None

if __name__ == "__main__":
    import sys
    run_debug(["f"])
