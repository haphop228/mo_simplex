"""Тесты двухфазного модифицированного симплекс-метода.
"""

from fractions import Fraction
from typing import List, Tuple
import pytest

from core.models import LinearProblem
from core.solver import SimplexSolver


# ---------------------------------------------------------------------------- helpers
def _solve(c, A, b, signs, is_max):
    """Запускает солвер и возвращает (последний_шаг, объект-solver, все_шаги)."""
    p = LinearProblem(
        c=[Fraction(x) for x in c],
        A=[[Fraction(x) for x in r] for r in A],
        b=[Fraction(x) for x in b],
        signs=signs,
        is_max=is_max,
    )
    s = SimplexSolver(p)
    steps = list(s.solve())
    return steps[-1], s, steps


def _objective(last, solver, is_max):
    """Восстанавливает значение исходной целевой функции (z* / f*)."""
    val = sum(solver.c[idx] * last.x_B[i] for i, idx in enumerate(last.N))
    return val if is_max else -val


# ---------------------------------------------------------------------------- baseline (фаза I пропускается)
def test_classic_lp_no_phase1():
    """Классический пример из методички: max 12x1+3x2, 3 ограничения <=."""
    last, solver, steps = _solve(
        c=[12, 3],
        A=[[4, 1], [2, 2], [6, 3]],
        b=[16, 22, 36],
        signs=['<=', '<=', '<='],
        is_max=True,
    )

    assert last.is_optimal
    assert not last.is_infeasible
    assert _objective(last, solver, is_max=True) == Fraction(48)
    # Все шаги должны быть в фазе II (искусственные не нужны).
    assert all(st.phase == 2 for st in steps)

    x = last.x_full
    assert x[0] == Fraction(4)
    assert x[1] == Fraction(0)
    assert last.u_0 == [Fraction(3), Fraction(0), Fraction(0)]


# ---------------------------------------------------------------------------- задача 1
def test_problem1_min_with_geq_constraints():
    """min 2x1 + 3x2, x1+x2 >= 3, 2x1+x2 >= 4 → x* = (3, 0), z* = 6."""
    last, solver, steps = _solve(
        c=[2, 3],
        A=[[1, 1], [2, 1]],
        b=[3, 4],
        signs=['>=', '>='],
        is_max=False,
    )

    assert last.is_optimal
    assert not last.is_infeasible
    assert last.phase == 2

    # Оптимальный план
    assert last.x_full[0] == Fraction(3)
    assert last.x_full[1] == Fraction(0)
    # z* = 6 (минимум)
    assert _objective(last, solver, is_max=False) == Fraction(6)

    # Должна была быть фаза I (есть >= ограничения).
    assert any(st.phase == 1 for st in steps)
    assert any(st.phase == 2 for st in steps)


# ---------------------------------------------------------------------------- задача 2
def test_problem2_max_with_equality():
    """max 4x1 + x2, x1+2x2 <= 6, x1+x2 = 3 → x* = (3, 0), z* = 12, u* = (0, 4)."""
    last, solver, steps = _solve(
        c=[4, 1],
        A=[[1, 2], [1, 1]],
        b=[6, 3],
        signs=['<=', '='],
        is_max=True,
    )

    assert last.is_optimal
    assert last.phase == 2
    assert last.x_full[0] == Fraction(3)
    assert last.x_full[1] == Fraction(0)
    assert _objective(last, solver, is_max=True) == Fraction(12)

    # u* = (0, 4) — двойственная пара совпадает с эталоном (равенство => u2 свободная,
    # знак не инвертируется, т.к. b_i >= 0 и signs[i] == '=' остаётся '=').
    assert last.u_0 == [Fraction(0), Fraction(4)]


# ---------------------------------------------------------------------------- задача 3
def test_problem3_mixed_constraints():
    """max 6x1 + 8x2, 2x1+x2 <= 10, x1+2x2 >= 6 → x* = (0, 10), z* = 80, u* = (8, 0)."""
    last, solver, steps = _solve(
        c=[6, 8],
        A=[[2, 1], [1, 2]],
        b=[10, 6],
        signs=['<=', '>='],
        is_max=True,
    )

    assert last.is_optimal
    assert last.phase == 2
    assert last.x_full[0] == Fraction(0)
    assert last.x_full[1] == Fraction(10)
    assert _objective(last, solver, is_max=True) == Fraction(80)
    assert last.u_0 == [Fraction(8), Fraction(0)]


# ---------------------------------------------------------------------------- инфизибельность / неограниченность
def test_infeasible_problem():
    """x1+x2 <= 5 и x1+x2 >= 10 — несовместная система."""
    last, _, steps = _solve(
        c=[1, 1],
        A=[[1, 1], [1, 1]],
        b=[5, 10],
        signs=['<=', '>='],
        is_max=True,
    )

    assert last.is_infeasible
    assert not last.is_optimal
    # Завершилось на фазе I.
    assert last.phase == 1


def test_unbounded_problem():
    """max x1, x1 - x2 <= 10 — функция не ограничена сверху по x1."""
    last, _, _ = _solve(
        c=[1, 0],
        A=[[1, -1]],
        b=[10],
        signs=['<='],
        is_max=True,
    )

    assert last.is_unbounded
    assert not last.is_optimal


# ---------------------------------------------------------------------------- профессорский кейс с фото
def test_professor_example_phase1_then_phase2():
    """x1+x2<=10, x1+x2>=10, max x1+x2 — двухфазный, ответ z=10."""
    last, solver, steps = _solve(
        c=[1, 1],
        A=[[1, 1], [1, 1]],
        b=[10, 10],
        signs=['<=', '>='],
        is_max=True,
    )

    assert last.is_optimal
    assert _objective(last, solver, is_max=True) == Fraction(10)
    # Должен присутствовать переход из фазы I в фазу II.
    phases_in_order = [st.phase for st in steps]
    assert phases_in_order[0] == 1
    assert phases_in_order[-1] == 2


# ---------------------------------------------------------------------------- свойства алгоритма
def test_bland_first_index_rule():
    """Δ_j считается до первого отрицательного включительно (правило первого индекса)."""
    last_step_first, _, steps = _solve(
        c=[12, 3],
        A=[[4, 1], [2, 2], [6, 3]],
        b=[16, 22, 36],
        signs=['<=', '<=', '<='],
        is_max=True,
    )
    # На первой итерации (j_0 = 0 → x1) Δ_1 = -12 < 0, и перебор прерывается.
    iter1 = steps[0]
    assert iter1.diffs is not None
    # diffs — список (j, Δ_j); должен содержать ровно один элемент с Δ < 0.
    assert iter1.diffs[-1][1] < 0
    # Последний элемент именно тот, на котором сработал break.
    assert all(d >= 0 for _, d in iter1.diffs[:-1])


def test_full_x_vector_length():
    """x_full имеет длину расширенной канонической задачи (включая балансовые/искусств.)."""
    last, solver, steps = _solve(
        c=[1, 1],
        A=[[1, 1], [1, 1]],
        b=[10, 10],
        signs=['<=', '>='],
        is_max=True,
    )
    # 2 исходных + s1 (для <=) + s2 (избыточная для >=) + a1 (искусственная) = 5
    assert len(last.x_full) == 5
    # Сумма базисных значений = сумма соответствующих позиций в x_full.
    for i, idx in enumerate(last.N):
        assert last.x_full[idx] == last.x_B[i]


def test_strong_duality():
    """Сильная двойственность: f* = b^T u* (с учётом инверсии знаков ≥-строк)."""
    # Задача 2 (с равенством, без инверсий) — двойственность должна выполниться буквально.
    last, solver, _ = _solve(
        c=[4, 1],
        A=[[1, 2], [1, 1]],
        b=[6, 3],
        signs=['<=', '='],
        is_max=True,
    )
    z_star = _objective(last, solver, is_max=True)
    # b в солвере уже приведён к ≥0, но для signs=['<=','='] инверсии не было.
    g_star = sum(solver.b[i] * last.u_0[i] for i in range(len(solver.b)))
    assert z_star == g_star
