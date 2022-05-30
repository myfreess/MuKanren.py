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

triangular substitution的另一危险是容易引入环 -- 而每次扩展都要检查是否产生环路又成本高昂，所以本报告中的MuKanren实现并未进行环路检查。

unify函数在某个特定的Substitution下对俩个MuKanren项进行合一 - 这一神秘的概念将在后文进行详细的解释，合一成功将返回新的substitution，失败则返回#f。

MuKanren中的目标几乎都要基于unify实现，一个目标是类型为Substitution -> Stream[Subsititution]的函数，以比较庸俗的解释，当我们想解一个很小的问题A时，我们其实是在寻求对A的一个赋值x，它与我们在先前所记录的事实无冲突。放到具体的编程中，也就是当前目标对A 和 x在substitution s下的合一能成功。

这可以看作一种聪明的深度优先搜索，每个成功的目标都为当前的Substitution贡献0 ~ n个事实(实际上可以有无穷个，但是最终给出回答时只能有有限个组合)，如果当前目标失败，就放弃掉这条搜索路线，回退到其他的组合再试试。这也是为什么目标的返回值是一个Stream，因为在现在的已知信息下，合理的组合可能有很多(包括无穷)，也可能一个都没有。

合取与析取通过bind与mplus函数实现，它们的命名来源于元数学分支范畴论中的概念"Monad"(常常被戏谑地称为"自函子范畴上的幺半群"), 此处不做赘述, 详细的介绍可见"Notions of computation and monads"。

# 说明代码

