
class Object(object):
    pass

class EffectObject(object):
    _immutable_=True

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



def handle_with(handler, effect, k):
    assert isinstance(effect, EffectObject)
    if isinstance(effect, Thunk):
        return CallEffectFn(handler, effect, k)
    else:
        ret = handler.handle(effect, k)
        if ret is None:
            effect.__stuff = (k)
            return effect
        else:
            return ret


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

## End Default Handler
