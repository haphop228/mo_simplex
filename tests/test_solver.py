import pytest
from fractions import Fraction
from core.models import LinearProblem, SimplexStep
from core.solver import SimplexSolver

def test_solver_example_1():
    # 12x1 + 3x2 -> max
    # 4x1 + x2 <= 16
    # 2x1 + 2x2 <= 22
    # 6x1 + 3x2 <= 36
    c = [Fraction(12), Fraction(3)]
    A = [
        [Fraction(4), Fraction(1)],
        [Fraction(2), Fraction(2)],
        [Fraction(6), Fraction(3)]
    ]
    b = [Fraction(16), Fraction(22), Fraction(36)]
    signs = ['<=', '<=', '<=']
    
    problem = LinearProblem(c=c, A=A, b=b, signs=signs, is_max=True)
    solver = SimplexSolver(problem)
    
    steps = list(solver.solve())
    
    # Check steps count
    assert len(steps) == 3 # Initial state checked, iteration 1, iteration 2 (optimal)
    
    # Check optimal step
    final_step = steps[-1]
    assert final_step.is_optimal == True
    
    # Optimal basis x_1, x_4, x_5 => indices 0, 3, 4
    assert sorted(final_step.N) == [0, 3, 4]
    
    # Optimal answer is 48.
    # Check u_0 on optimal step
    assert final_step.u_0 == [Fraction(3), Fraction(0), Fraction(0)]
    
    # Check objective value c_B * x_B
    c_B = [solver.c[idx] for idx in final_step.N]
    obj_val = sum(c_B[i] * final_step.x_B[i] for i in range(len(final_step.N)))
    assert obj_val == Fraction(48)
