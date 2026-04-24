from typing import List
from fractions import Fraction
from core.models import LinearProblem, SimplexStep

class Exporter:
    @staticmethod
    def frac_to_latex(f: Fraction) -> str:
        if f.denominator == 1:
            return str(f.numerator)
        if f.numerator < 0:
            return f"-\\frac{{{-f.numerator}}}{{{f.denominator}}}"
        return f"\\frac{{{f.numerator}}}{{{f.denominator}}}"

    @staticmethod
    def vec_to_latex(v: List[Fraction], is_column: bool = True) -> str:
        lines = " \\\\ ".join(Exporter.frac_to_latex(x) for x in v)
        if not is_column:
            lines = " & ".join(Exporter.frac_to_latex(x) for x in v)
            return f"\\begin{{bmatrix}} {lines} \\end{{bmatrix}}"
        return f"\\begin{{bmatrix}} {lines} \\end{{bmatrix}}"

    @staticmethod
    def mat_to_latex(M: List[List[Fraction]]) -> str:
        rows = []
        for row in M:
            rows.append(" & ".join(Exporter.frac_to_latex(x) for x in row))
        body = " \\\\ \n".join(rows)
        return f"\\begin{{bmatrix}}\n{body}\n\\end{{bmatrix}}"

    @staticmethod
    def generate_markdown(problem: LinearProblem, steps: List[SimplexStep], final_answer: Fraction) -> str:
        md = []
        md.append("# Решение задачи модифицированным симплекс-методом\n")
        
        md.append("## Прямая задача")
        md.append("$$")
        md.append("\\begin{align*}")
        
        obj_terms = []
        for i, c in enumerate(problem.c):
            if c != 0:
                sign = "+" if c > 0 and obj_terms else ("" if c > 0 else "-")
                c_abs = abs(c)
                coeff = str(c_abs) if c_abs != 1 else ""
                obj_terms.append(f"{sign} {coeff}x_{{{i+1}}}")
        if not obj_terms:
            obj_terms.append("0")
        obj_str = " ".join(obj_terms).strip()
        if obj_str.startswith("+ "):
            obj_str = obj_str[2:]
        target = "\\max" if problem.is_max else "\\min"
        md.append(f"{obj_str} &\\to {target} \\\\")
        
        for i, row in enumerate(problem.A):
            terms = []
            for j, val in enumerate(row):
                if val != 0:
                    sign = "+" if val > 0 and terms else ("" if val > 0 else "-")
                    v_abs = abs(val)
                    coeff = str(v_abs) if v_abs != 1 else ""
                    terms.append(f"{sign} {coeff}x_{{{j+1}}}")
            row_str = " ".join(terms) if terms else "0"
            if row_str.startswith("+ "):
                row_str = row_str[2:]
            if problem.signs[i] == '<=':
                sign_str = "\\leq"
            elif problem.signs[i] == '>=':
                sign_str = "\\geq"
            else:
                sign_str = "="
            md.append(f"{row_str} &{sign_str} {problem.b[i]} \\\\")
            
        md.append("x &\\geq 0")
        md.append("\\end{align*}")
        md.append("$$\n")
        
        md.append("---\n")
        
        for step in steps:
            md.append(f"### Шаг {step.iteration}")
            
            md.append(f"**Базис N:** $({', '.join(str(n+1) for n in step.N)})$  ")
            md.append(f"**Текущий план $x_B$:**  \n$$ {Exporter.vec_to_latex(step.x_B)} $$  ")
            md.append(f"**Обратная матрица $B^{{-1}}$:**  \n$$ {Exporter.mat_to_latex(step.B_inv)} $$  ")
            md.append(f"**Вектор оценок $u_0$:**  \n$$ {Exporter.vec_to_latex(step.u_0, is_column=False)} $$  ")
            
            if step.is_optimal:
                md.append("\n-- **План оптимален.** Все двойственные ограничения выполнены.\n")
                if final_answer is not None:
                    md.append(f"**Ответ:** ${Exporter.frac_to_latex(final_answer)}$")
            elif step.is_unbounded:
                md.append("\n-- **Целевая функция не ограничена сверху. Решения нет.**\n")
            else:
                md.append(f"\n-- **План не оптимален.** Вводим в базис $x_{{{step.j_0+1}}}$.\n")
                md.append(f"**Направляющий вектор $z_0$:**  \n$$ {Exporter.vec_to_latex(step.z_0)} $$  ")
                md.append(f"**Шаг $t_0$:** ${Exporter.frac_to_latex(step.t_0)}$  ")
                md.append(f"Выводим из базиса $x_{{{step.s_0+1}}}$.\n")
                
            md.append("---\n")
            
        return "\n".join(md)
