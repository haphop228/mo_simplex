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


# ============================================================ regressions: lb + ub, var_map sync
class TestLowerAndUpperBoundCombined:
    """Регрессионные тесты для багов #1 (игнорируемая верхняя граница при lb != 0)
    и #2 (рассинхронизация _var_map с матрицей A)."""

    def test_lb_positive_and_upper_bound(self):
        """Bug #1: max x1, x1+x2<=100, x1 ∈ [3, 10] → f*=10."""
        p = LinearProblem(
            c=[Fraction(1), Fraction(0)],
            A=[[Fraction(1), Fraction(1)]],
            b=[Fraction(100)],
            signs=['<='],
            is_max=True,
            lower_bounds=[Fraction(3), Fraction(0)],
            upper_bounds=[Fraction(10), None],
        )
        s = SimplexSolver(p)
        last = list(s.solve())[-1]
        assert last.is_optimal
        x = s.recover_original_x(last.x_full)
        assert x[0] == Fraction(10)
        assert s.compute_final_answer(last) == Fraction(10)

    def test_lb_negative_and_upper_bound(self):
        """Bug #1: max x1, x1+x2<=100, x1 ∈ [-5, 7] → f*=7."""
        p = LinearProblem(
            c=[Fraction(1), Fraction(0)],
            A=[[Fraction(1), Fraction(1)]],
            b=[Fraction(100)],
            signs=['<='],
            is_max=True,
            lower_bounds=[Fraction(-5), Fraction(0)],
            upper_bounds=[Fraction(7), None],
        )
        s = SimplexSolver(p)
        last = list(s.solve())[-1]
        assert last.is_optimal
        x = s.recover_original_x(last.x_full)
        assert x[0] == Fraction(7)
        assert s.compute_final_answer(last) == Fraction(7)

    def test_fixed_var_in_middle(self):
        """Bug #2: fixed-переменная в середине + сдвинутая после неё.
        max x1+x2+x3, x1+x2+x3<=10, lb=[0,2,-3], ub=[None,2,None].
        x2 фиксирована (lb=ub=2) → x2 ОБЯЗАТЕЛЬНО = 2, f*=10."""
        p = LinearProblem(
            c=[Fraction(1)] * 3,
            A=[[Fraction(1)] * 3],
            b=[Fraction(10)],
            signs=['<='],
            is_max=True,
            lower_bounds=[Fraction(0), Fraction(2), Fraction(-3)],
            upper_bounds=[None, Fraction(2), None],
        )
        s = SimplexSolver(p)
        last = list(s.solve())[-1]
        assert last.is_optimal
        x = s.recover_original_x(last.x_full)
        assert x[1] == Fraction(2), f"x2 должно быть строго 2, но получено {x[1]}"
        # Проверка ограничения
        assert x[0] + x[1] + x[2] <= Fraction(10)
        assert x[0] >= Fraction(0)
        assert x[2] >= Fraction(-3)
        assert s.compute_final_answer(last) == Fraction(10)

    def test_free_then_shifted(self):
        """Bug #2: свободная x1 + сдвинутая x2.
        max x1+x2, x1+x2<=10, x1 свободная, x2>=2.
        recover_original_x не должен падать с IndexError."""
        p = LinearProblem(
            c=[Fraction(1), Fraction(1)],
            A=[[Fraction(1), Fraction(1)]],
            b=[Fraction(10)],
            signs=['<='],
            is_max=True,
            lower_bounds=[None, Fraction(2)],
            upper_bounds=[None, None],
        )
        s = SimplexSolver(p)
        last = list(s.solve())[-1]
        assert last.is_optimal
        x = s.recover_original_x(last.x_full)  # не должно падать
        assert x[1] >= Fraction(2)
        assert x[0] + x[1] == Fraction(10)
        assert s.compute_final_answer(last) == Fraction(10)


# ============================================================ sanity: compute_final_answer ⟺ c·x
class TestComputeFinalAnswerConsistency:
    """Регрессионный тест для бага #4: compute_final_answer всегда должна
    совпадать с прямым произведением c_orig^T x_orig."""

    @staticmethod
    def _build_and_check(c, A, b, signs, is_max=True,
                         lower_bounds=None, upper_bounds=None):
        p = LinearProblem(
            c=[Fraction(x) for x in c],
            A=[[Fraction(x) for x in r] for r in A],
            b=[Fraction(x) for x in b],
            signs=signs,
            is_max=is_max,
            lower_bounds=[Fraction(v) if v is not None else None
                          for v in lower_bounds] if lower_bounds else None,
            upper_bounds=[Fraction(v) if v is not None else None
                          for v in upper_bounds] if upper_bounds else None,
        )
        s = SimplexSolver(p)
        last = list(s.solve())[-1]
        assert last.is_optimal, "задача должна быть разрешима"
        x_orig = s.recover_original_x(last.x_full)
        f_solver = s.compute_final_answer(last)
        f_manual = sum(
            (p.c[i] * x_orig[i] for i in range(s.n_orig_vars)),
            Fraction(0),
        )
        assert f_solver == f_manual, (
            f"f_solver={f_solver}, c^T x={f_manual}, x_orig={x_orig}"
        )

    def test_standard_no_bounds_max(self):
        self._build_and_check(
            c=[12, 3], A=[[4, 1], [2, 2], [6, 3]], b=[16, 22, 36],
            signs=['<=', '<=', '<='], is_max=True,
        )

    def test_standard_no_bounds_min(self):
        self._build_and_check(
            c=[2, 3], A=[[1, 1], [2, 1]], b=[3, 4],
            signs=['>=', '>='], is_max=False,
        )

    def test_with_lb_shift(self):
        self._build_and_check(
            c=[1, 1], A=[[1, 1]], b=[10], signs=['<='],
            is_max=True, lower_bounds=[3, 0], upper_bounds=[10, None],
        )

    def test_with_negative_lb(self):
        self._build_and_check(
            c=[1, 0], A=[[1, 1]], b=[100], signs=['<='],
            is_max=True, lower_bounds=[-5, 0], upper_bounds=[7, None],
        )

    def test_with_fixed_var(self):
        self._build_and_check(
            c=[1, 1, 1], A=[[1, 1, 1]], b=[10], signs=['<='],
            is_max=True,
            lower_bounds=[0, 2, -3], upper_bounds=[None, 2, None],
        )

    def test_with_free_var(self):
        self._build_and_check(
            c=[1, 1], A=[[1, 1]], b=[10], signs=['<='],
            is_max=True, lower_bounds=[None, 2], upper_bounds=[None, None],
        )

    def test_xample_regression(self):
        """Контрольная регрессия из xample.md: f*=7280, x*=[40,250,210]."""
        self._build_and_check(
            c=[46, 10, 14],
            A=[[1, 1, 1], [1, 0, 0]],
            b=[500, 40],
            signs=['=', '>='],
            is_max=False,
            lower_bounds=[0, 0, 100], upper_bounds=[None, 250, None],
        )


# ============================================================ validate_solution (защитная сетка)
class TestValidateSolution:
    """Регрессия для бага #5: проверка того, что восстановленное решение
    удовлетворяет ИСХОДНЫМ ограничениям задачи."""

    @staticmethod
    def _make_solver(lower_bounds=None, upper_bounds=None):
        p = LinearProblem(
            c=[Fraction(1), Fraction(0)],
            A=[[Fraction(1), Fraction(1)]],
            b=[Fraction(100)],
            signs=['<='],
            is_max=True,
            lower_bounds=[Fraction(v) if v is not None else None
                          for v in lower_bounds] if lower_bounds else None,
            upper_bounds=[Fraction(v) if v is not None else None
                          for v in upper_bounds] if upper_bounds else None,
        )
        return SimplexSolver(p)

    def test_validate_valid_solution(self):
        """Корректное решение → validate_solution возвращает пустой список."""
        s = self._make_solver(
            lower_bounds=[3, 0], upper_bounds=[10, None],
        )
        last = list(s.solve())[-1]
        x = s.recover_original_x(last.x_full)
        errs = s.validate_solution(x)
        assert errs == [], f"неожиданные ошибки: {errs}"
        # Также step.validation_errors должен быть None.
        assert last.validation_errors is None

    def test_validate_upper_bound_violation(self):
        """Искусственно подсовываем x, нарушающий ub → validate возвращает ошибку."""
        s = self._make_solver(
            lower_bounds=[3, 0], upper_bounds=[10, None],
        )
        last = list(s.solve())[-1]
        bad_x = [Fraction(100), Fraction(0)]  # ub=10, нарушение
        errs = s.validate_solution(bad_x)
        assert errs, "должна быть как минимум одна ошибка валидации"
        assert any("upper_bound" in e for e in errs), errs

    def test_validate_lower_bound_violation(self):
        s = self._make_solver(
            lower_bounds=[3, 0], upper_bounds=[10, None],
        )
        last = list(s.solve())[-1]
        bad_x = [Fraction(1), Fraction(0)]  # lb=3, нарушение
        errs = s.validate_solution(bad_x)
        assert errs
        assert any("lower_bound" in e for e in errs), errs

    def test_validate_constraint_violation(self):
        """Нарушение исходного ограничения x1+x2 <= 100."""
        s = self._make_solver(
            lower_bounds=[0, 0], upper_bounds=[None, None],
        )
        last = list(s.solve())[-1]
        bad_x = [Fraction(60), Fraction(60)]  # 120 > 100
        errs = s.validate_solution(bad_x)
        assert errs
        assert any("ограничение" in e for e in errs), errs

    def test_validation_errors_on_final_step_is_none_for_correct_solve(self):
        """Для любых корректно решённых задач из аудита #1-#4
        step.validation_errors на финальном шаге = None."""
        # Bug#1: lb=3, ub=10
        s = self._make_solver(lower_bounds=[3, 0], upper_bounds=[10, None])
        last = list(s.solve())[-1]
        assert last.validation_errors is None

        # Bug#1: lb=-5, ub=7
        s = self._make_solver(lower_bounds=[-5, 0], upper_bounds=[7, None])
        last = list(s.solve())[-1]
        assert last.validation_errors is None

        # Bug#2: fixed-в-середине
        p = LinearProblem(
            c=[Fraction(1)] * 3,
            A=[[Fraction(1)] * 3],
            b=[Fraction(10)],
            signs=['<='],
            is_max=True,
            lower_bounds=[Fraction(0), Fraction(2), Fraction(-3)],
            upper_bounds=[None, Fraction(2), None],
        )
        s2 = SimplexSolver(p)
        last = list(s2.solve())[-1]
        assert last.validation_errors is None, last.validation_errors
