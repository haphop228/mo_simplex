import webview
import os
import sys
from fractions import Fraction
from typing import Optional
from core.models import LinearProblem
from core.solver import SimplexSolver
from core.exporter import Exporter

class Api:
    def __init__(self):
        self.last_problem = None
        self.last_steps = None
        self.last_final_answer = None
        self.last_solver = None

    def solve(self, data):
        try:
            c = [Fraction(x).limit_denominator() for x in data['c']]
            A = [[Fraction(x).limit_denominator() for x in row] for row in data['A']]
            b = [Fraction(x).limit_denominator() for x in data['b']]
            signs = data['signs']
            is_max = data['is_max']

            # Границы переменных (опциональные)
            n = len(c)
            raw_lb = data.get('lower_bounds', None)
            raw_ub = data.get('upper_bounds', None)

            def parse_bound(val):
                """None / 'inf' / '-inf' → None, иначе Fraction."""
                if val is None:
                    return None
                s = str(val).strip().lower()
                if s in ('inf', '+inf', 'infinity', 'none', ''):
                    return None
                if s in ('-inf', '-infinity'):
                    return None
                return Fraction(val).limit_denominator()

            lower_bounds = None
            upper_bounds = None
            if raw_lb is not None:
                lower_bounds = [parse_bound(v) for v in raw_lb]
                # Если все нижние границы = 0 (дефолт) — не передаём
                if all(v == Fraction(0) for v in lower_bounds):
                    lower_bounds = None
            if raw_ub is not None:
                upper_bounds = [parse_bound(v) for v in raw_ub]
                # Если все верхние границы None (дефолт) — не передаём
                if all(v is None for v in upper_bounds):
                    upper_bounds = None

            canonical_mode = bool(data.get('canonical_mode', False))

            problem = LinearProblem(
                c, A, b, signs, is_max,
                lower_bounds=lower_bounds,
                upper_bounds=upper_bounds,
            )
            solver = SimplexSolver(problem, canonical_mode=canonical_mode)
            steps = list(solver.solve())

            final_answer: Optional[Fraction] = None
            x_original = None
            if steps and steps[-1].is_optimal and steps[-1].phase == 2:
                final_step = steps[-1]
                c_B = [solver.c[idx] for idx in final_step.N]
                obj_val = sum(
                    (c_B[i] * final_step.x_B[i] for i in range(len(final_step.N))),
                    Fraction(0)
                )
                final_answer = Fraction(obj_val) if problem.is_max else Fraction(-obj_val)
                # Восстанавливаем исходные переменные
                x_original = solver.recover_original_x(final_step.x_full)

            self.last_problem = problem
            self.last_steps = steps
            self.last_final_answer = final_answer
            self.last_solver = solver

            detailed = data.get('detailed', False)
            html_output = Exporter.generate_html(
                problem, steps, final_answer,
                detailed=detailed,
                x_original=x_original,
                n_orig_vars=solver.n_orig_vars,
            )
            return html_output

        except Exception as e:
            import traceback
            return {"error": str(e) + "\n" + traceback.format_exc()}

    def save_markdown(self, detailed=False, hidden_steps=None):
        if not self.last_problem or not self.last_steps:
            return {"error": "Нет решенной задачи"}

        try:
            solver = self.last_solver
            x_original = None
            if self.last_steps and self.last_steps[-1].is_optimal and self.last_steps[-1].phase == 2:
                x_original = solver.recover_original_x(self.last_steps[-1].x_full) if solver else None

            md_str = Exporter.generate_markdown(
                self.last_problem, self.last_steps, self.last_final_answer,
                detailed=detailed, hidden_steps=hidden_steps,
                x_original=x_original,
                n_orig_vars=solver.n_orig_vars if solver else None,
            )

            window = webview.windows[0]
            file_path = window.create_file_dialog(
                webview.SAVE_DIALOG,  # type: ignore[arg-type]
                directory='',
                save_filename='solution.md'
            )

            if file_path:
                if isinstance(file_path, (tuple, list)):
                    file_path = file_path[0]

                with open(str(file_path), 'w', encoding='utf-8') as f:
                    f.write(md_str)
                return {"success": True}
            return {"success": False, "reason": "cancelled"}
        except Exception as e:
            return {"error": str(e)}

if __name__ == '__main__':
    api = Api()

    import sys
    if getattr(sys, 'frozen', False):
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(os.path.abspath(__file__))

    ui_path = os.path.join(basedir, 'ui', 'index.html')

    window = webview.create_window('Модифицированный Симплекс-Метод', ui_path, js_api=api, width=1200, height=800)
    webview.start(debug=False)
