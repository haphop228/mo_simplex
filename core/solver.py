"""
Двухфазный модифицированный симплекс-метод.

См. task/algorith.md для математического описания.
"""

from typing import List, Generator, Optional, Tuple
from fractions import Fraction
from core.models import LinearProblem, SimplexStep, Bound


class SimplexSolver:
    def __init__(self, problem: LinearProblem, canonical_mode: bool = False):
        """
        Parameters
        ----------
        problem : LinearProblem
            Задача ЛП в общей форме.
        canonical_mode : bool
            Если True — задача уже в канонической форме (Ax=b, x>=0).
            Солвер попытается найти единичные столбцы-орты и использовать
            их как начальный базис без добавления искусственных переменных.
        """
        self.problem = problem
        self.n_orig_vars = len(problem.c)
        self.n_constraints = len(problem.A)
        self.canonical_mode = canonical_mode

        self.is_max = problem.is_max
        # Минимизацию сводим к максимизации; в main.py финальный ответ корректируется обратно.
        self.c: List[Fraction] = [c if self.is_max else -c for c in problem.c]
        self.A: List[List[Fraction]] = [[v for v in row] for row in problem.A]
        self.b: List[Fraction] = [v for v in problem.b]
        self.signs: List[str] = [s for s in problem.signs]

        # Границы переменных (по умолчанию x_j >= 0, без верхней границы)
        n = self.n_orig_vars
        raw_lb = problem.lower_bounds or [Fraction(0)] * n
        raw_ub = problem.upper_bounds or [None] * n
        self.lower_bounds: List[Bound] = list(raw_lb)
        self.upper_bounds: List[Bound] = list(raw_ub)

        self.n_vars: int = self.n_orig_vars
        self.N: List[int] = []          # упорядоченный список базисных индексов
        self.artificial: List[int] = [] # индексы искусственных переменных

        # Карта перевода: список (тип, исходный_индекс, сдвиг) для восстановления x*.
        # Типы: 'direct' — x'_j = x_j - shift (shift = l_j),
        #        'neg'    — x'_j = -x_j (x_j <= 0),
        #        'split+' — x_j = x_j^+ - x_j^- (положительная часть),
        #        'split-' — отрицательная часть (парная к split+).
        self._var_map: List[Tuple[str, int, Fraction]] = []

        # Флаги инверсии строк (True = строка была умножена на -1 при b_i < 0)
        self._row_inverted: List[bool] = [False] * self.n_constraints

        self._to_canonical()

    # ---------------------------------------------------------------- canonical
    def _to_canonical(self) -> None:
        """Приводит задачу к канонической форме Ax = b, x >= 0, b >= 0.

        Шаги:
        1. Редукции переменных (сдвиги, замены знака, расщепление свободных).
        2. Нормализация b >= 0 (умножение строк на -1).
        3. Добавление верхних границ как дополнительных ограничений.
        4. Добавление балансовых/избыточных/искусственных переменных.
        """
        # --- Шаг 1. Редукции переменных ---
        self._apply_variable_reductions()

        # --- Шаг 2. Нормализация b >= 0 ---
        for i in range(self.n_constraints):
            if self.b[i] < 0:
                self.b[i] = -self.b[i]
                for j in range(self.n_vars):
                    self.A[i][j] = -self.A[i][j]
                if self.signs[i] == '<=':
                    self.signs[i] = '>='
                elif self.signs[i] == '>=':
                    self.signs[i] = '<='
                self._row_inverted[i] = True

        # --- Шаг 3. Верхние границы как дополнительные ограничения ---
        # (применяется только к исходным переменным после редукций;
        #  после _apply_variable_reductions верхние границы уже сброшены)
        # Верхние границы обрабатываются внутри _apply_variable_reductions.

        # --- Шаг 4. Начальный базис ---
        if self.canonical_mode:
            self._build_canonical_basis()
        else:
            self._build_artificial_basis()

    def _apply_variable_reductions(self) -> None:
        """Применяет редукции переменных согласно таблице 1.2 algorith.md."""
        n = self.n_orig_vars
        # Инициализируем карту: изначально все переменные — прямые с нулевым сдвигом
        self._var_map = [('direct', j, Fraction(0)) for j in range(n)]

        j = 0
        while j < n:
            lb = self.lower_bounds[j]
            ub = self.upper_bounds[j]

            # Определяем тип переменной
            lb_is_none = (lb is None)
            ub_is_none = (ub is None)

            if not lb_is_none and not ub_is_none and lb == ub:
                # Фиксированная переменная: x_j = lb. Подставляем и убираем.
                # Вычитаем A_j * lb из b, убираем столбец.
                shift = lb
                for i in range(self.n_constraints):
                    self.b[i] -= self.A[i][j] * shift
                # Убираем столбец j из A и c
                for i in range(self.n_constraints):
                    self.A[i].pop(j)
                self.c.pop(j)
                self.lower_bounds.pop(j)
                self.upper_bounds.pop(j)
                self._var_map[j] = ('fixed', j, shift)
                # Сдвигаем карту для последующих переменных
                n -= 1
                self.n_vars -= 1
                # j не увеличиваем — следующая переменная теперь на том же индексе
                continue

            if lb_is_none and ub_is_none:
                # Свободная переменная: x_j = x_j^+ - x_j^-
                self._split_free_variable(j)
                self._var_map[j] = ('split+', j, Fraction(0))
                self._var_map.insert(j + 1, ('split-', j, Fraction(0)))
                n += 1
                j += 2  # пропускаем обе части
                continue

            if not lb_is_none and lb < 0 and ub_is_none:
                # x_j >= lb < 0: сдвиг x_j' = x_j - lb, x_j' >= 0
                shift = lb
                self._shift_variable(j, shift)
                self._var_map[j] = ('direct', j, shift)
                self.lower_bounds[j] = Fraction(0)
                j += 1
                continue

            if lb_is_none and not ub_is_none:
                # x_j <= ub (без нижней границы) — свободная сверху.
                # Заменяем x_j' = ub - x_j >= 0 (инвертируем столбец, сдвигаем b).
                shift = ub
                for i in range(self.n_constraints):
                    self.b[i] -= self.A[i][j] * shift
                    self.A[i][j] = -self.A[i][j]
                self.c[j] = -self.c[j]
                self._var_map[j] = ('neg_shift', j, shift)
                self.lower_bounds[j] = Fraction(0)
                self.upper_bounds[j] = None
                j += 1
                continue

            if not lb_is_none and lb != 0:
                # x_j >= lb != 0: сдвиг x_j' = x_j - lb
                shift = lb
                self._shift_variable(j, shift)
                self._var_map[j] = ('direct', j, shift)
                self.lower_bounds[j] = Fraction(0)
                # Если есть верхняя граница — пересчитываем
                if not ub_is_none:
                    self.upper_bounds[j] = ub - shift
                j += 1
                continue

            if not ub_is_none and lb == Fraction(0):
                # x_j <= ub при x_j >= 0: добавляем ограничение x_j + s = ub
                # Это делается через дополнительную строку <=
                self._add_upper_bound_constraint(j, ub)
                self.upper_bounds[j] = None
                j += 1
                continue

            # Стандартный случай: x_j >= 0, без верхней границы
            j += 1

    def _shift_variable(self, j: int, shift: Fraction) -> None:
        """Сдвигает переменную j: x_j' = x_j - shift. Обновляет b."""
        for i in range(self.n_constraints):
            self.b[i] -= self.A[i][j] * shift

    def _split_free_variable(self, j: int) -> None:
        """Расщепляет свободную переменную j: x_j = x_j^+ - x_j^-.
        Вставляет новый столбец -A_j после столбца j."""
        for i in range(self.n_constraints):
            self.A[i].insert(j + 1, -self.A[i][j])
        self.c.insert(j + 1, -self.c[j])
        self.lower_bounds.insert(j + 1, Fraction(0))
        self.upper_bounds.insert(j + 1, None)
        self.n_vars += 1

    def _add_upper_bound_constraint(self, j: int, ub: Fraction) -> None:
        """Добавляет ограничение x_j <= ub как новую строку системы."""
        m = self.n_constraints
        new_row = [Fraction(0)] * self.n_vars
        new_row[j] = Fraction(1)
        self.A.append(new_row)
        self.b.append(ub)
        self.signs.append('<=')
        self._row_inverted.append(False)
        self.n_constraints += 1

    def _build_artificial_basis(self) -> None:
        """Строит начальный базис с балансовыми/искусственными переменными."""
        self.N = [-1] * self.n_constraints
        for i in range(self.n_constraints):
            sign = self.signs[i]
            if sign == '<=':
                self._append_var(coeff_row=i, coeff=Fraction(1), c_value=Fraction(0))
                self.N[i] = self.n_vars - 1
            elif sign == '>=':
                self._append_var(coeff_row=i, coeff=Fraction(-1), c_value=Fraction(0))
                self._append_var(coeff_row=i, coeff=Fraction(1), c_value=Fraction(0))
                self.artificial.append(self.n_vars - 1)
                self.N[i] = self.n_vars - 1
            elif sign == '=':
                self._append_var(coeff_row=i, coeff=Fraction(1), c_value=Fraction(0))
                self.artificial.append(self.n_vars - 1)
                self.N[i] = self.n_vars - 1
            else:
                raise ValueError(f"Неизвестный знак ограничения: {sign}")

    def _build_canonical_basis(self) -> None:
        """Авто-детектор ортов для канонической формы.

        Для каждой строки ищет столбец с единственной единицей (+1) и нулями
        в остальных строках. Если для всех строк такой столбец найден —
        используем их как начальный базис без искусственных переменных.
        Для строк, где орт не найден, добавляем искусственную переменную.
        """
        m = self.n_constraints
        n = self.n_vars
        self.N = [-1] * m

        # Для каждого столбца проверяем, является ли он ортом
        col_is_unit: dict[int, int] = {}  # col -> row_index
        for j in range(n):
            col = [self.A[i][j] for i in range(m)]
            ones = [i for i, v in enumerate(col) if v == Fraction(1)]
            zeros = [i for i, v in enumerate(col) if v == Fraction(0)]
            if len(ones) == 1 and len(zeros) == m - 1:
                col_is_unit[j] = ones[0]

        # Назначаем орты в базис (каждый орт — в свою строку, без повторений)
        used_rows: set = set()
        for j, row in col_is_unit.items():
            if row not in used_rows and self.N[row] == -1:
                self.N[row] = j
                used_rows.add(row)

        # Для строк без орта добавляем искусственные переменные
        for i in range(m):
            if self.N[i] == -1:
                self._append_var(coeff_row=i, coeff=Fraction(1), c_value=Fraction(0))
                self.artificial.append(self.n_vars - 1)
                self.N[i] = self.n_vars - 1

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
            phase1_c: List[Fraction] = [Fraction(0)] * self.n_vars
            for idx in self.artificial:
                phase1_c[idx] = Fraction(-1)

            forbidden: set = set()

            terminated, B_inv = yield from self._run_phase(
                B_inv, phase1_c, phase=1, forbidden=forbidden,
                iteration_counter=iteration_counter,
            )
            if terminated == 'infeasible':
                return
            if terminated == 'unbounded':
                return

            x_B = self._mat_vec_mult(B_inv, self.b)
            w_min = sum(
                phase1_c[self.N[i]] * x_B[i] for i in range(self.n_constraints)
            )
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
                    row_inverted=list(self._row_inverted),
                )
                return

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
        """Внутренний цикл симплекс-метода для одной фазы."""
        m = self.n_constraints

        while True:
            iteration_counter[0] += 1

            x_B = self._mat_vec_mult(B_inv, self.b)
            c_B = [c_vec[idx] for idx in self.N]
            u_0 = self._vec_mat_mult(c_B, B_inv)

            # --- проверка оптимальности: правило ПЕРВОГО индекса (Бленд) ---
            j_0: Optional[int] = None
            diffs: List[tuple] = []
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
                    break

            x_full = self._build_full_x(x_B)

            # Вычисляем u_0 для исходной задачи (с учётом инверсий строк)
            u_0_original = self._compute_u0_original(u_0)

            if j_0 is None:
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
                    var_map=list(self._var_map),
                    u_0_original=u_0_original,
                    row_inverted=list(self._row_inverted),
                )
                return ('optimal', B_inv)

            # --- направляющий вектор и выбор переменной на вывод ---
            A_j0 = [self.A[i][j_0] for i in range(m)]
            z_0 = self._mat_vec_mult(B_inv, A_j0)

            if all(z <= 0 for z in z_0):
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
                    u_0_original=u_0_original,
                    row_inverted=list(self._row_inverted),
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
                u_0_original=u_0_original,
                row_inverted=list(self._row_inverted),
            )

            # --- pivot ---
            self.N[s_0] = j_0
            B_inv = self._pivot(B_inv, z_0, s_0)

    # ---------------------------------------------------------------- helpers
    def _compute_u0_original(self, u_0: List[Fraction]) -> List[Fraction]:
        """Возвращает u_0 для исходной (не приведённой) задачи.

        При инверсии строки i (b_i < 0 → умножение на -1) знак u_i меняется.
        Для исходной задачи нужно вернуть -u_i для инвертированных строк.
        Также учитываем направление оптимизации: при min исходная задача
        имеет двойственные переменные с противоположным знаком.
        """
        # u_0 вычислен для задачи max (внутренняя). Для min исходная — знак меняется.
        sign = Fraction(1) if self.is_max else Fraction(-1)
        result = []
        for i, u in enumerate(u_0):
            # Если строка была инвертирована — знак u_i меняется обратно
            row_sign = Fraction(-1) if self._row_inverted[i] else Fraction(1)
            result.append(sign * row_sign * u)
        return result

    def compute_final_answer(self, last_step) -> Fraction:
        """Вычисляет значение исходной целевой функции f* = c^T x*.

        Учитывает:
        1. Вклад базисных переменных (через внутренние коэффициенты c).
        2. Константный сдвиг от нижних границ (lb != 0): c_j * lb_j.
        3. Фиксированные переменные (lb == ub): c_j * lb_j (они убраны из задачи).
        4. Направление оптимизации (min → инвертируем знак).
        """
        # Вклад базисных переменных (внутренние коэффициенты уже учитывают сдвиги x' = x - lb)
        c_B = [self.c[idx] for idx in last_step.N]
        obj_val = sum(
            (c_B[i] * last_step.x_B[i] for i in range(len(last_step.N))),
            Fraction(0)
        )

        # Добавляем константные вклады от редукций переменных
        # _var_map содержит записи для всех исходных переменных
        ext_idx = 0
        for entry in self._var_map:
            kind = entry[0]
            orig_j = entry[1]
            shift = entry[2]

            if kind == 'fixed':
                # Переменная была удалена из задачи: x_j = shift (= lb = ub)
                # Её вклад: c_j * shift (используем исходный c, до инверсии для min)
                orig_c_j = self.problem.c[orig_j]
                internal_c_j = orig_c_j if self.is_max else -orig_c_j
                obj_val += internal_c_j * shift
                # fixed не занимает столбец в расширенной задаче
            elif kind == 'direct' and shift != Fraction(0):
                # x_j' = x_j - shift => c_j * x_j = c_j * x_j' + c_j * shift
                # Внутренний obj_val уже содержит c_j * x_j', добавляем c_j * shift
                # Используем внутренний коэффициент (уже с учётом is_max)
                if ext_idx < len(self.c):
                    obj_val += self.c[ext_idx] * shift
                ext_idx += 1
            elif kind == 'neg_shift':
                # x_j' = shift - x_j => x_j = shift - x_j'
                # c_j * x_j = c_j * shift - c_j * x_j'
                # Внутренний c_j уже инвертирован: self.c[ext_idx] = -orig_c_j (или +orig_c_j для min)
                # Нужно добавить c_j * shift (исходный c_j)
                orig_c_j = self.problem.c[orig_j] if orig_j < self.n_orig_vars else Fraction(0)
                internal_c_j = orig_c_j if self.is_max else -orig_c_j
                obj_val += internal_c_j * shift
                ext_idx += 1
            else:
                if kind != 'fixed':
                    ext_idx += 1

        return obj_val if self.is_max else -obj_val

    def recover_original_x(self, x_full: List[Fraction]) -> List[Fraction]:
        """Восстанавливает значения исходных переменных из расширенного вектора x.

        Применяет обратные преобразования карты _var_map.
        Возвращает вектор длины n_orig_vars.
        """
        result = [Fraction(0)] * self.n_orig_vars
        # x_full содержит значения переменных после всех редукций.
        # Карта _var_map описывает, как каждая исходная переменная была преобразована.
        split_minus_seen: dict = {}  # orig_idx -> значение x_j^-

        # Первый проход: собираем split- части
        ext_idx = 0
        for entry in self._var_map:
            kind = entry[0]
            orig_j = entry[1]
            shift = entry[2]
            if kind == 'split-':
                if ext_idx < len(x_full):
                    split_minus_seen[orig_j] = x_full[ext_idx]
                ext_idx += 1
            elif kind == 'fixed':
                pass  # фиксированная переменная не занимает столбец
            else:
                ext_idx += 1

        # Второй проход: восстанавливаем исходные переменные
        ext_idx = 0
        for entry in self._var_map:
            kind = entry[0]
            orig_j = entry[1]
            shift = entry[2]

            if kind == 'fixed':
                result[orig_j] = shift
                continue

            val = x_full[ext_idx] if ext_idx < len(x_full) else Fraction(0)

            if kind == 'direct':
                result[orig_j] = val + shift
            elif kind == 'neg':
                result[orig_j] = -val
            elif kind == 'neg_shift':
                # x_j' = shift - x_j => x_j = shift - x_j'
                result[orig_j] = shift - val
            elif kind == 'split+':
                x_minus = split_minus_seen.get(orig_j, Fraction(0))
                result[orig_j] = val - x_minus
            elif kind == 'split-':
                pass  # уже учтено в split+

            ext_idx += 1

        return result

    def _purge_artificials_from_basis(
        self, B_inv: List[List[Fraction]], x_B: List[Fraction]
    ) -> List[List[Fraction]]:
        """Пытается вывести из базиса искусственные переменные с нулевым значением."""
        m = self.n_constraints
        artificial_set = set(self.artificial)
        i = 0
        while i < m:
            if self.N[i] in artificial_set and x_B[i] == 0:
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
