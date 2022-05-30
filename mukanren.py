from dataclasses import dataclass
from inspect import isfunction
from typing import Any, Callable, List, Tuple

Unit = Tuple[()]

mzero: Unit = ()


class Var:
    _count: int = 0
    def __init__(self):
        Var._count = Var._count + 1
        self.count = Var._count
    def __repr__(self) -> str:
        return "{*" + self.count.__repr__() + "*}"


def isVar(x) -> bool:
    return isinstance(x, Var)

@dataclass
class Subst:
    _hd_: Tuple[Var, Any]
    _tl_: Any
    def __repr__(self):
        if self._tl_ == ():
            return self._hd_.__repr__() + ')'
        else:
            return self._hd_.__repr__() + ' ' + self._tl_.__repr__()


def cons(x: Tuple[Var, Any], xs: Any) -> Subst:
    return Subst(x, xs)

def isSubst(s: Any) -> bool:
    return isinstance(s, Subst)


def assq(f: Callable[[Var], bool], s: Subst | Unit) -> Tuple[Var, Any] | Unit:
    while s != ():
        v, n = s._hd_
        if f(v):
            return s._hd_
        else:
            s = s._tl_
    # 查询失败返回()
    return ()

def isPair(x: Any) -> bool:
    return isinstance(x,List) and x.__len__() > 0

    

Empty   = Unit
Mature = Tuple[Subst, Any] 
Immature   = Callable[[], Any] # Any <=> Stream
Stream = Empty | Mature | Immature
Goal = Callable[[Subst], Stream]


def walk(u, s):
    # u为term或var
    if not isVar(u):
        return u
    # 非变量term直接返回
    pr = assq(lambda x: x is u, s)
    if pr == ():
        return u # 表中无对应值，返回u
    else:
        _, n = pr
        return walk(n, s)

def ext_s(x: Var, v: Any, s: Subst) -> Subst:
    return Subst((x,v), s)

def unify(u, v, s: Subst | Unit) -> Subst | Unit | bool:
    u = walk(u, s)
    v = walk(v, s)
    # print(f"u = {u}, v = {v}")
    if isVar(u) and isVar(v) and u is v:
        return s
    # 搜索结果为同一变量
    # 不扩展s
    elif isVar(u):
        return ext_s(u, v, s)
    elif isVar(v):
        return ext_s(v, u, s)
    elif isPair(u) and isPair(v):
        s = unify(u[0], v[0], s)
        if s != False:
            return unify(u[1:], v[1:], s)
        else:
            return False
    elif u == v:
        return s
    else:
        return False

def uf(u, v) -> Goal:
    def receiver(s: Subst) -> Stream:
        s = unify(u, v, s)
        if s == False:
            return mzero
        else:
            return (s, mzero)
    return receiver



def mplus(m1: Stream, m2: Stream) -> Stream:
    if m1 == ():
        return m2
    elif isfunction(m1): #这个判断对built-in函数无效
        return lambda: mplus(m2, m1())
    else:
        hd, tl = m1
        return (hd, mplus(m2, tl))

def bind(m: Stream, g: Callable[[Tuple[Subst, Any]], Stream]) -> Stream:
    if m == ():
        return mzero
    elif isfunction(m):
        return lambda: bind(m(), g)
    else:
        hd, tl = m
        return mplus(g(hd), bind(tl, g))


def disj(g1: Goal, g2: Goal) -> Goal:
    def receiver(s: Subst) -> Stream:
        return mplus(g1(s), g2(s))
    return receiver

def conj(g1: Goal, g2: Goal) -> Goal:
    def receiver(s: Subst) -> Stream:
        return bind(g1(s), g2)
    return receiver


# a_and_b = mu.conj(mu.uf(a, 7), mu.disj(mu.uf(b, 5), mu.uf(b, 6)))

def pull(m: Stream) -> Stream:
    while isfunction(m):
        m = m()
    return m

def take(n: int, m: Stream) -> List:
    l = []
    while n > 0:
        m = pull(m)
        if m == ():
            return l
        else:
            hd, tl = m
            l.append(hd)
            m = tl
            n = n - 1
    return l

