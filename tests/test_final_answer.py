"""Тесты корректности значения целевой функции (final_answer).

Проверяем все комбинации:
- max / min
- без границ (стандартные x >= 0)
- с нижними границами (сдвиг переменных)
- с верхними границами
- с фиксированными переменными (lb == ub)
- смешанные ограничения (<=, >=, =)
- свободные переменные

Для каждого теста вычисляем ожидаемое значение вручную через исходные переменные x*
и исходные коэффициенты c, чтобы убедиться что final_answer = c^T x*.
"""

from fractions import Fraction
import pytest
from core.models import LinearProblem
from core.solver import SimplexSolver


def _run(c, A, b, signs, is_max=True, lower_bounds=None, upper_bounds=None, canonical_mode=False):
    """Запускает солвер, возвращает (final_answer, x_original, solver, last_step)."""
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
    last = steps[-1]

    final_answer = None
    x_original = None
    if last.is_optimal and last.phase == 2:
        final_answer = s.compute_final_answer(last)
        x_original = s.recover_original_x(last.x_full)

    return final_answer, x_original, s, last


def _check(c_orig, x_orig, is_max, expected_f):
    """Проверяет что c^T x* == expected_f."""
    c = [Fraction(v) for v in c_orig]
    f = sum(c[i] * x_orig[i] for i in range(len(c)))
    assert f == Fraction(expected_f), f"c^T x* = {f}, ожидалось {expected_f}, x*={x_orig}"


# ============================================================ Без границ (стандарт)

class TestNoBounds:
    def test_max_simple(self):
        """max 12x1 + 3x2, 3 ограничения <=. Эталон: f*=48, x*=(4,0)."""
        f, x, s, last = _run(
            c=[12, 3],
            A=[[4, 1], [2, 2], [6, 3]],
            b=[16, 22, 36],
            signs=['<=', '<=', '<='],
            is_max=True,
        )
        assert last.is_optimal
        assert f == Fraction(48), f"f*={f}"
        _check([12, 3], x, True, 48)

    def test_min_simple(self):
        """min 2x1 + 3x2, x1+x2>=3, 2x1+x2>=4. Эталон: f*=6, x*=(3,0) или (1,2)."""
        f, x, s, last = _run(
            c=[2, 3],
            A=[[1, 1], [2, 1]],
            b=[3, 4],
            signs=['>=', '>='],
            is_max=False,
        )
        assert last.is_optimal
        assert f == Fraction(6), f"f*={f}"
        _check([2, 3], x, False, 6)

    def test_max_with_equality(self):
        """max 4x1 + x2, x1+2x2<=6, x1+x2=3. Эталон: f*=12, x*=(3,0)."""
        f, x, s, last = _run(
            c=[4, 1],
            A=[[1, 2], [1, 1]],
            b=[6, 3],
            signs=['<=', '='],
            is_max=True,
        )
        assert last.is_optimal
        assert f == Fraction(12), f"f*={f}"
        _check([4, 1], x, True, 12)

    def test_max_mixed_geq(self):
        """max 6x1 + 8x2, 2x1+x2<=10, x1+2x2>=6. Эталон: f*=80, x*=(0,10)."""
        f, x, s, last = _run(
            c=[6, 8],
            A=[[2, 1], [1, 2]],
            b=[10, 6],
            signs=['<=', '>='],
            is_max=True,
        )
        assert last.is_optimal
        assert f == Fraction(80), f"f*={f}"
        _check([6, 8], x, True, 80)

    def test_max_three_vars(self):
        """max 5x1 + 4x2 + 3x3, x1+x2+x3<=10, 2x1+x2<=12, x3<=5.
        Оптимум: x1=6, x2=0, x3=4 → f*=42. Или x1=5,x2=0,x3=5 → f*=40.
        Проверяем что c^T x* == f*."""
        f, x, s, last = _run(
            c=[5, 4, 3],
            A=[[1, 1, 1], [2, 1, 0], [0, 0, 1]],
            b=[10, 12, 5],
            signs=['<=', '<=', '<='],
            is_max=True,
        )
        assert last.is_optimal
        # Проверяем согласованность: c^T x* == f*
        _check([5, 4, 3], x, True, f)
        # Проверяем допустимость
        assert x[0] + x[1] + x[2] <= Fraction(10)
        assert 2*x[0] + x[1] <= Fraction(12)
        assert x[2] <= Fraction(5)


# ============================================================ С нижними границами (сдвиг)

class TestLowerBounds:
    def test_max_with_lb_nonzero(self):
        """max x1 + x2, x1+x2<=10, x1>=3, x2>=2.
        Оптимум: x1=8, x2=2 или x1=3, x2=7 — любая точка на грани.
        f* = 10. Проверяем c^T x* == f* == 10."""
        f, x, s, last = _run(
            c=[1, 1],
            A=[[1, 1]],
            b=[10],
            signs=['<='],
            is_max=True,
            lower_bounds=[3, 2],
        )
        assert last.is_optimal
        assert f == Fraction(10), f"f*={f}"
        _check([1, 1], x, True, 10)
        assert x[0] >= Fraction(3)
        assert x[1] >= Fraction(2)

    def test_max_with_lb_shifts_objective(self):
        """max 46x1 + 10x2 + 14x3, ограничения <=, x1>=40, x2>=250, x3>=210.
        Это задача из описания бага: ответ должен быть 46*40+10*250+14*210 = 7280
        если x* = (40, 250, 210) — минимально допустимая точка.
        Но если есть ограничения сверху, оптимум может быть другим.
        Здесь проверяем что f* = c^T x* корректно."""
        # Простая версия: только нижние границы, ограничение x1+x2+x3 <= 500
        f, x, s, last = _run(
            c=[46, 10, 14],
            A=[[1, 1, 1]],
            b=[500],
            signs=['<='],
            is_max=True,
            lower_bounds=[40, 250, 210],
        )
        assert last.is_optimal
        # Проверяем согласованность: c^T x* == f*
        _check([46, 10, 14], x, True, f)
        # Проверяем допустимость
        assert x[0] >= Fraction(40)
        assert x[1] >= Fraction(250)
        assert x[2] >= Fraction(210)
        assert x[0] + x[1] + x[2] <= Fraction(500)

    def test_min_with_lb(self):
        """min x1 + x2, x1+x2>=5, x1>=2, x2>=1. f*=5."""
        f, x, s, last = _run(
            c=[1, 1],
            A=[[1, 1]],
            b=[5],
            signs=['>='],
            is_max=False,
            lower_bounds=[2, 1],
        )
        assert last.is_optimal
        assert f == Fraction(5), f"f*={f}"
        _check([1, 1], x, False, 5)

    def test_lb_equals_optimal(self):
        """max x1, x1<=7, x1>=7 (фиксированная через lb=ub=7). f*=7."""
        f, x, s, last = _run(
            c=[1],
            A=[[1]],
            b=[7],
            signs=['<='],
            is_max=True,
            lower_bounds=[7],
            upper_bounds=[7],
        )
        assert last.is_optimal
        assert f == Fraction(7), f"f*={f}"
        _check([1], x, True, 7)

    def test_lb_negative(self):
        """min x1, x1>=-3, x1<=10. Оптимум x1=-3, f*=-3."""
        f, x, s, last = _run(
            c=[1],
            A=[[1]],
            b=[10],
            signs=['<='],
            is_max=False,
            lower_bounds=[-3],
            upper_bounds=[10],
        )
        assert last.is_optimal
        assert f == Fraction(-3), f"f*={f}"
        _check([1], x, False, -3)


# ============================================================ С верхними границами

class TestUpperBounds:
    def test_ub_restricts_max(self):
        """max x1 + x2, x1+x2<=10, x1<=3. f*=10, x1=3, x2=7."""
        f, x, s, last = _run(
            c=[1, 1],
            A=[[1, 1]],
            b=[10],
            signs=['<='],
            is_max=True,
            upper_bounds=[3, None],
        )
        assert last.is_optimal
        assert f == Fraction(10), f"f*={f}"
        _check([1, 1], x, True, 10)
        assert x[0] == Fraction(3)
        assert x[1] == Fraction(7)

    def test_ub_and_lb(self):
        """max x1 + x2, x2<=5, x1 фиксирована в 2 (lb=ub=2). f*=7."""
        f, x, s, last = _run(
            c=[1, 1],
            A=[[0, 1]],
            b=[5],
            signs=['<='],
            is_max=True,
            lower_bounds=[2, 0],
            upper_bounds=[2, None],
        )
        assert last.is_optimal
        assert f == Fraction(7), f"f*={f}"
        _check([1, 1], x, True, 7)


# ============================================================ Дробные коэффициенты

class TestFractionalCoeffs:
    def test_fractional_objective(self):
        """max (1/2)x1 + (1/3)x2, x1+x2<=6. Оптимум x1=6, x2=0, f*=3."""
        f, x, s, last = _run(
            c=[Fraction(1, 2), Fraction(1, 3)],
            A=[[1, 1]],
            b=[6],
            signs=['<='],
            is_max=True,
        )
        assert last.is_optimal
        assert f == Fraction(3), f"f*={f}"
        _check([Fraction(1, 2), Fraction(1, 3)], x, True, 3)

    def test_fractional_lb(self):
        """max x1, x1<=5, x1>=(3/2). Оптимум x1=5, f*=5."""
        f, x, s, last = _run(
            c=[1],
            A=[[1]],
            b=[5],
            signs=['<='],
            is_max=True,
            lower_bounds=[Fraction(3, 2)],
        )
        assert last.is_optimal
        assert f == Fraction(5), f"f*={f}"
        _check([1], x, True, 5)


# ============================================================ Согласованность c^T x* == f*

class TestConsistency:
    """Для любой задачи: final_answer должен совпадать с c^T x* через исходные переменные."""

    def test_consistency_max_no_bounds(self):
        f, x, s, last = _run(
            c=[3, 5],
            A=[[1, 0], [0, 2], [3, 2]],
            b=[4, 12, 18],
            signs=['<=', '<=', '<='],
            is_max=True,
        )
        assert last.is_optimal
        _check([3, 5], x, True, f)

    def test_consistency_min_geq(self):
        f, x, s, last = _run(
            c=[1, 2],
            A=[[1, 1], [1, 0]],
            b=[4, 2],
            signs=['>=', '>='],
            is_max=False,
        )
        assert last.is_optimal
        _check([1, 2], x, False, f)

    def test_consistency_with_lb(self):
        """Задача с нижними границами: f* должен совпадать с c^T x* через исходные x."""
        f, x, s, last = _run(
            c=[2, 3],
            A=[[1, 1], [1, 2]],
            b=[20, 30],
            signs=['<=', '<='],
            is_max=True,
            lower_bounds=[5, 3],
        )
        assert last.is_optimal
        _check([2, 3], x, True, f)
        assert x[0] >= Fraction(5)
        assert x[1] >= Fraction(3)

    def test_consistency_with_ub(self):
        f, x, s, last = _run(
            c=[4, 3],
            A=[[2, 1], [1, 2]],
            b=[10, 10],
            signs=['<=', '<='],
            is_max=True,
            upper_bounds=[4, None],
        )
        assert last.is_optimal
        _check([4, 3], x, True, f)
        assert x[0] <= Fraction(4)
