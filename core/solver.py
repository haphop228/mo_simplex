from typing import List, Generator
from fractions import Fraction
from core.models import LinearProblem, SimplexStep

class SimplexSolver:
    def __init__(self, problem: LinearProblem):
        self.problem = problem
        self.n_orig_vars = len(problem.c)
        self.n_constraints = len(problem.A)
        
        self.is_max = problem.is_max
        self.c = [c if self.is_max else -c for c in problem.c]
        
        self.A = [[c for c in row] for row in problem.A]
        self.b = [c for c in problem.b]
        self.signs = [s for s in problem.signs]
        
        self.n_vars = self.n_orig_vars
        self.N = []

        # Применяем сдвиг переменных по нижним границам: x_i' = x_i - lb_i
        # Это позволяет свести задачу к стандартной форме x' >= 0
        if problem.var_bounds:
            for i, (lb, ub) in enumerate(problem.var_bounds):
                if lb is not None and lb != Fraction(0):
                    # b_j -= A[j][i] * lb для каждого ограничения j
                    for j in range(self.n_constraints):
                        self.b[j] -= self.A[j][i] * lb
                    # Целевая функция: c_i * x_i = c_i * (x_i' + lb) => константа c_i*lb добавляется к ответу
                    # (учитывается в main.py при вычислении final_answer)
        
        self._to_canonical()

    def _to_canonical(self):
        for i in range(self.n_constraints):
            if self.b[i] < Fraction(0):
                self.b[i] *= -1
                for j in range(self.n_vars):
                    self.A[i][j] *= -1
                if self.signs[i] == '<=':
                    self.signs[i] = '>='
                elif self.signs[i] == '>=':
                    self.signs[i] = '<='

        for i in range(self.n_constraints):
            if self.signs[i] == '<=':
                for r in range(self.n_constraints):
                    self.A[r].append(Fraction(1) if r == i else Fraction(0))
                self.c.append(Fraction(0))
                self.N.append(self.n_vars)
                self.n_vars += 1
            elif self.signs[i] == '>=':
                for r in range(self.n_constraints):
                    self.A[r].append(Fraction(-1) if r == i else Fraction(0))
                self.c.append(Fraction(0))
                self.n_vars += 1
                
        if len(self.N) < self.n_constraints:
            raise ValueError("Двухфазный симплекс-метод пока не реализован. Используйте ограничения типа <=")

    def solve(self) -> Generator[SimplexStep, None, None]:
        B_inv = [[Fraction(1) if i == j else Fraction(0) for j in range(self.n_constraints)] for i in range(self.n_constraints)]
        
        iteration = 0
        while True:
            iteration += 1
            x_B = self._mat_vec_mult(B_inv, self.b)
            c_B = [self.c[idx] for idx in self.N]
            u_0 = self._vec_mat_mult(c_B, B_inv)
            
            is_optimal = True
            j_0 = -1
            min_diff = Fraction(0)
            diffs = []
            
            for j in range(self.n_vars):
                if j in self.N:
                    diffs.append(Fraction(0))
                    continue
                A_j = [self.A[i][j] for i in range(self.n_constraints)]
                u_A = sum(u_0[i] * A_j[i] for i in range(self.n_constraints))
                diff = u_A - self.c[j]
                diffs.append(diff)
                
                if diff < Fraction(0):
                    is_optimal = False
                    if j_0 == -1 or diff < min_diff:
                        j_0 = j
                        min_diff = diff
            
            if is_optimal:
                yield SimplexStep(
                    iteration=iteration, N=list(self.N), B_inv=[r[:] for r in B_inv], x_B=x_B, u_0=u_0,
                    is_optimal=True, description="План оптимален. Все двойственные ограничения выполнены.",
                    c_B=c_B, diffs=diffs
                )
                return

            A_j0 = [self.A[i][j_0] for i in range(self.n_constraints)]
            z_0 = self._mat_vec_mult(B_inv, A_j0)
            
            if all(z <= Fraction(0) for z in z_0):
                yield SimplexStep(
                    iteration=iteration, N=list(self.N), B_inv=[r[:] for r in B_inv], x_B=x_B, u_0=u_0,
                    is_optimal=False, is_unbounded=True, j_0=j_0, z_0=z_0,
                    description="Целевая функция не ограничена сверху. Решения нет.",
                    c_B=c_B, diffs=diffs
                )
                return
            
            t_0 = None
            s_0 = -1
            ratios = []
            for i in range(self.n_constraints):
                if z_0[i] > Fraction(0):
                    ratio = x_B[i] / z_0[i]
                    ratios.append(ratio)
                    if t_0 is None or ratio < t_0:
                        t_0 = ratio
                        s_0 = i
                else:
                    ratios.append(None)
                        
            yield SimplexStep(
                iteration=iteration, N=list(self.N), B_inv=[r[:] for r in B_inv], x_B=x_B, u_0=u_0,
                is_optimal=False, j_0=j_0, z_0=z_0, t_0=t_0, s_0=self.N[s_0],
                description=f"План не оптимален. Вводим x_{{{j_0+1}}} в базис, выводим x_{{{self.N[s_0]+1}}}.",
                c_B=c_B, diffs=diffs, ratios=ratios
            )
            
            self.N[s_0] = j_0
            pivot = z_0[s_0]
            
            for j in range(self.n_constraints):
                B_inv[s_0][j] /= pivot
                
            for i in range(self.n_constraints):
                if i != s_0:
                    factor = z_0[i]
                    for j in range(self.n_constraints):
                        B_inv[i][j] -= factor * B_inv[s_0][j]

    def _mat_vec_mult(self, M: List[List[Fraction]], v: List[Fraction]) -> List[Fraction]:
        return [sum(M[i][j] * v[j] for j in range(len(v))) for i in range(len(M))]

    def _vec_mat_mult(self, v: List[Fraction], M: List[List[Fraction]]) -> List[Fraction]:
        cols = len(M[0])
        res = [Fraction(0)] * cols
        for j in range(cols):
            res[j] = sum(v[i] * M[i][j] for i in range(len(v)))
        return res
