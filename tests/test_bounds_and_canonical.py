"""Тесты для новых возможностей:
- Границы переменных (lower_bounds / upper_bounds)
- Свободные и отрицательные переменные
- Канонический режим (авто-детектор ортов)
- Восстановление исходных переменных (recover_original_x)
- Двойственное решение с учётом инверсий строк (u_0_original)
"""

from fractions import Fraction
import pytest
from core.models import LinearProblem
from core.solver import SimplexSolver


def _solve(c, A, b, signs, is_max=True, lower_bounds=None, upper_bounds=None, canonical_mode=False):
    """Вспомогательная функция: запускает солвер и возвращает (last_step, solver, steps)."""
    p = LinearProblem(
        c=[Fraction(x) for x in c],
        A=[[Fraction(x) for x in r] for r in A],
        b=[Fraction(x) for x in b],
        signs=signs,
        is_max=is_max,
        lower_bounds=[Fraction(v) if v is not None else None for v in lower_bounds] if lower_bounds else None,
        upper_bounds=[Fraction(v) if v is not None else None for v in upper_bounds] if upper_bounds else None,
    )
    s = SimplexSolver(p, canonical_mode=canonical_mode)
    steps = list(s.solve())
    return steps[-1], s, steps


def _obj(last, solver, is_max):
    val = sum(solver.c[idx] * last.x_B[i] for i, idx in enumerate(last.N))
    return val if is_max else -val


# ============================================================ upper_bounds
class TestUpperBounds:
    def test_upper_bound_restricts_solution(self):
        """max x1 + x2, x1 + x2 <= 10, x1 <= 3 (через upper_bounds).
        Без ограничения x1 <= 3 оптимум был бы x1=10, x2=0.
        С ограничением: x1=3, x2=7, f*=10."""
        last, solver, steps = _solve(
            c=[1, 1],
            A=[[1, 1]],
            b=[10],
            signs=['<='],
            is_max=True,
            upper_bounds=[3, None],
        )
        assert last.is_optimal
        x = solver.recover_original_x(last.x_full)
        assert x[0] == Fraction(3)
        assert x[1] == Fraction(7)
        assert _obj(last, solver, is_max=True) == Fraction(10)

    def test_upper_bound_equal_to_lower(self):
        """Фиксированная переменная x1 = 2 (lb=ub=2).
        max x1 + x2, x2 <= 5 → x1=2, x2=5, f*=7."""
        last, solver, steps = _solve(
            c=[1, 1],
            A=[[0, 1]],
            b=[5],
            signs=['<='],
            is_max=True,
            lower_bounds=[2, 0],
            upper_bounds=[2, None],
        )
        assert last.is_optimal
        x = solver.recover_original_x(last.x_full)
        assert x[0] == Fraction(2)
        assert x[1] == Fraction(5)


# ============================================================ lower_bounds (сдвиг)
class TestLowerBounds:
    def test_shifted_variable(self):
        """max x1, x1 >= 3, x1 <= 7 → x1* = 7, f* = 7.
        Реализуется через lower_bounds=[3], upper_bounds=[7]."""
        last, solver, steps = _solve(
            c=[1],
            A=[[1]],
            b=[7],
            signs=['<='],
            is_max=True,
            lower_bounds=[3],
            upper_bounds=[7],
        )
        assert last.is_optimal
        x = solver.recover_original_x(last.x_full)
        assert x[0] == Fraction(7)

    def test_nonzero_lower_bound_shifts_b(self):
        """min x1 + x2, x1 + x2 >= 5, x1 >= 2, x2 >= 1.
        Оптимум: f* = 5 (любая точка на грани x1+x2=5 с x1>=2, x2>=1).

        Примечание: _obj считает по внутренним (сдвинутым) переменным.
        Для проверки f* используем recover_original_x и исходные коэффициенты c.
        """
        last, solver, steps = _solve(
            c=[1, 1],
            A=[[1, 1]],
            b=[5],
            signs=['>='],
            is_max=False,
            lower_bounds=[2, 1],
        )
        assert last.is_optimal
        x = solver.recover_original_x(last.x_full)
        # Проверяем выполнение ограничений
        assert x[0] >= Fraction(2), f"x1={x[0]} должно быть >= 2"
        assert x[1] >= Fraction(1), f"x2={x[1]} должно быть >= 1"
        assert x[0] + x[1] >= Fraction(5), f"x1+x2={x[0]+x[1]} должно быть >= 5"
        # Значение целевой функции через исходные переменные (c=[1,1])
        f_star = x[0] + x[1]
        assert f_star == Fraction(5), f"f*={f_star} должно быть 5"


# ============================================================ free variables
class TestFreeVariables:
    def test_free_variable_split(self):
        """max x1 - x2, x1 - x2 <= 5, x1 свободная (lb=None, ub=None).
        Оптимум: x1 - x2 = 5, f* = 5."""
        last, solver, steps = _solve(
            c=[1, -1],
            A=[[1, -1]],
            b=[5],
            signs=['<='],
            is_max=True,
            lower_bounds=[None, 0],
            upper_bounds=[None, None],
        )
        assert last.is_optimal
        assert _obj(last, solver, is_max=True) == Fraction(5)

    def test_free_variable_recover(self):
        """Свободная переменная x1 может быть отрицательной.
        min x1, x1 >= -3 (через lb=-3), x1 <= 10 → x1* = -3."""
        last, solver, steps = _solve(
            c=[1],
            A=[[1]],
            b=[10],
            signs=['<='],
            is_max=False,
            lower_bounds=[-3],
            upper_bounds=[10],
        )
        assert last.is_optimal
        x = solver.recover_original_x(last.x_full)
        assert x[0] == Fraction(-3)


# ============================================================ canonical mode
class TestCanonicalMode:
    def test_canonical_mode_no_artificials(self):
        """Задача в канонической форме с готовым единичным базисом.
        4x1 + x2 + x3 = 16, 2x1 + 2x2 + x4 = 22, 6x1 + 3x2 + x5 = 36.
        max 12x1 + 3x2. Ожидаем f* = 48 без фазы I."""
        last, solver, steps = _solve(
            c=[12, 3, 0, 0, 0],
            A=[
                [4, 1, 1, 0, 0],
                [2, 2, 0, 1, 0],
                [6, 3, 0, 0, 1],
            ],
            b=[16, 22, 36],
            signs=['=', '=', '='],
            is_max=True,
            canonical_mode=True,
        )
        assert last.is_optimal
        # Фаза I не должна присутствовать (орты найдены автоматически)
        assert all(st.phase == 2 for st in steps)
        assert _obj(last, solver, is_max=True) == Fraction(48)

    def test_canonical_mode_partial_identity(self):
        """Частичный единичный базис: одна строка без орта → добавляется искусственная."""
        # x1 + x2 + x3 = 5 (x3 — орт), x1 + x2 = 3 (нет орта → искусственная)
        last, solver, steps = _solve(
            c=[1, 1, 0],
            A=[
                [1, 1, 1],
                [1, 1, 0],
            ],
            b=[5, 3],
            signs=['=', '='],
            is_max=True,
            canonical_mode=True,
        )
        assert last.is_optimal
        assert _obj(last, solver, is_max=True) == Fraction(3)


# ============================================================ recover_original_x
class TestRecoverOriginalX:
    def test_recover_standard(self):
        """Стандартная задача (без редукций): recover_original_x возвращает первые n_orig_vars."""
        last, solver, steps = _solve(
            c=[12, 3],
            A=[[4, 1], [2, 2], [6, 3]],
            b=[16, 22, 36],
            signs=['<=', '<=', '<='],
            is_max=True,
        )
        assert last.is_optimal
        x = solver.recover_original_x(last.x_full)
        assert len(x) == 2
        assert x[0] == Fraction(4)
        assert x[1] == Fraction(0)

    def test_recover_with_shift(self):
        """Переменная со сдвигом: x1 >= 1. Восстановленное x1 должно быть >= 1."""
        last, solver, steps = _solve(
            c=[1, 1],
            A=[[1, 1]],
            b=[5],
            signs=['<='],
            is_max=True,
            lower_bounds=[1, 0],
        )
        assert last.is_optimal
        x = solver.recover_original_x(last.x_full)
        # x1 + x2 = 5, x1 >= 1 → оптимум x1=1, x2=4 или x1=5, x2=0 (любая точка на грани)
        assert x[0] >= Fraction(1)
        assert x[0] + x[1] == Fraction(5)


# ============================================================ u_0_original (знаки двойственных)
class TestDualSignCorrection:
    def test_u0_original_no_inversion(self):
        """Без инверсий строк u_0_original == u_0 (для задачи max)."""
        last, solver, steps = _solve(
            c=[12, 3],
            A=[[4, 1], [2, 2], [6, 3]],
            b=[16, 22, 36],
            signs=['<=', '<=', '<='],
            is_max=True,
        )
        assert last.is_optimal
        assert last.u_0_original is not None
        # Нет инверсий, задача max → u_0_original == u_0
        assert last.u_0_original == last.u_0

    def test_u0_original_with_row_inversion(self):
        """При b_i < 0 строка инвертируется → u_0_original[i] = -u_0[i].

        max x1, x1 <= 5, -x1 <= -2 (эквивалентно x1 >= 2).
        Строка 2 имеет b=-2 < 0 → инвертируется. Оптимум x1=5, f*=5.
        """
        last, solver, steps = _solve(
            c=[1],
            A=[[1], [-1]],
            b=[5, -2],
            signs=['<=', '<='],
            is_max=True,
        )
        assert last.is_optimal
        assert last.row_inverted is not None
        # Строка 1 (индекс 1) была инвертирована (b=-2 < 0)
        assert last.row_inverted[1] is True
        assert last.row_inverted[0] is False
        # u_0_original[1] должен иметь противоположный знак к u_0[1]
        assert last.u_0_original is not None
        if last.u_0[1] != 0:
            assert last.u_0_original[1] == -last.u_0[1]
        # u_0_original[0] совпадает с u_0[0] (строка не инвертирована, задача max)
        assert last.u_0_original[0] == last.u_0[0]

    def test_u0_original_min_problem(self):
        """Для задачи min u_0_original имеет противоположный знак к u_0."""
        last, solver, steps = _solve(
            c=[2, 3],
            A=[[1, 1], [2, 1]],
            b=[3, 4],
            signs=['>=', '>='],
            is_max=False,
        )
        assert last.is_optimal
        assert last.u_0_original is not None
        # Для min: u_0_original = -u_0 (без инверсий строк)
        # Строки >= с b>0 не инвертируются, но задача min → знак меняется
        for i, (u, u_orig) in enumerate(zip(last.u_0, last.u_0_original)):
            if not (last.row_inverted or [])[i] if last.row_inverted else True:
                assert u_orig == -u
