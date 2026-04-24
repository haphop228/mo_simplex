import pytest
from fractions import Fraction
from core.models import LinearProblem, SimplexStep
from core.exporter import Exporter

@pytest.fixture
def sample_problem():
    c = [Fraction(12), Fraction(3)]
    A = [[Fraction(4), Fraction(1)]]
    b = [Fraction(16)]
    signs = ['<=']
    return LinearProblem(c, A, b, signs, is_max=True)

@pytest.fixture
def sample_steps():
    step = SimplexStep(
        iteration=1,
        N=[2],
        B_inv=[[Fraction(1)]],
        x_B=[Fraction(16)],
        u_0=[Fraction(0)],
        is_optimal=False,
        j_0=0,
        z_0=[Fraction(4)],
        t_0=Fraction(4),
        s_0=2
    )
    opt_step = SimplexStep(
        iteration=2,
        N=[0],
        B_inv=[[Fraction(1, 4)]],
        x_B=[Fraction(4)],
        u_0=[Fraction(3)],
        is_optimal=True
    )
    return [step, opt_step]

def test_frac_to_latex():
    assert Exporter.frac_to_latex(Fraction(1, 4)) == "\\frac{1}{4}"
    assert Exporter.frac_to_latex(Fraction(4, 1)) == "4"
    assert Exporter.frac_to_latex(Fraction(-3, 2)) == "-\\frac{3}{2}"

def test_generate_markdown(sample_problem, sample_steps):
    md = Exporter.generate_markdown(sample_problem, sample_steps, Fraction(48))
    
    # Check headers
    assert "# Решение задачи модифицированным симплекс-методом" in md
    
    # Check math blocks
    assert "12x_{1} + 3x_{2} &\\to \\max \\\\" in md
    assert "4x_{1} + 1x_{2} &\\leq 16 \\\\" in md
    
    # Check steps
    assert "### Шаг 1" in md
    assert "### Шаг 2" in md
    
    # Check optimal and answer
    assert "План оптимален" in md
    assert "**Ответ:** $48$" in md

def test_generate_html(sample_problem, sample_steps):
    html = Exporter.generate_html(sample_problem, sample_steps, Fraction(48))
    
    # Check headers
    assert "<h3 class='text-xl font-bold text-gray-800 mb-4'>Прямая задача</h3>" in html
    
    # Check math
    assert "12x_{1} + 3x_{2} &\\to \\max \\\\" in html
    
    # Check steps
    assert "Шаг 1</h4>" in html
    assert "Шаг 2</h4>" in html
    assert "План оптимален" in html
    assert "<strong>Ответ:</strong> $48$" in html
