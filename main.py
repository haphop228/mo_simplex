import webview
import os
from fractions import Fraction
from core.models import LinearProblem
from core.solver import SimplexSolver
from core.exporter import Exporter

class Api:
    def __init__(self):
        self.last_problem = None
        self.last_steps = None
        self.last_final_answer = None

    def solve(self, data):
        try:
            c = [Fraction(x).limit_denominator() for x in data['c']]
            A = [[Fraction(x).limit_denominator() for x in row] for row in data['A']]
            b = [Fraction(x).limit_denominator() for x in data['b']]
            signs = data['signs']
            is_max = data['is_max']

            problem = LinearProblem(c, A, b, signs, is_max)
            solver = SimplexSolver(problem)
            steps = list(solver.solve())

            final_answer = None
            if steps and steps[-1].is_optimal:
                final_step = steps[-1]
                c_B = [solver.c[idx] for idx in final_step.N]
                obj_val = sum(c_B[i] * final_step.x_B[i] for i in range(len(final_step.N)))
                # If minimizing, we need to multiply the result by -1
                final_answer = obj_val if problem.is_max else -obj_val

            self.last_problem = problem
            self.last_steps = steps
            self.last_final_answer = final_answer

            detailed = data.get('detailed', False)
            html_output = Exporter.generate_html(problem, steps, final_answer, detailed=detailed)
            return html_output

        except Exception as e:
            return {"error": str(e)}

    def save_markdown(self, detailed=False, hidden_steps=None):
        if not self.last_problem or not self.last_steps:
            return {"error": "Нет решенной задачи"}

        try:
            md_str = Exporter.generate_markdown(self.last_problem, self.last_steps, self.last_final_answer, detailed=detailed, hidden_steps=hidden_steps)
            
            # Using webview's save file dialog
            window = webview.windows[0]
            file_path = window.create_file_dialog(
                webview.SAVE_DIALOG, 
                directory='', 
                save_filename='solution.md'
            )
            
            if file_path:
                # create_file_dialog returns a tuple/list or a string
                if isinstance(file_path, tuple) or isinstance(file_path, list):
                    file_path = file_path[0]
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(md_str)
                return {"success": True}
            return {"success": False, "reason": "cancelled"}
        except Exception as e:
            return {"error": str(e)}

if __name__ == '__main__':
    api = Api()
    
    # Check if running in PyInstaller bundle
    import sys
    if getattr(sys, 'frozen', False):
        # We are running in a |PyInstaller| bundle
        basedir = sys._MEIPASS
    else:
        # We are running in a normal Python environment
        basedir = os.path.dirname(os.path.abspath(__main__.__file__)) if '__main__' in dir() else os.getcwd()
        
    ui_path = os.path.join(basedir, 'ui', 'index.html')
    
    window = webview.create_window('Модифицированный Симплекс-Метод', ui_path, js_api=api, width=1200, height=800)
    webview.start(debug=False)
