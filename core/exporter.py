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
        
        md.append("## Каноническая форма")
        md.append("$$")
        md.append("\\begin{align*}")
        n_orig = len(problem.c)
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
            
            # Canonical always adds x_{n_orig + i + 1}
            row_str += f" + x_{{{n_orig + i + 1}}}"
            md.append(f"{row_str} &= {problem.b[i]} \\\\")
            
        md.append("x &\\geq 0")
        md.append("\\end{align*}")
        md.append("$$\n")

        md.append("## Двойственная задача")
        md.append("$$")
        md.append("\\begin{align*}")
        dual_obj = []
        for i, b_val in enumerate(problem.b):
            if b_val != 0:
                sign = "+" if b_val > 0 and dual_obj else ("" if b_val > 0 else "-")
                b_abs = abs(b_val)
                coeff = str(b_abs) if b_abs != 1 else ""
                dual_obj.append(f"{sign} {coeff}u_{{{i+1}}}")
        dual_obj_str = " ".join(dual_obj) if dual_obj else "0"
        if dual_obj_str.startswith("+ "):
            dual_obj_str = dual_obj_str[2:]
        dual_target = "\\min" if problem.is_max else "\\max"
        md.append(f"{dual_obj_str} &\\to {dual_target} \\\\")
        
        for j in range(len(problem.c)):
            terms = []
            for i in range(len(problem.A)):
                val = problem.A[i][j]
                if val != 0:
                    sign = "+" if val > 0 and terms else ("" if val > 0 else "-")
                    v_abs = abs(val)
                    coeff = str(v_abs) if v_abs != 1 else ""
                    terms.append(f"{sign} {coeff}u_{{{i+1}}}")
            row_str = " ".join(terms) if terms else "0"
            if row_str.startswith("+ "):
                row_str = row_str[2:]
            # If max, dual is >= c. If min, dual is <= c
            sign_str = "\\geq" if problem.is_max else "\\leq"
            md.append(f"{row_str} &{sign_str} {problem.c[j]} \\\\")
            
        md.append("u &\\geq 0")
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

    @staticmethod
    def generate_html(problem: LinearProblem, steps: List[SimplexStep], final_answer: Fraction) -> str:
        html = []
        html.append("<div class='mb-8 pb-4 border-b border-gray-200'>")
        html.append("<h3 class='text-xl font-bold text-gray-800 mb-4'>Прямая задача</h3>")
        html.append("<div class='overflow-x-auto bg-gray-50 p-4 rounded-lg'>")
        html.append("$$")
        html.append("\\begin{align*}")
        
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
        html.append(f"{obj_str} &\\to {target} \\\\")
        
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
            html.append(f"{row_str} &{sign_str} {problem.b[i]} \\\\")
            
        html.append("x &\\geq 0")
        html.append("\\end{align*}")
        html.append("$$")
        html.append("</div>")
        
        # Canonical Form
        html.append("<h3 class='text-xl font-bold text-gray-800 mb-4 mt-6'>Каноническая форма</h3>")
        html.append("<div class='overflow-x-auto bg-gray-50 p-4 rounded-lg'>")
        html.append("$$")
        html.append("\\begin{align*}")
        n_orig = len(problem.c)
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
            row_str += f" + x_{{{n_orig + i + 1}}}"
            html.append(f"{row_str} &= {problem.b[i]} \\\\")
            
        html.append("x &\\geq 0")
        html.append("\\end{align*}")
        html.append("$$")
        html.append("</div>")

        # Dual Form
        html.append("<h3 class='text-xl font-bold text-gray-800 mb-4 mt-6'>Двойственная задача</h3>")
        html.append("<div class='overflow-x-auto bg-gray-50 p-4 rounded-lg'>")
        html.append("$$")
        html.append("\\begin{align*}")
        dual_obj = []
        for i, b_val in enumerate(problem.b):
            if b_val != 0:
                sign = "+" if b_val > 0 and dual_obj else ("" if b_val > 0 else "-")
                b_abs = abs(b_val)
                coeff = str(b_abs) if b_abs != 1 else ""
                dual_obj.append(f"{sign} {coeff}u_{{{i+1}}}")
        dual_obj_str = " ".join(dual_obj) if dual_obj else "0"
        if dual_obj_str.startswith("+ "):
            dual_obj_str = dual_obj_str[2:]
        dual_target = "\\min" if problem.is_max else "\\max"
        html.append(f"{dual_obj_str} &\\to {dual_target} \\\\")
        
        for j in range(len(problem.c)):
            terms = []
            for i in range(len(problem.A)):
                val = problem.A[i][j]
                if val != 0:
                    sign = "+" if val > 0 and terms else ("" if val > 0 else "-")
                    v_abs = abs(val)
                    coeff = str(v_abs) if v_abs != 1 else ""
                    terms.append(f"{sign} {coeff}u_{{{i+1}}}")
            row_str = " ".join(terms) if terms else "0"
            if row_str.startswith("+ "):
                row_str = row_str[2:]
            sign_str = "\\geq" if problem.is_max else "\\leq"
            html.append(f"{row_str} &{sign_str} {problem.c[j]} \\\\")
            
        html.append("u &\\geq 0")
        html.append("\\end{align*}")
        html.append("$$")
        html.append("</div>")

        html.append("</div>")
        
        for step in steps:
            html.append("<div class='step-container bg-white p-6 rounded-lg border border-gray-200 shadow-sm mb-6'>")
            html.append(f"<h4 class='text-lg font-bold text-indigo-700 mb-4 border-b pb-2'>Шаг {step.iteration}</h4>")
            
            html.append("<div class='grid grid-cols-1 md:grid-cols-2 gap-6'>")
            
            html.append("<div>")
            html.append(f"<p class='mb-2'><strong>Базис N:</strong> $({', '.join(str(n+1) for n in step.N)})$</p>")
            html.append(f"<p class='mb-2'><strong>Текущий план $x_B$:</strong></p><div class='overflow-x-auto'>$$ {Exporter.vec_to_latex(step.x_B)} $$</div>")
            html.append("</div>")
            
            html.append("<div>")
            html.append(f"<p class='mb-2'><strong>Обратная матрица $B^{{-1}}$:</strong></p><div class='overflow-x-auto'>$$ {Exporter.mat_to_latex(step.B_inv)} $$</div>")
            html.append(f"<p class='mb-2'><strong>Вектор оценок $u_0$:</strong></p><div class='overflow-x-auto'>$$ {Exporter.vec_to_latex(step.u_0, is_column=False)} $$</div>")
            html.append("</div>")
            
            html.append("</div>")
            
            html.append("<div class='mt-6 pt-4 border-t border-gray-100 bg-gray-50 p-4 rounded'>")
            if step.is_optimal:
                html.append("<p class='text-green-700 font-bold'>&check; План оптимален. Все двойственные ограничения выполнены.</p>")
                if final_answer is not None:
                    html.append(f"<p class='text-xl mt-2'><strong>Ответ:</strong> ${Exporter.frac_to_latex(final_answer)}$</p>")
            elif step.is_unbounded:
                html.append("<p class='text-red-600 font-bold'>&cross; Целевая функция не ограничена сверху. Решения нет.</p>")
            else:
                html.append(f"<p class='text-gray-700 font-medium'>План не оптимален. Вводим в базис $x_{{{step.j_0+1}}}$.</p>")
                html.append("<div class='mt-2 grid grid-cols-1 md:grid-cols-2 gap-4'>")
                html.append(f"<div><strong>Направляющий вектор $z_0$:</strong><br>$$ {Exporter.vec_to_latex(step.z_0)} $$</div>")
                html.append(f"<div><strong>Шаг $t_0$:</strong> ${Exporter.frac_to_latex(step.t_0)}$<br><br>")
                html.append(f"<strong>Выводим из базиса:</strong> $x_{{{step.s_0+1}}}$.</div>")
                html.append("</div>")
            html.append("</div>")
            html.append("</div>")
            
        return "\n".join(html)
