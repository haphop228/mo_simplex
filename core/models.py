from dataclasses import dataclass, field
from typing import List, Optional
from fractions import Fraction

@dataclass
class LinearProblem:
    c: List[Fraction]
    A: List[List[Fraction]]
    b: List[Fraction]
    signs: List[str]  # '<=', '>=', '='
    is_max: bool = True

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
