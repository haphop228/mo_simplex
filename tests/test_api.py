import pytest
from fractions import Fraction
from main import Api

def test_api_solve_success():
    api = Api()
    
    # JS теперь передаёт числа как строки
    data = {
        'c': ['12', '3'],
        'A': [['4', '1'], ['2', '2'], ['6', '3']],
        'b': ['16', '22', '36'],
        'signs': ['<=', '<=', '<='],
        'is_max': True
    }
    
    result = api.solve(data)
    
    # Ensure it returns an HTML string and not an error dictionary
    assert isinstance(result, str)
    assert "<div class='step-container" in result
    
    # Internal state is updated
    assert api.last_problem is not None
    assert api.last_steps is not None
    assert api.last_final_answer is not None

def test_api_solve_error():
    api = Api()
    
    # Invalid data (missing parameters or bad types)
    data = {
        'c': ['invalid_string', '3'],
        'A': [['4', '1']],
        'b': ['16'],
        'signs': ['<='],
        'is_max': True
    }
    
    result = api.solve(data)
    
    # Ensure it returns an error dict
    assert isinstance(result, dict)
    assert "error" in result

def test_api_solve_fractional_coefficient():
    """Кейс с дробным коэффициентом — строка '0.333333' даёт точный Fraction.

    Задача: min 0.333333·x₁ + x₂,  x₁ + x₂ >= 3,  x₁,x₂ >= 0
    Оптимум: x* = (3, 0), f* = 3 × 333333/1000000 = 999999/1000000.

    Ключевая проверка: Fraction('0.333333') = 333333/1000000 (точно),
    а не иррациональный float, т.е. арифметика остаётся точной.
    """
    api = Api()

    data = {
        'c': ['0.333333', '1'],
        'A': [['1', '1']],
        'b': ['3'],
        'signs': ['>='],
        'is_max': False,
    }

    result = api.solve(data)

    assert isinstance(result, str), f"Ожидался HTML, получено: {result}"
    assert api.last_final_answer is not None

    # Fraction('0.333333') = 333333/1000000, x* = (3, 0)
    # f* = 3 * 333333/1000000 = 999999/1000000
    assert api.last_final_answer == Fraction(999999, 1000000)

def test_api_save_markdown_no_data():
    api = Api()
    # Trying to save without solving first
    result = api.save_markdown()
    
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] == "Нет решенной задачи"
