# 需求分析

在进行需求分析之前，首先需要介绍关系式编程的一些背景知识与历史。

参考资料包括：

Logic Programming - Robert Kowalski

MuKanren: A Minimal Functional Core for Relational Programming - Jason Hemann, Daniel Friedman

Relational Programming in MiniKanren - William E. Byrd

The Implementation of Prolog - Boizumault Patrice 等

1965年，John Alan Robinson 提出了名为**The Resolution Princple**的自动定理证明方法，此方法的核心步骤名为**合一(Unification)**, 7年后，Robert Kowalski及其协作者Alain Colmerauer在将Robinson的方法应用于人工智能研究时，意外地发现了一种可用于执行逻辑程序的自顶向下方法。这一发现催生了后世以Prolog为代表的逻辑式程序设计语言，实际上，就在当年夏末，Colmerauer便完成了Prolog的第一个版本，并用其编写了一个自然语言问答系统。

而关系式编程则是逻辑式的一个变体，其中每个目标(Goal)都由纯的关系写成。每个关系都可给出有意义的回答，即使所有参数都是未绑定的逻辑变量(unbound logic variable)。逻辑式编程中的一些非纯语言构造(如Prolog的cut)不被关系式编程支持。

关系是对传统函数概念的泛化，它不严格区分输入与输出，从而获得极高的灵活度。例如，一个关系式的类型推导器同样可以执行类型检查，而一个关系式的定理证明器也可用于定理生成与证明检查。一个最有趣的例子之一是，通过限定一个关系式解释器的输入输出为同一逻辑变量，令其枚举求值结果与自身形式一致的程序，这种程序传统上被称为quine。

现今扛起关系式大旗的语言是miniKanren，由Dan Friedman设计，因其易于实现而常见于教学。其变种相当多，此报告中选择的MuKanren是minikanren语言家族中偏简单而实现设计思想独到的一种。


# 总体设计

miniKanren语族的特点是几乎都以EDSL(内嵌式领域特定语言)方式实现，通过宿主语言的解释器/编译器绕过解析解释等大多数实现工作，在此处选择的宿主语言按课程要求则为Python。我们选择Python中的一些数据类型(如int, str, List)作为MuKanren的常规项(term)，并定义一个特殊的类充当MuKanren的逻辑变量。

其核心数据结构是一个叫做Substitution的键值对序列，或者说是从逻辑变量到MuKanren项的映射，实现方式原则上可自由选择，但因为MuKanren对扩展(即添加键值对)的需求较多，最好用链表/Trie等可快速插入的数据结构实现。本报告中使用类与空元组模拟朴素的关联链表。

Substitution中的键类型必须为逻辑变量，而值可以是MuKanren中的常规项，亦可是逻辑变量，当某个键值对的右侧(right hand side, rhs)为逻辑变量时，就需要递归地在同一Substitution中以此逻辑变量为键进行链式的查询，这种实现被称为**triangular substitution**, 与其相对的**idempotent substitution**不允许键值对右侧出现逻辑变量。

在链表实现下，triangular substitution的优点非常明显：扩展快，时间复杂度为常数。同时基于数据共享的扩展使得回溯搜索的实现非常简单，因此这一实现方式在以函数式语言为载体的MuKanren实现中非常流行。而idempotent substitution因为无需递归查询速度较快，[Kleene 1952]证明了triangular substitution的查询函数是非原始递归的。

注: 有一位熟悉python的类型论学人向我们建议用with语句做idempotent substitution的回溯，并称对可变数据结构的回溯写起来更有艺术感，这一建议非常高明，但是想正确实现比较困难。

triangular substitution的另一危险是容易引入环 -- 而每次扩展都要检查是否产生环路又成本高昂，所以本报告中的MuKanren实现并未进行环路检查。

unify函数在某个特定的Substitution下对俩个MuKanren项进行合一 - 这一神秘的概念将在后文进行详细的解释，合一成功将返回新的substitution，失败则返回#f。

MuKanren中的目标几乎都要基于unify实现，一个目标是类型为`Substitution -> Stream[Subsititution]`的函数. 而基本的控制结构conj(代表合取)与disj(代表析取)类型都是`Goal -> Goal -> Goal`, 它们对输入目标的处理不尽相同，但都将空Stream看做失败。

disj在目标1失败后将目标2的返回值作为整体的结果，而俩个目标都成功时将它们的返回值进行拼接(保留尽可能多的结果)这可以看作一种聪明的深度优先搜索，每个成功的目标返回一到多个无冲突的Substitution，如果当前目标失败，就放弃掉这条搜索路线，回退到其他的选择再试试。这也是为什么目标的返回值是一个Stream，因为在现在的已知信息下，合理的组合可能有很多(包括无穷)，也可能一个都没有。而conj在目标一失败后即返回空stream。

合取与析取通过bind与mplus函数实现，它们的命名来源于元数学分支范畴论中的概念"Monad"(常常被戏谑地称为"自函子范畴上的幺半群"), 此处不做赘述, 详细的介绍可见"Notions of computation and monads"。

# 详细设计

虽然python是一种典型的动态类型语言，但是我们选择使用Python 3.7后引入的类型标注，在此报告的情景中这有助于提升代码的可读性。

```python
from typing import Any, Callable, List, Tuple

Unit = Tuple[()]
Empty   = Unit
Mature = Tuple[Subst, Any] 
Immature   = Callable[[], Any] # Any <=> Stream
Stream = Empty | Mature | Immature
Goal = Callable[[Subst], Stream]
```

Stream类型有三种值：空流(Empty)，饱和流(Mature),不饱和流(Immature), 不饱和流的引入目的是应对可能的无穷个解答，它被实现为基于闭包的延时求值。

为了保证每个逻辑变量在比较时都有所不同，以及在视觉上有较高区分度，为每个逻辑变量分配一个整数id并在比较时使用is。

```python
class Var:
    _count: int = 0
    def __init__(self):
        Var._count = Var._count + 1
        self.count = Var._count
    def __repr__(self) -> str:
        return "{*" + self.count.__repr__() + "*}"
```

Substitution使用dataclass

```python
@dataclass
class Subst:
    _hd_: Tuple[Var, Any]
    _tl_: Any
    def __repr__(self):
        if self._tl_ == ():
            return self._hd_.__repr__() + ')'
        else:
            return self._hd_.__repr__() + ' ' + self._tl_.__repr__()
```

我们首先编写在Substitution中根据输入谓词查找键值对的函数

```python
def assq(f: Callable[[Var], bool], s: Subst | Unit) -> Tuple[Var, Any] | Unit:
    while s != ():
        v, n = s._hd_
        if f(v):
            return s._hd_
        else:
            s = s._tl_
    # 查询失败返回()
    return ()
```

然后编写根据逻辑变量查找对应term的walk函数

```python
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
```

在参数u为常规项时会直接返回，查询失败则会返回变量本身。

unify的实现并不复杂，其接受一对MuKanren项u, v与一个Substitution s，首先在s中进行查询，然后判断这一对项

+ 它们能构成键值对吗？

+ 它们所构成的键值对与原本的Substitution是否有冲突？

若u，v在walk后都为常规项，则判断其是否相等

+ 若相等，则它们至少无冲突，本次合一成功，但是s无改动

+ 不等，则合一彻底失败。

若u，v在walk后都为逻辑变量，当其为同一逻辑变量时，合一成功s无改动，为不同逻辑变量则合一失败。

u, v中仅有一个为逻辑变量的情景简单扩展s即可。

对于List，我们把它当作一种递归数据结构分而治之。

# 代码

```python
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
```



