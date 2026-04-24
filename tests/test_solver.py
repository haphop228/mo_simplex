import pytest
from fractions import Fraction
from core.models import LinearProblem, SimplexStep
from core.solver import SimplexSolver

def test_solver_example_1_max():
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
    assert len(steps) == 2 
    final_step = steps[-1]
    assert final_step.is_optimal == True
    
    c_B = [solver.c[idx] for idx in final_step.N]
    obj_val = sum(c_B[i] * final_step.x_B[i] for i in range(len(final_step.N)))
    assert obj_val == Fraction(48)

def test_solver_example_2_max():
    # 5x1 + 4x2 -> max
    # x1 + x2 <= 5
    # 10x1 + 6x2 <= 45
    # x1 <= 3
    c = [Fraction(5), Fraction(4)]
    A = [
        [Fraction(1), Fraction(1)],
        [Fraction(10), Fraction(6)],
        [Fraction(1), Fraction(0)]
    ]
    b = [Fraction(5), Fraction(45), Fraction(3)]
    signs = ['<=', '<=', '<=']
    
    problem = LinearProblem(c=c, A=A, b=b, signs=signs, is_max=True)
    solver = SimplexSolver(problem)
    
    steps = list(solver.solve())
    
    final_step = steps[-1]
    assert final_step.is_optimal == True
    
    c_B = [solver.c[idx] for idx in final_step.N]
    obj_val = sum(c_B[i] * final_step.x_B[i] for i in range(len(final_step.N)))
    assert obj_val == Fraction(23)

def test_solver_unbounded():
    # 2x1 + x2 -> max
    # -x1 + x2 <= 2
    # x1 - x2 <= 1
    c = [Fraction(2), Fraction(1)]
    A = [
        [Fraction(-1), Fraction(1)],
        [Fraction(1), Fraction(-1)]
    ]
    b = [Fraction(2), Fraction(1)]
    signs = ['<=', '<=']
    
    problem = LinearProblem(c=c, A=A, b=b, signs=signs, is_max=True)
    solver = SimplexSolver(problem)
    steps = list(solver.solve())
    
    # Should end up being unbounded
    final_step = steps[-1]
    assert final_step.is_optimal == False
    assert final_step.is_unbounded == True

def test_solver_minimization():
    # -12x1 - 3x2 -> min
    # 4x1 + x2 <= 16
    # 2x1 + 2x2 <= 22
    # 6x1 + 3x2 <= 36
    # Minimum should be -48
    c = [Fraction(-12), Fraction(-3)]
    A = [
        [Fraction(4), Fraction(1)],
        [Fraction(2), Fraction(2)],
        [Fraction(6), Fraction(3)]
    ]
    b = [Fraction(16), Fraction(22), Fraction(36)]
    signs = ['<=', '<=', '<=']
    
    problem = LinearProblem(c=c, A=A, b=b, signs=signs, is_max=False)
    solver = SimplexSolver(problem)
    
    steps = list(solver.solve())
    final_step = steps[-1]
    assert final_step.is_optimal == True
    
    c_B = [solver.c[idx] for idx in final_step.N]
    obj_val = sum(c_B[i] * final_step.x_B[i] for i in range(len(final_step.N)))
    # For min, internal solver maximizes -c. 
    # internal objective = 48. Thus, original objective is -48.
    assert obj_val == Fraction(48)
