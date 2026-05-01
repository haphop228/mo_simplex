from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from fractions import Fraction

# Тип границы переменной: None означает отсутствие ограничения (±∞)
Bound = Optional[Fraction]

@dataclass
class LinearProblem:
    c: List[Fraction]
    A: List[List[Fraction]]
    b: List[Fraction]
    signs: List[str]  # '<=', '>=', '='
    is_max: bool = True
    # Границы переменных: lower_bounds[j] = l_j, upper_bounds[j] = u_j.
    # None означает отсутствие ограничения (-∞ / +∞).
    # По умолчанию все переменные >= 0 (lower=0, upper=None).
    lower_bounds: Optional[List[Bound]] = None
    upper_bounds: Optional[List[Bound]] = None

@dataclass
class SimplexStep:
    iteration: int
    N: List[int]            # 0-indexed indices of basic variables (in extended canonical space)
    B_inv: List[List[Fraction]]  # inverse basis matrix (m x m)
    x_B: List[Fraction]     # values of basic variables (length m)
    u_0: List[Fraction]     # dual estimates of current phase
    x_full: List[Fraction] = field(default_factory=list)  # full plan vector x (length n_vars)
    phase: int = 2          # 1 = вспомогательная задача, 2 = основная
    is_optimal: bool = False
    is_unbounded: bool = False
    is_infeasible: bool = False  # фаза I завершилась с w_min > 0
    j_0: Optional[int] = None
    z_0: Optional[List[Fraction]] = None  # length m (basic decomposition)
    t_0: Optional[Fraction] = None
    s_0: Optional[int] = None             # extended index выводимой переменной
    description: str = ""
    c_B: Optional[List[Fraction]] = None
    diffs: Optional[List[tuple]] = None   # список (j, Δ_j) — посчитанные до первого Δ<0 включительно
    ratios: Optional[List[Optional[Fraction]]] = None
    artificial_indices: Optional[List[int]] = None  # индексы искусственных переменных в расширенной задаче
    # Карта восстановления исходных переменных из расширенных (для финального шага)
    var_map: Optional[List[Tuple[str, int, Fraction]]] = None
    # u_0 для исходной (не приведённой) задачи — с учётом инверсий строк
    u_0_original: Optional[List[Fraction]] = None
    # Знаки строк после приведения b>=0 (True = строка была инвертирована)
    row_inverted: Optional[List[bool]] = None
