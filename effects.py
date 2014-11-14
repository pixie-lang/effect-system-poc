
class Object(object):
    pass

class EffectObject(object):
    _immutable_=True

class Effect(EffectObject):
    _immutable_ = True
    pass

class Answer(EffectObject):
    _immutable_=True
    def __init__(self, w_val):
        self._w_val = w_val

    def val(self):
        return self._w_val

class Handler(EffectObject):
    _immutable_=True
    def handle(self, effect, k):
        raise NotImplementedError()

class Thunk(EffectObject):
    _immutable_=True
    def execute_thunk(self):
        raise NotImplementedError()

    def get_loc(self):
        return (None, None)

class Continuation(object):
    _immutable_= True
    def step(self, x):
        raise NotImplementedError()

class Fn(Object):
    _immutable_ = True
    def invoke_(self, args):
        raise NotImplementedError()

def answer(x):
    return Answer(x)

def raise_(x, k):
    x._k = k
    return x

def handle_with(handler, effect, k):
    assert isinstance(effect, EffectObject)
    if isinstance(effect, Thunk):
        return CallEffectFn(handler, effect, k)
    else:
        ret = handler.handle(effect, k)
        if ret is None:
            without = effect.without_k()
            without._k = EffectStepThunk(handler, effect, k)

            return without
        else:
            return ret

class EffectThunk(Thunk):
    _immutable_ = True
    def __init__(self, k, val):
        self._k = k
        self._val = val

    def execute_thunk(self):
        return self._k.step(self._val)

class EffectStepThunk(Continuation):
    _immutable_ = True
    def __init__(self, handler, effect, k):
        self._k = k
        self._effect_k = effect._k
        self._handler = handler

    def step(self, val):
        return handle_with(self._handler, EffectThunk(self._effect_k, val), self._k)


def handle(effect, k):
    return handle_with(default_handler, effect, k)

class CallEffectFn(Thunk):
    _immutable_ = True
    def __init__(self, handler, effect, k):
        self._handler = handler
        self._k = k
        self._effect = effect

    def execute_thunk(self):
        return handle_with(self._handler, self._effect.execute_thunk(), self._k)

    def get_loc(self):
        return self._effect.get_loc()


class HandleRecFn(Handler):
    _immutable_ = True
    def __init__(self, handler, k):
        self._handler = handler
        self._k = k

    def handle_rec(self, arg):
        return handle_with(self._handler, arg, self._k)

## End Handle With

## Default Handler

class DefaultHandler(EffectObject):
    _immutable_ = True
    def handle(self, effect, k):
        if isinstance(effect, Answer):
            return DefaultHandlerFn(k, effect.val())

default_handler = DefaultHandler()

class DefaultHandlerFn(Thunk):
    _immutable_ = True
    def __init__(self, k, val):
        assert isinstance(k, Continuation)
        self._val = val
        self._k = k

    def execute_thunk(self):
        return self._k.step(self._val)

    def get_loc(self):
        return (None, None)

## End Default Handler
