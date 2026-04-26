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
    assert "4x_{1} + x_{2} &\\leq 16 \\\\" in md
    
    # Check headers
    assert "## Каноническая форма" in md
    assert "## Двойственная задача" in md
    
    # Check optimal and answer
    assert "План оптимален" in md
    assert "x^*" in md
    assert "f(x^*)" in md

def test_generate_markdown_hidden_steps(sample_problem, sample_steps):
    md = Exporter.generate_markdown(sample_problem, sample_steps, Fraction(48), hidden_steps=[1])
    assert "### Шаг 1" not in md
    assert "### Шаг 2" in md

def test_generate_html_detailed(sample_problem, sample_steps):
    step1 = sample_steps[0]
    step1.c_B = [Fraction(0)]
    step1.diffs = [Fraction(-1)]
    step1.z_0 = [Fraction(1)]
    step1.ratios = [Fraction(4)]
    
    html = Exporter.generate_html(sample_problem, sample_steps, Fraction(48), detailed=True)
    
    # Check detailed calculations
    assert "u_0 =  \\begin{bmatrix} 0 \\end{bmatrix}  B^{-1}" in html
    assert "\\Delta_" in html
    assert "z_0 = B^{-1} A_{1}" in html
    assert "\\min" in html

def test_generate_html(sample_problem, sample_steps):
    html = Exporter.generate_html(sample_problem, sample_steps, Fraction(48))
    
    # Check headers
    assert "<h3 class='text-xl font-bold text-gray-800 mb-4'>Прямая задача</h3>" in html
    
    # Check math
    assert "12x_{1} + 3x_{2} &\\to \\max \\\\" in html
    
    # Check headers
    assert "<h3 class='text-xl font-bold text-gray-800 mb-4 mt-6'>Каноническая форма</h3>" in html
    assert "<h3 class='text-xl font-bold text-gray-800 mb-4 mt-6'>Двойственная задача</h3>" in html
    assert "План оптимален" in html
    assert "x^*" in html
    assert "f(x^*)" in html
