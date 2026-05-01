"""
Двухфазный модифицированный симплекс-метод.

См. task/algorith.md для математического описания.
"""

from typing import List, Generator, Optional
from fractions import Fraction
from core.models import LinearProblem, SimplexStep


class SimplexSolver:
    def __init__(self, problem: LinearProblem):
        self.problem = problem
        self.n_orig_vars = len(problem.c)
        self.n_constraints = len(problem.A)

        self.is_max = problem.is_max
        # Минимизацию сводим к максимизации, в main.py финальный ответ корректируется обратно.
        self.c: List[Fraction] = [c if self.is_max else -c for c in problem.c]
        self.A: List[List[Fraction]] = [[v for v in row] for row in problem.A]
        self.b: List[Fraction] = [v for v in problem.b]
        self.signs: List[str] = [s for s in problem.signs]

        self.n_vars: int = self.n_orig_vars
        self.N: List[int] = []                 # упорядоченный список базисных индексов
        self.artificial: List[int] = []        # индексы искусственных переменных

        self._to_canonical()

    # ---------------------------------------------------------------- caconical
    def _to_canonical(self) -> None:
        """Приводит задачу к канонической форме Ax = b, x >= 0, b >= 0.

        Добавляет балансовые/избыточные/искусственные переменные. Заполняет
        начальный базис self.N (один индекс на каждое ограничение)."""

        # 1. Делаем все b_i >= 0
        for i in range(self.n_constraints):
            if self.b[i] < 0:
                self.b[i] = -self.b[i]
                for j in range(self.n_vars):
                    self.A[i][j] = -self.A[i][j]
                if self.signs[i] == '<=':
                    self.signs[i] = '>='
                elif self.signs[i] == '>=':
                    self.signs[i] = '<='
                # '=' остаётся '='

        # 2. Для каждой строки добавляем нужные переменные.
        #    Сначала отметим, какой переменной строка попадёт в начальный базис.
        self.N = [-1] * self.n_constraints
        for i in range(self.n_constraints):
            sign = self.signs[i]
            if sign == '<=':
                # балансовая s_i: коэффициент +1 в строке i
                self._append_var(coeff_row=i, coeff=Fraction(1), c_value=Fraction(0))
                self.N[i] = self.n_vars - 1
            elif sign == '>=':
                # избыточная s_i: коэффициент -1
                self._append_var(coeff_row=i, coeff=Fraction(-1), c_value=Fraction(0))
                # искусственная y_i: коэффициент +1
                self._append_var(coeff_row=i, coeff=Fraction(1), c_value=Fraction(0))
                self.artificial.append(self.n_vars - 1)
                self.N[i] = self.n_vars - 1
            elif sign == '=':
                # только искусственная y_i
                self._append_var(coeff_row=i, coeff=Fraction(1), c_value=Fraction(0))
                self.artificial.append(self.n_vars - 1)
                self.N[i] = self.n_vars - 1
            else:
                raise ValueError(f"Неизвестный знак ограничения: {sign}")

    def _append_var(self, coeff_row: int, coeff: Fraction, c_value: Fraction) -> None:
        """Добавляет новый столбец в A и расширяет c."""
        for r in range(self.n_constraints):
            self.A[r].append(coeff if r == coeff_row else Fraction(0))
        self.c.append(c_value)
        self.n_vars += 1

    # ---------------------------------------------------------------- public
    def solve(self) -> Generator[SimplexStep, None, None]:
        # Стартовая обратная базисная матрица — единичная (т.к. начальный базис
        # составлен из единичных столбцов: балансовых или искусственных).
        B_inv = [[Fraction(1) if i == j else Fraction(0)
                  for j in range(self.n_constraints)]
                 for i in range(self.n_constraints)]

        iteration_counter = [0]  # mutable wrapper for closure-style increment

        # ---------- Фаза I (если есть искусственные) ----------
        if self.artificial:
            # Целевая функция фазы I: -sum(y_i) -> max ⇔ min sum y_i.
            phase1_c: List[Fraction] = [Fraction(0)] * self.n_vars
            for idx in self.artificial:
                phase1_c[idx] = Fraction(-1)

            # Запрещённые для ввода переменные на фазе I — пустое множество
            forbidden: set = set()

            terminated, B_inv = yield from self._run_phase(
                B_inv, phase1_c, phase=1, forbidden=forbidden,
                iteration_counter=iteration_counter,
            )
            if terminated == 'infeasible':
                return
            if terminated == 'unbounded':
                # На фазе I это невозможно при корректной формулировке, но защитимся.
                return

            # Вычислим x_B и проверим w_min
            x_B = self._mat_vec_mult(B_inv, self.b)
            w_min = sum(
                phase1_c[self.N[i]] * x_B[i] for i in range(self.n_constraints)
            )
            # Минимум исходной задачи фазы I = -(c_phase1 . x_B), поскольку c_phase1 = -1 для y.
            # w_min здесь = -sum(y), и если sum(y) > 0, то w_min < 0.
            if w_min < 0:
                yield SimplexStep(
                    iteration=iteration_counter[0],
                    N=list(self.N),
                    B_inv=[r[:] for r in B_inv],
                    x_B=x_B,
                    x_full=self._build_full_x(x_B),
                    u_0=[Fraction(0)] * self.n_constraints,
                    phase=1,
                    is_optimal=False,
                    is_infeasible=True,
                    description="Задача несовместна: на фазе I минимум суммы искусственных переменных строго положителен.",
                    artificial_indices=list(self.artificial),
                )
                return

            # Если в базисе остались искусственные с нулевым значением — попытаемся их вытеснить.
            B_inv = self._purge_artificials_from_basis(B_inv, x_B)

        # ---------- Фаза II ----------
        forbidden = set(self.artificial)
        yield from self._run_phase(
            B_inv, self.c, phase=2, forbidden=forbidden,
            iteration_counter=iteration_counter,
        )

    # ---------------------------------------------------------------- phase loop
    def _run_phase(
        self,
        B_inv: List[List[Fraction]],
        c_vec: List[Fraction],
        phase: int,
        forbidden: set,
        iteration_counter: list,
    ):
        """Внутренний цикл симплекс-метода для одной фазы.

        Возвращает (status, B_inv), где status ∈ {None, 'optimal', 'infeasible', 'unbounded'}.
        Все промежуточные шаги отдаются через yield.
        """
        m = self.n_constraints

        while True:
            iteration_counter[0] += 1

            x_B = self._mat_vec_mult(B_inv, self.b)
            c_B = [c_vec[idx] for idx in self.N]
            u_0 = self._vec_mat_mult(c_B, B_inv)

            # --- проверка оптимальности: правило ПЕРВОГО индекса (Бленд) ---
            j_0: Optional[int] = None
            diffs: List[tuple] = []  # (j, Δ_j), считаем до первого Δ<0 включительно
            basis_set = set(self.N)

            for j in range(self.n_vars):
                if j in basis_set:
                    continue
                if j in forbidden:
                    continue
                A_j = [self.A[i][j] for i in range(m)]
                u_A = sum(u_0[i] * A_j[i] for i in range(m))
                diff = u_A - c_vec[j]
                diffs.append((j, diff))
                if diff < 0:
                    j_0 = j
                    break  # ПРЕРЫВАЕМ — берём первый

            x_full = self._build_full_x(x_B)

            if j_0 is None:
                # План оптимален в этой фазе.
                yield SimplexStep(
                    iteration=iteration_counter[0],
                    N=list(self.N),
                    B_inv=[r[:] for r in B_inv],
                    x_B=x_B,
                    x_full=x_full,
                    u_0=u_0,
                    phase=phase,
                    is_optimal=True,
                    description=(
                        "Фаза I завершена. Все искусственные равны нулю — переходим к фазе II."
                        if phase == 1 else
                        "План оптимален. Все двойственные ограничения выполнены."
                    ),
                    c_B=c_B,
                    diffs=diffs,
                    artificial_indices=list(self.artificial),
                )
                return ('optimal', B_inv)

            # --- направляющий вектор и выбор переменной на вывод ---
            A_j0 = [self.A[i][j_0] for i in range(m)]
            z_0 = self._mat_vec_mult(B_inv, A_j0)

            if all(z <= 0 for z in z_0):
                # Целевая функция не ограничена.
                yield SimplexStep(
                    iteration=iteration_counter[0],
                    N=list(self.N),
                    B_inv=[r[:] for r in B_inv],
                    x_B=x_B,
                    x_full=x_full,
                    u_0=u_0,
                    phase=phase,
                    is_optimal=False,
                    is_unbounded=True,
                    j_0=j_0,
                    z_0=z_0,
                    description="Целевая функция не ограничена сверху. Решения нет.",
                    c_B=c_B,
                    diffs=diffs,
                    artificial_indices=list(self.artificial),
                )
                return ('unbounded', B_inv)

            # Минимальное отношение + правило Бленда при ничьей.
            t_0: Optional[Fraction] = None
            s_0: int = -1
            ratios: List[Optional[Fraction]] = []
            for i in range(m):
                if z_0[i] > 0:
                    ratio = x_B[i] / z_0[i]
                    ratios.append(ratio)
                    if t_0 is None or ratio < t_0 or (ratio == t_0 and self.N[i] < self.N[s_0]):
                        t_0 = ratio
                        s_0 = i
                else:
                    ratios.append(None)

            yield SimplexStep(
                iteration=iteration_counter[0],
                N=list(self.N),
                B_inv=[r[:] for r in B_inv],
                x_B=x_B,
                x_full=x_full,
                u_0=u_0,
                phase=phase,
                is_optimal=False,
                j_0=j_0,
                z_0=z_0,
                t_0=t_0,
                s_0=self.N[s_0],
                description=(
                    f"Фаза {phase}. План не оптимален. Вводим x_{{{j_0+1}}} в базис, "
                    f"выводим x_{{{self.N[s_0]+1}}}."
                ),
                c_B=c_B,
                diffs=diffs,
                ratios=ratios,
                artificial_indices=list(self.artificial),
            )

            # --- pivot ---
            self.N[s_0] = j_0
            B_inv = self._pivot(B_inv, z_0, s_0)

    # ---------------------------------------------------------------- helpers
    def _purge_artificials_from_basis(
        self, B_inv: List[List[Fraction]], x_B: List[Fraction]
    ) -> List[List[Fraction]]:
        """Пытается вывести из базиса искусственные переменные с нулевым значением."""
        m = self.n_constraints
        artificial_set = set(self.artificial)
        i = 0
        while i < m:
            if self.N[i] in artificial_set and x_B[i] == 0:
                # Ищем небазисный неискусственный j с z_0[i] != 0.
                replaced = False
                for j in range(self.n_vars):
                    if j in artificial_set or j in self.N:
                        continue
                    A_j = [self.A[r][j] for r in range(m)]
                    z = self._mat_vec_mult(B_inv, A_j)
                    if z[i] != 0:
                        self.N[i] = j
                        B_inv = self._pivot(B_inv, z, i)
                        replaced = True
                        break
                # Если не удалось заменить — строка линейно зависима, оставим как есть.
                # (Артикль с нулём в базисе и forbidden-ом в фазе II останется неактивным.)
            i += 1
        return B_inv

    def _pivot(
        self, B_inv: List[List[Fraction]], z_0: List[Fraction], s_0: int
    ) -> List[List[Fraction]]:
        """Возвращает обновлённую обратную базисную матрицу после Gauss-Jordan."""
        m = self.n_constraints
        pivot = z_0[s_0]
        new_B = [row[:] for row in B_inv]
        for j in range(m):
            new_B[s_0][j] = new_B[s_0][j] / pivot
        for i in range(m):
            if i != s_0:
                factor = z_0[i]
                if factor != 0:
                    for j in range(m):
                        new_B[i][j] = new_B[i][j] - factor * new_B[s_0][j]
        return new_B

    def _build_full_x(self, x_B: List[Fraction]) -> List[Fraction]:
        x = [Fraction(0)] * self.n_vars
        for i, idx in enumerate(self.N):
            x[idx] = x_B[i]
        return x

    @staticmethod
    def _mat_vec_mult(M: List[List[Fraction]], v: List[Fraction]) -> List[Fraction]:
        return [sum((M[i][j] * v[j] for j in range(len(v))), Fraction(0))
                for i in range(len(M))]

    @staticmethod
    def _vec_mat_mult(v: List[Fraction], M: List[List[Fraction]]) -> List[Fraction]:
        cols = len(M[0])
        res: List[Fraction] = [Fraction(0)] * cols
        for j in range(cols):
            res[j] = sum((v[i] * M[i][j] for i in range(len(v))), Fraction(0))
        return res
