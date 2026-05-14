import re
from typing import List, Optional, Tuple
from fractions import Fraction
from core.models import LinearProblem, SimplexStep


class Exporter:
    # ---------------------------------------------------------------- LaTeX helpers
    @staticmethod
    def frac_to_latex(f: Fraction) -> str:
        if f.denominator == 1:
            return str(f.numerator)
        if f.numerator < 0:
            return f"-\\frac{{{-f.numerator}}}{{{f.denominator}}}"
        return f"\\frac{{{f.numerator}}}{{{f.denominator}}}"

    @staticmethod
    def vec_to_latex(v: List[Fraction], is_column: bool = True) -> str:
        if is_column:
            lines = " \\\\ ".join(Exporter.frac_to_latex(x) for x in v)
        else:
            lines = " & ".join(Exporter.frac_to_latex(x) for x in v)
        return f"\\begin{{bmatrix}} {lines} \\end{{bmatrix}}"

    @staticmethod
    def mat_to_latex(M: List[List[Fraction]]) -> str:
        rows = [" & ".join(Exporter.frac_to_latex(x) for x in row) for row in M]
        body = " \\\\ \n".join(rows)
        return f"\\begin{{bmatrix}}\n{body}\n\\end{{bmatrix}}"

    # ---------------------------------------------------------------- problem statements
    @staticmethod
    def _format_objective_terms(coeffs: List[Fraction], var_letter: str = "x") -> str:
        terms = []
        for i, c in enumerate(coeffs):
            if c != 0:
                sign = "+" if c > 0 and terms else ("" if c > 0 else "-")
                c_abs = abs(c)
                if c_abs == 1:
                    coeff = ""
                    sep = ""
                else:
                    coeff = Exporter.frac_to_latex(c_abs)
                    # Если коэффициент — дробь (\frac{...}{...}), добавляем тонкий пробел
                    # чтобы числитель/знаменатель не склеивались с именем переменной
                    sep = "\\," if coeff.startswith("\\frac") else ""
                terms.append(f"{sign} {coeff}{sep}{var_letter}_{{{i+1}}}")
        if not terms:
            terms.append("0")
        s = " ".join(terms).strip()
        if s.startswith("+ "):
            s = s[2:]
        return s

    @staticmethod
    def _format_problem_block(problem: LinearProblem) -> List[str]:
        lines: List[str] = []
        lines.append("$$")
        lines.append("\\begin{align*}")
        obj_str = Exporter._format_objective_terms(problem.c, "x")
        target = "\\max" if problem.is_max else "\\min"
        lines.append(f"{obj_str} &\\to {target} \\\\")
        for i, row in enumerate(problem.A):
            row_str = Exporter._format_objective_terms(row, "x")
            sign_map = {"<=": "\\leq", ">=": "\\geq", "=": "="}
            lines.append(f"{row_str} &{sign_map[problem.signs[i]]} {Exporter.frac_to_latex(problem.b[i])} \\\\")
        lines.append("x &\\geq 0")
        lines.append("\\end{align*}")
        lines.append("$$\n")
        return lines

    @staticmethod
    def _format_dual_block(problem: LinearProblem) -> List[str]:
        lines: List[str] = []
        lines.append("$$")
        lines.append("\\begin{align*}")
        dual_obj_str = Exporter._format_objective_terms(problem.b, "u")
        dual_target = "\\min" if problem.is_max else "\\max"
        lines.append(f"{dual_obj_str} &\\to {dual_target} \\\\")
        for j in range(len(problem.c)):
            col = [problem.A[i][j] for i in range(len(problem.A))]
            row_str = Exporter._format_objective_terms(col, "u")
            sign_str = "\\geq" if problem.is_max else "\\leq"
            lines.append(f"{row_str} &{sign_str} {Exporter.frac_to_latex(problem.c[j])} \\\\")
        lines.append("u &\\geq 0")
        lines.append("\\end{align*}")
        lines.append("$$\n")
        return lines

    # ---------------------------------------------------------------- step rendering
    @staticmethod
    def _phase_label(phase: int) -> str:
        return "Фаза I (вспомогательная задача)" if phase == 1 else "Фаза II"

    @staticmethod
    def _step_heading(step) -> str:
        """Заголовок шага: «Шаг N» для итерации с pivot, «Итог»/«Неограниченность»/
        «Несовместность» для терминальных шагов (без реального pivot).

        Терминальные шаги в текущей реализации получают такой же номер итерации,
        как и предыдущий pivot, поэтому отображать «Шаг N» для них вводит в
        заблуждение.
        """
        if getattr(step, 'is_infeasible', False):
            return "Итог (несовместность)"
        if getattr(step, 'is_unbounded', False):
            return "Итог (неограниченность)"
        if getattr(step, 'is_optimal', False):
            return "Итог (оптимум)"
        return f"Шаг {step.iteration}"

    @staticmethod
    def _render_step_lines(
        step: SimplexStep,
        detailed: bool,
        final_answer: Optional[Fraction],
        x_original: Optional[List[Fraction]] = None,
        n_orig_vars: Optional[int] = None,
    ) -> List[str]:
        """Возвращает линии Markdown-описания шага (без HTML-обёрток)."""
        lines: List[str] = []

        artificial_set = set(step.artificial_indices or [])

        def var_label(idx: int) -> str:
            if idx in artificial_set:
                return f"y_{{{idx+1}}}"
            return f"x_{{{idx+1}}}"

        basis_labels = ", ".join(var_label(n) for n in step.N)
        lines.append(f"**Базис $N$:** $({basis_labels})$  ")
        lines.append(f"**Полный план $x$:**  ")
        lines.append(f"$$ x = {Exporter.vec_to_latex(step.x_full, is_column=False)} $$  ")
        lines.append(f"**Базисная подвыборка $x_B$:**  ")
        lines.append(f"$$ x_B = {Exporter.vec_to_latex(step.x_B)} $$  ")
        lines.append(f"**Обратная базисная матрица $B$:**  ")
        lines.append(f"$$ B = {Exporter.mat_to_latex(step.B_inv)} $$  ")

        if detailed and step.c_B is not None:
            c_b_str = "\\begin{bmatrix} " + " & ".join(Exporter.frac_to_latex(x) for x in step.c_B) + " \\end{bmatrix}"
            lines.append(
                f"**Вектор оценок $u_0 = c_B B$:**  \n"
                f"$$ u_0 = {c_b_str} \\cdot B = {Exporter.vec_to_latex(step.u_0, is_column=False)} $$  "
            )
        else:
            lines.append(f"**Вектор оценок $u_0$:**  \n$$ u_0 = {Exporter.vec_to_latex(step.u_0, is_column=False)} $$  ")

        # Δ_j: выводим только посчитанные (до первого отрицательного включительно).
        if step.diffs:
            lines.append("**Проверка оптимальности $\\Delta_j = u_0 A_j - c_j$ (по правилу первого индекса):**")
            lines.append("$$ \\begin{align*} ")
            for j, diff in step.diffs:
                marker = ""
                if diff < 0:
                    marker = " \\quad <\\!0\\ \\Rightarrow\\ j_0 = " + str(j + 1)
                lines.append(f"\\Delta_{{{j+1}}} &= {Exporter.frac_to_latex(diff)}{marker} \\\\ ")
            lines.append("\\end{align*} $$\n")

        # Финальные исходы шага
        if step.is_infeasible:
            lines.append("\n❌ **Задача несовместна.** На фазе I минимум суммы искусственных переменных строго положителен.\n")
            return lines

        if step.is_optimal:
            if step.phase == 1:
                lines.append("\n✓ **Фаза I завершена.** Все искусственные равны нулю — переходим к фазе II.\n")
            else:
                lines.append("\n✓ **План оптимален.** Все двойственные ограничения выполнены.\n")
                if final_answer is not None:
                    lines.append(f"**Ответ:** $f^* = {Exporter.frac_to_latex(final_answer)}$\n")

                # Восстановленные исходные переменные (если были редукции)
                if x_original is not None and n_orig_vars is not None:
                    x_orig_str = Exporter.vec_to_latex(x_original[:n_orig_vars], is_column=False)
                    lines.append(f"**Исходные переменные $x^*$:** $x^* = {x_orig_str}$\n")

                # Защитная сетка (баг #5): если восстановленное решение нарушает
                # исходные ограничения — выводим предупреждение.
                errs = getattr(step, 'validation_errors', None)
                if errs:
                    lines.append(
                        "\n⚠️ **Внимание:** восстановленное решение НАРУШАЕТ "
                        "исходные ограничения задачи. Это указывает на ошибку в солвере "
                        "или некорректно заданную задачу:\n"
                    )
                    for e in errs:
                        lines.append(f"- {e}")
                    lines.append("")

                # Раздел двойственного решения с учётом знаков (пункт №4)
                lines.extend(Exporter._render_dual_solution(step))

            return lines

        if step.is_unbounded:
            lines.append("\n❌ **Целевая функция не ограничена.** Решения нет.\n")
            return lines

        # Обычный шаг: ввод/вывод
        j0_label = step.j_0 + 1 if step.j_0 is not None else "?"
        lines.append(f"\n**План не оптимален.** Вводим в базис $x_{{{j0_label}}}$.\n")
        if step.z_0 is not None:
            if detailed:
                lines.append(
                    f"**Направляющий вектор $z_0 = B \\cdot A_{{{j0_label}}}$:**  \n"
                    f"$$ z_0 = {Exporter.vec_to_latex(step.z_0)} $$  "
                )
            else:
                lines.append(f"**Направляющий вектор $z_0$:**  \n$$ z_0 = {Exporter.vec_to_latex(step.z_0)} $$  ")

        if step.ratios is not None and step.t_0 is not None and step.z_0 is not None:
            if detailed:
                ratios_str = ", ".join(
                    f"\\frac{{{Exporter.frac_to_latex(step.x_B[i])}}}{{{Exporter.frac_to_latex(step.z_0[i])}}}"
                    for i, r in enumerate(step.ratios) if r is not None
                )
                lines.append(f"**Шаг $t_0$:** $t_0 = \\min({ratios_str}) = {Exporter.frac_to_latex(step.t_0)}$  ")
            else:
                lines.append(f"**Шаг $t_0$:** $t_0 = {Exporter.frac_to_latex(step.t_0)}$  ")
        if step.s_0 is not None:
            lines.append(f"Выводим из базиса $x_{{{step.s_0+1}}}$.\n")
        return lines

    @staticmethod
    def _render_dual_solution(step: SimplexStep) -> List[str]:
        """Раздел двойственного решения с пояснением знаков (пункт №4 STATUS.md).

        Выводит u_0 (внутренний, для приведённой задачи) и u_0_original
        (для исходной задачи, с учётом инверсий строк и направления оптимизации).
        """
        lines: List[str] = []
        lines.append("---\n")
        lines.append("**Двойственное решение $u^*$:**\n")
        lines.append(
            f"$$ u^* = u_0 = {Exporter.vec_to_latex(step.u_0, is_column=False)} $$\n"
        )

        # Если есть инвертированные строки или задача на min — показываем пояснение
        row_inv = step.row_inverted or []
        has_inversions = any(row_inv)
        u_orig = step.u_0_original

        if u_orig is not None and (has_inversions or True):
            lines.append(
                "**Двойственное решение для исходной задачи** "
                "(с учётом инверсий строк при $b_i < 0$ и направления оптимизации):\n"
            )
            lines.append(
                f"$$ u^*_{{\\text{{orig}}}} = {Exporter.vec_to_latex(u_orig, is_column=False)} $$\n"
            )

            if has_inversions:
                inv_indices = [i + 1 for i, inv in enumerate(row_inv) if inv]
                inv_str = ", ".join(str(k) for k in inv_indices)
                lines.append(
                    f"*Строки {inv_str} были умножены на $-1$ при приведении $b \\geq 0$, "
                    f"поэтому знак соответствующих $u_i$ инвертирован.*\n"
                )

        lines.append(
            "**Проверка сильной двойственности:** "
            "$f^* = c_B^T x_B = u_0^T b$\n"
        )
        return lines

    # ---------------------------------------------------------------- markdown
    @staticmethod
    def generate_markdown(
        problem: LinearProblem,
        steps: List[SimplexStep],
        final_answer: Optional[Fraction],
        detailed: bool = False,
        hidden_steps: Optional[List[int]] = None,
        x_original: Optional[List[Fraction]] = None,
        n_orig_vars: Optional[int] = None,
    ) -> str:
        hidden = set(hidden_steps or [])
        md: List[str] = []
        md.append("# Решение задачи модифицированным двухфазным симплекс-методом\n")

        md.append("## Прямая задача")
        md.extend(Exporter._format_problem_block(problem))

        md.append("## Двойственная задача")
        md.extend(Exporter._format_dual_block(problem))

        md.append("---\n")

        last_phase: Optional[int] = None
        for step in steps:
            if step.iteration in hidden:
                continue
            if step.phase != last_phase:
                md.append(f"\n## {Exporter._phase_label(step.phase)}\n")
                last_phase = step.phase

            md.append(f"### {Exporter._step_heading(step)}")
            md.extend(Exporter._render_step_lines(
                step, detailed, final_answer,
                x_original=x_original,
                n_orig_vars=n_orig_vars,
            ))
            md.append("---\n")

        return "\n".join(md)

    # ---------------------------------------------------------------- html
    @staticmethod
    def generate_html(
        problem: LinearProblem,
        steps: List[SimplexStep],
        final_answer: Optional[Fraction],
        detailed: bool = False,
        hidden_steps: Optional[List[int]] = None,
        x_original: Optional[List[Fraction]] = None,
        n_orig_vars: Optional[int] = None,
    ) -> str:
        hidden = set(hidden_steps or [])
        html: List[str] = []

        # Шапка: прямая + двойственная
        html.append("<div class='mb-8 pb-4 border-b border-gray-200'>")
        html.append("<h3 class='text-xl font-bold text-gray-800 mb-4'>Прямая задача</h3>")
        html.append("<div class='overflow-x-auto bg-gray-50 p-4 rounded-lg'>")
        html.extend(Exporter._format_problem_block(problem))
        html.append("</div>")

        html.append("<h3 class='text-xl font-bold text-gray-800 mb-4 mt-6'>Двойственная задача</h3>")
        html.append("<div class='overflow-x-auto bg-gray-50 p-4 rounded-lg'>")
        html.extend(Exporter._format_dual_block(problem))
        html.append("</div>")
        html.append("</div>")

        last_phase: Optional[int] = None
        for step in steps:
            if step.iteration in hidden:
                continue

            if step.phase != last_phase:
                phase_color = "indigo" if step.phase == 2 else "amber"
                html.append(
                    f"<h3 class='text-2xl font-bold text-{phase_color}-700 mt-8 mb-4 border-b-2 border-{phase_color}-300 pb-1'>"
                    f"{Exporter._phase_label(step.phase)}</h3>"
                )
                last_phase = step.phase

            html.append(
                f"<div class='step-container bg-white p-6 rounded-lg border border-gray-200 shadow-sm mb-6' "
                f"id='step-card-{step.iteration}'>"
            )
            html.append("<div class='flex justify-between items-center border-b pb-2 mb-4'>")
            html.append(
                f"<h4 class='text-lg font-bold text-indigo-700'>"
                f"{Exporter._step_heading(step)} ({Exporter._phase_label(step.phase)})</h4>"
            )
            html.append(
                f"<label class='text-sm text-gray-500 flex items-center cursor-pointer no-print'>"
                f"<input type='checkbox' class='mr-2 step-visibility-toggle' data-step='{step.iteration}' "
                f"checked onchange='toggleStepVisibility(this)'> Показывать шаг</label>"
            )
            html.append("</div>")

            html.append("<div class='space-y-2 overflow-x-auto'>")
            md_lines = Exporter._render_step_lines(
                step, detailed, final_answer,
                x_original=x_original,
                n_orig_vars=n_orig_vars,
            )
            html.append(Exporter._md_lines_to_html(md_lines))
            html.append("</div>")
            html.append("</div>")

        return "\n".join(html)

    # ---------------------------------------------------------------- markdown → HTML
    @staticmethod
    def _md_lines_to_html(md_lines: List[str]) -> str:
        """Преобразует список markdown-строк (с inline `$...$` и блочными `$$...$$`)
        в HTML, сохраняя многострочные $$-блоки в едином DOM-узле для KaTeX.

        Минимальный markdown-парсинг:
        * `**bold**` → `<strong>bold</strong>`
        * `*italic*` → `<em>italic</em>` (только если не часть `**`)
        * trailing `  ` перед \n → `<br>`
        * `---` на отдельной строке → `<hr>`
        * пустая строка → `<br>` (визуальный отступ)
        """
        text = "\n".join(md_lines)

        # Жирный (greedy не годится — используем .+?)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text, flags=re.DOTALL)

        # Горизонтальная линия (отдельная строка из --- )
        text = re.sub(r"(?m)^---\s*$", "<hr class='my-3 border-gray-200'>", text)

        # Markdown two-space line break: "  \n" → "<br>\n"
        text = re.sub(r"  +\n", "<br>\n", text)

        return text
