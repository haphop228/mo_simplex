from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from fractions import Fraction

@dataclass
class LinearProblem:
    c: List[Fraction]
    A: List[List[Fraction]]
    b: List[Fraction]
    signs: List[str]  # '<=', '>=', '='
    is_max: bool = True
    # var_bounds[i] = (lb, ub): нижняя и верхняя граница для x_{i+1}.
    # lb=None означает -inf, ub=None означает +inf.
    # По умолчанию None — все переменные >= 0 (стандартное условие).
    var_bounds: Optional[List[Tuple[Optional[Fraction], Optional[Fraction]]]] = None

@dataclass
class SimplexStep:
    iteration: int
    N: List[int]  # 0-indexed indices of basic variables
    B_inv: List[List[Fraction]]
    x_B: List[Fraction]
    u_0: List[Fraction]
    is_optimal: bool
    is_unbounded: bool = False
    j_0: Optional[int] = None
    z_0: Optional[List[Fraction]] = None
    t_0: Optional[Fraction] = None
    s_0: Optional[int] = None
    description: str = ""
    c_B: Optional[List[Fraction]] = None
    diffs: Optional[List[Fraction]] = None
    ratios: Optional[List[Fraction]] = None
