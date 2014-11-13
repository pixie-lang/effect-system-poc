## Effects System for Pixie Prototype

### Motivation

While the current Pixie interpreter works well it's pretty much just like any other mutable interpreter. But on the other
hand we have the PyPy JIT generator that allows us to create interpreters modeled almost any way we want. What would a
interpreter look like in a "perfect world"?

For answers to such questions I suggest reading up on the language Eff (http://arxiv.org/pdf/1203.1539v1.pdf). This language
specifies an interesting language design, one that makes a distinction between side-effect-free computations, and effects that
modify the environment or the system. Having an interpreter that makes this distinction has several benefits:

1) Any computation in the system could be hinted to the JIT as being pure, thus removable if the arguments to the computation
are constants.

.....




### CPS Transform

This project contains a very 'touchy' code transformer, known as `@cps`. This will take an RPython function or method and
transform it into an immutable state-machine via CPS transformation. As is expected with this sort of code mangling there
are many caveats to using this transformer, but they are mostly simple to remember:

* Calls to functions or methods that end with a single `_` are considered to be effect functions (functions that will either
 return Answer or an Effect). Thus at every call to such a function the transformer will create a continuation.
* Generators/Iterators should be avoided. A single step of the function may be run many times, thus it is important to clone
  any mutable state.
* The call stack is not persisted across continuations, so be sure that the stack position is 0 at every effect function call.
For example:


    @cps
    def foo(x):
      r = invoke_(x)
      z = invoke_(r)
      return z


Is fine, while the following is not:


    @cps
    def foo(x):
      return invoke_(invoke_(x))


Since the outer `invoke_` will be loaded before the `inner_`.

* Calls to effect functions that immediately return will be turned into tail calls, so prefer this style when possible:


    @cps
    def foo(x):
      return invoke_(x)

* Currently (until this restriction is removed) effect calls that take anything but locals as arguments are not supported.


    @cps
    def foo(x):
      # works
      x = invoke_(something)
      # doesn't work
      x = invoke_(something._zing)

* `break` and `continue` require the stack to operate, and as such are not supported
* Since functions are RPython and internally function locals are converted class fields, locals can only have one type. Unlike
RPython that supports locals with conflicting types as long as they are redefined between usages.