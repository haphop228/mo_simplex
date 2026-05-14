# 🔍 Аудит кода: список багов с заданиями для отдельных агентов

---

## 📚 Контекст проекта

Проект — десктопное приложение на Python + pywebview, решает задачи линейного программирования двухфазным модифицированным симплекс-методом с точной арифметикой (`fractions.Fraction`).

**Архитектура:**
- [`core/models.py`](core/models.py:1) — датаклассы `LinearProblem`, `SimplexStep`.
- [`core/solver.py`](core/solver.py:1) — алгоритм симплекс-метода и редукция к канонической форме.
- [`core/exporter.py`](core/exporter.py:1) — рендеринг шагов в Markdown / HTML с LaTeX.
- [`main.py`](main.py:1) — Python ↔ JS API (`Api` класс) и запуск webview.
- [`ui/index.html`](ui/index.html:1), [`ui/app.js`](ui/app.js:1), [`ui/styles.css`](ui/styles.css:1) — фронтенд.
- [`tests/`](tests:1) — 50 проходящих тестов (но они не покрывают баги ниже).

**Запуск тестов:**
```bash
cd /Users/alice3e/Desktop/Work_Main/MO
python3 -m pytest tests/ --ignore=tests/test_api.py --tb=short
```

**Известная корректная задача** (контрольная точка регрессии):
- См. [`xample.md`](xample.md:1) — `min 46x₁+10x₂+14x₃, …, lb=[0,0,100], ub=[None,250,None]` → `f*=7280, x*=[40,250,210]`.
- Сейчас она решается **верно**. При любой правке убедиться, что регрессия не сломала её.

---

### 🐛 Баг 9— `Fraction(float).limit_denominator()` теряет точность для входных чисел с большими знаменателями

| Поле | Значение |
|---|---|
| **Приоритет** | 🟠 Серьёзный |
| **Файл** | [`main.py:19-21`](main.py:19), [`main.py:39`](main.py:39) |
| **Функция** | [`Api.solve()`](main.py:17) |
| **Зависимости** | Нет. |

**Симптом:** UI присылает значения как JS-числа (float64). В [`main.py`](main.py:19) делается `Fraction(x).limit_denominator()`. Дефолтный аргумент `limit_denominator(max_denominator=10**6)` округляет дроби со знаменателем больше миллиона. Для рядовых задач это незаметно, но при вводе, например, `0.1` (float — `3602879701896397/36028797018963968`) `limit_denominator` корректно вернёт `1/10`. А вот `1/7` через float сохраняется неточно, и `limit_denominator()` даёт `1/7` корректно, но `1/1000003` уже даст `0/1`.

**Что сделать:**

1. Передавать числа из JS как **строки** (`String(value)`), а не как `parseFloat`. В Python — `Fraction(str_value)` (без `limit_denominator`) парсит десятичные строки точно.
2. В [`ui/app.js:210`](ui/app.js:210) — заменить `parseFloat(el.value)` на `el.value.trim()` (или `el.value || '0'`).
3. В [`main.py:19-21`](main.py:19) — `Fraction(x)` без `limit_denominator`.
4. Обновить тип в [`tests/test_api.py`](tests/test_api.py:1).

**Тест:** добавить кейс с дробным коэффициентом `1/3`, ввести как `"0.333333"` и проверить что результат соответствует.

---

## 🟡 Косметические и стилистические

---

### 🐛 Баг #10 — `has_inversions or True` — тавтология

| Поле | Значение |
|---|---|
| **Приоритет** | 🟡 Косметика |
| **Файл** | [`core/exporter.py:213`](core/exporter.py:213) |
| **Зависимости** | Нет. |

**Симптом:** Условие `if u_orig is not None and (has_inversions or True):` всегда совпадает с `if u_orig is not None:`. Лишняя логика.

**Что сделать:** Заменить на `if u_orig is not None:`.

---

### 🐛 Баг #11 — Хрупкое форматирование `_format_objective_terms`

| Поле | Значение |
|---|---|
| **Приоритет** | 🟡 Косметика |
| **Файл** | [`core/exporter.py:33-53`](core/exporter.py:33) |
| **Зависимости** | Нет. |

**Симптом:** При коэффициенте `±1` строка формируется как `f"{sign} {coeff}{sep}{var}"`, где `coeff = ""`, `sep = ""`. Получается двойной пробел. Внешний `.strip()` спасает первый член, но внутри строки могут оставаться двойные пробелы.

**Что сделать:** Переписать через явный `terms.append(...)` с условиями:
```python
if c_abs == 1:
    term = f"{sign}{var}"
elif coeff.startswith("\\frac"):
    term = f"{sign}{coeff}\\,{var}"
else:
    term = f"{sign}{coeff}{var}"
terms.append(term)
```
Затем `" ".join(terms)` без `strip()`.

**Тест:** проверить [`tests/test_exporter.py`](tests/test_exporter.py:1) после правки.

---

### 🐛 Баг #12 — O(m²·n) проверка `if j in self.N` + потенциальное застревание искусственной

| Поле | Значение |
|---|---|
| **Приоритет** | 🟡 Косметика + латентный |
| **Файл** | [`core/solver.py:591-612`](core/solver.py:591) |
| **Функция** | [`_purge_artificials_from_basis()`](core/solver.py:591) |
| **Зависимости** | Нет. |

**Симптом:**

1. **Производительность:** [`строка 602`](core/solver.py:602) — `if j in artificial_set or j in self.N:` — линейный поиск в списке. Для задач с большим количеством переменных O(m²·n) лишних операций.
2. **Корректность:** если для нулевой искусственной нашёлся `j` с `z[i] == 0` (вырожденный случай), функция тихо оставляет её в базисе.

**Что сделать:**

1. Заменить `self.N` на `set(self.N)` перед циклом.
2. Если искусственная нулевая не выводится — это **не баг** (она «заморожена» через `forbidden` в фазе II), но добавить логирование/предупреждение, чтобы при поиске других багов было видно.

---

### 🐛 Баг #13 — Дублирующиеся `import sys`

| Поле | Значение |
|---|---|
| **Приоритет** | 🟡 Косметика |
| **Файл** | [`main.py:3,111,204`](main.py:3) |
| **Зависимости** | Нет. |

`import sys` встречается трижды. Оставить только верхний.

---

### 🐛 Баг #14 — Не подтверждена консистентность `requirements.txt` с README

| Поле | Значение |
|---|---|
| **Приоритет** | 🟡 Косметика |
| **Файл** | [`requirements.txt`](requirements.txt:1) |
| **Зависимости** | Нет. |

**Что сделать:** Открыть [`requirements.txt`](requirements.txt:1), убедиться что там есть `pywebview` (используется в [`main.py:1`](main.py:1)) и `pyinstaller` (используется в [`build.py:1`](build.py:1)). Если нет — добавить.

---

## 🆕 Новые баги, обнаруженные во второй итерации аудита

---

### 🐛 Баг #15 — Нет валидации размерностей `LinearProblem` в `__init__`

| Поле | Значение |
|---|---|
| **Приоритет** | 🟠 Серьёзный |
| **Файл** | [`core/models.py:8-19`](core/models.py:8) |
| **Зависимости** | Нет. |

**Симптом:** Если `len(c) != len(A[0])` или `len(b) != len(A)` или `len(signs) != len(A)` — `dataclass`-конструктор молча принимает несогласованные данные, и солвер падает в случайном месте с малопонятным сообщением.

**Что сделать:** Добавить `__post_init__` в [`LinearProblem`](core/models.py:9):
```python
def __post_init__(self):
    n = len(self.c)
    m = len(self.A)
    if any(len(row) != n for row in self.A):
        raise ValueError(f"A: все строки должны иметь длину {n}")
    if len(self.b) != m:
        raise ValueError(f"len(b)={len(self.b)} != len(A)={m}")
    if len(self.signs) != m:
        raise ValueError(f"len(signs)={len(self.signs)} != len(A)={m}")
    for s in self.signs:
        if s not in ('<=', '>=', '='):
            raise ValueError(f"signs: ожидается '<=', '>=' или '=', получено: {s!r}")
    if self.lower_bounds is not None and len(self.lower_bounds) != n:
        raise ValueError(f"len(lower_bounds)={len(self.lower_bounds)} != len(c)={n}")
    if self.upper_bounds is not None and len(self.upper_bounds) != n:
        raise ValueError(f"len(upper_bounds)={len(self.upper_bounds)} != len(c)={n}")
    if self.lower_bounds is not None and self.upper_bounds is not None:
        for j, (l, u) in enumerate(zip(self.lower_bounds, self.upper_bounds)):
            if l is not None and u is not None and l > u:
                raise ValueError(f"lb[{j}]={l} > ub[{j}]={u} (несовместная граница)")
```

**Тест:**
```python
def test_problem_validates_dimensions():
    with pytest.raises(ValueError):
        LinearProblem(c=[1,2], A=[[1,1]], b=[1,2], signs=['<='])  # len(b)≠len(A)
    with pytest.raises(ValueError):
        LinearProblem(c=[1,2], A=[[1,1]], b=[1], signs=['<<'])     # неверный знак
    with pytest.raises(ValueError):
        LinearProblem(c=[1], A=[[1]], b=[1], signs=['<='],
                      lower_bounds=[5], upper_bounds=[3])           # lb > ub
```

---

### 🐛 Баг #16 — `Fraction` коэффициенты в `is_max=False` не пересчитываются для `lower_bounds`

| Поле | Значение |
|---|---|
| **Приоритет** | 🟠 Серьёзный |
| **Файл** | [`core/solver.py:30-32`](core/solver.py:30), [`core/solver.py:482`](core/solver.py:482) |
| **Зависимости** | Связан с #4. |

**Симптом:** В `__init__` (строка 31) `self.c` инвертируется для `min`: `self.c = [c if is_max else -c for c in problem.c]`. Но `lower_bounds[j]` остаётся прежним. В [`compute_final_answer()`](core/solver.py:482) (строки 514–532) логика учитывает это для `direct` (через `self.c[ext_idx]`), но для `'fixed'` и `'neg_shift'` использует `internal_c_j = orig_c_j if self.is_max else -orig_c_j` — корректно. Однако для `direct` константа `self.c[ext_idx] * shift` использует **внутренний** `c`, а финальный `return obj_val if self.is_max else -obj_val` снова переворачивает знак — получается **двойная инверсия для min**.

**Воспроизведение:**
```python
# min x1, x1<=10, x1>=3 → ожидается x1=3, f*=3
p = LinearProblem(
    c=[Fraction(1)],
    A=[[Fraction(1)]],
    b=[Fraction(10)],
    signs=['<='], is_max=False,
    lower_bounds=[Fraction(3)],
)
s = SimplexSolver(p)
last = list(s.solve())[-1]
print(s.compute_final_answer(last))  # сейчас даёт... проверить
```

**Что сделать:** Сделать аудит знаков для каждой ветки `compute_final_answer`:
- `direct` со сдвигом: вклад `c_orig[orig_j] * shift` к **исходной** целевой. Затем финальный return должен возвращать `obj_val` (если `is_max`) или `-obj_val` (если min) **только для базисной части** — константные сдвиги должны быть отдельно.
- Лучше переписать формулу как: `f* = c_orig^T x_orig` напрямую через `recover_original_x` и `problem.c`. Это устранит весь хаос знаков.

**Альтернатива:** Заменить тело функции на:
```python
def compute_final_answer(self, last_step):
    x_orig = self.recover_original_x(last_step.x_full)
    return sum(self.problem.c[i] * x_orig[i] for i in range(self.n_orig_vars))
```

Этот вариант **гарантированно** даёт `c^T x*` и устраняет все ловушки с инверсиями. Зависит от корректного `recover_original_x` (баги #2-#3).

**Тесты:** уже есть в [`tests/test_final_answer.py`](tests/test_final_answer.py:1) — после рефакторинга должны продолжить проходить.

---

### 🐛 Баг #17 — `webview.SAVE_DIALOG` использует deprecated API

| Поле | Значение |
|---|---|
| **Приоритет** | 🟡 Косметика |
| **Файл** | [`main.py:150-153`](main.py:150), [`main.py:184-187`](main.py:184) |
| **Зависимости** | Нет. |

**Симптом:** В новых версиях `pywebview` константа `webview.SAVE_DIALOG` переехала в `webview.dialog.SaveDialog` или внутрь enum. Тип помечен `# type: ignore[arg-type]` уже сейчас — индикатор проблем.

**Что сделать:** Проверить текущую версию `pywebview` в [`requirements.txt`](requirements.txt:1). Если ≥4.x — использовать `webview.SAVE_DIALOG` через явный импорт, либо обновить через `pywebview` API guide.

---

### 🐛 Баг #18 — Сохранённый HTML ломается без интернета (KaTeX/Tailwind через CDN) → склейка числителя и знаменателя в дробях

| Поле | Значение |
|---|---|
| **Приоритет** | 🔴 Критический (UX-критический) |
| **Файл** | [`main.py:130-141`](main.py:130) (метод `Api.save_html`) |
| **Зависимости** | Нет. |

**Симптом (подтверждён пользователем на Windows):** В PDF, полученном из сохранённого HTML, **дроби рендерятся слитно — числитель прилеплен к знаменателю**, дробная черта отсутствует. Это происходит, когда `katex.min.css` не успевает или не может загрузиться (нет интернета, медленный сайт, CSP-блокировка, или браузер преобразует страницу в PDF до завершения сетевых запросов).

KaTeX рендерит дробь как трёхэтажную HTML-структуру:
```html
<span class="mfrac">
    <span class="frac-line" style="border-bottom-width: 0.04em;"></span>
    <span>numerator</span>
    <span>denominator</span>
</span>
```
Без CSS (`katex.min.css`) исчезают:
- `border-bottom` на `.frac-line` — нет дробной черты;
- `display:flex; flex-direction:column` — числитель и знаменатель ложатся в строку.

Аналогичный риск — для Tailwind: без него ломается вся вёрстка страницы.

**Воспроизведение:** Выключить интернет, открыть приложение, решить любую дробную задачу, нажать «Сохранить PDF», открыть сохранённый `solution.html` в браузере — дроби сольются.

**Что сделать (порядок предпочтения):**

#### Вариант A (правильный, но требует работы) — встроить CSS/JS прямо в HTML

В [`Api.save_html()`](main.py:92) **до** генерации `full_html`:
1. Поставить в `requirements.txt` пакет `katex` через `pip install katex` или скачать архив `katex-0.16.8.zip` с CDN и положить в `ui/vendor/katex/`.
2. Прочитать содержимое `katex.min.css`, `fonts/*.woff2` (через `base64-encoding`), `katex.min.js`, `contrib/auto-render.min.js`.
3. Встроить их как inline-`<style>` и inline-`<script>` в `full_html`.
4. Аналогично с Tailwind: либо скачать собранный `tailwind.min.css`, либо переписать минимальную нужную часть стилей вручную (большинство классов в проекте сводимы к ~50 CSS-правилам).

Шаблон встраивания:
```python
def _read_vendor(path: str) -> str:
    full = os.path.join(basedir, 'ui', 'vendor', path)
    with open(full, 'r', encoding='utf-8') as f:
        return f.read()

katex_css = _read_vendor('katex/katex.min.css')
katex_js = _read_vendor('katex/katex.min.js')
katex_auto = _read_vendor('katex/auto-render.min.js')
tailwind_css = _read_vendor('tailwind/tailwind.min.css')

full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>{tailwind_css}</style>
<style>{katex_css}</style>
<style>{extra_css}</style>
<script>{katex_js}</script>
<script>{katex_auto}</script>
<script>
window.addEventListener('DOMContentLoaded', function() {{
    renderMathInElement(document.body, {{
        delimiters: [
            {{left: '$$', right: '$$', display: true}},
            {{left: '$', right: '$', display: false}}
        ],
        throwOnError: false
    }});
}});
</script>
</head>
<body>
{content_html}
</body>
</html>"""
```

**Важно** для KaTeX: шрифты (`.woff2`) загружаются через `@font-face url(...)` относительными путями. Чтобы они тоже встроились, нужно:
- Либо взять `katex.min.css` и заменить `url(fonts/KaTeX_Main-Regular.woff2)` на `url(data:font/woff2;base64,...)` (base64-кодирование);
- Либо использовать собранный `katex-self-contained.css` (его генерируют через `npm run build`).

Сборку можно автоматизировать в `build.py` (загрузить, обработать, положить в `ui/vendor/`).

#### Вариант B (быстрый, но менее надёжный) — дождаться загрузки CSS перед `window.print`

Это **не решает** оффлайн-проблему, но устраняет race-condition при медленном интернете:

В [`main.py:124-141`](main.py:124) заменить `<script defer src=...>` на синхронную загрузку и `onload`-чейн:
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    renderMathInElement(document.body, {
        delimiters: [{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],
        throwOnError:false
    });
});
</script>
```

В текущем коде [`main.py:132-133`](main.py:132) — `auto-render` подключается с `onload` атрибутом, который вызывает `renderMathInElement` сразу. Но если **CSS** ещё не загрузился (`<link rel="stylesheet">` загружается параллельно и не блокирует `onload`-скрипта), браузер успеет напечатать PDF до того, как стили применятся.

#### Вариант C (компромисс) — отказ от «Сохранить PDF» через браузер и переход к нативному рендеру

См. баг #22 ниже.

**Тест:** ручной — выключить интернет, сохранить HTML, открыть в браузере, убедиться что дроби рендерятся корректно.

---

### 🐛 Баг #19 — Динамический CSS `dynamic-print-style` не удаляется при `resetApp`

| Поле | Значение |
|---|---|
| **Приоритет** | 🟡 Косметика |
| **Файл** | [`ui/app.js:352-360`](ui/app.js:352), [`ui/app.js:344-349`](ui/app.js:344) |
| **Зависимости** | Нет. |

**Симптом:** При нажатии «Новая задача» предыдущий CSS-блок `<style id="dynamic-print-style">` остаётся в DOM. Если решить новую задачу — он переопределяется, но при множественных вызовах может оставаться мусор.

**Что сделать:** В [`resetApp()`](ui/app.js:344) добавить:
```js
const oldStyle = document.getElementById('dynamic-print-style');
if (oldStyle) oldStyle.remove();
```

---

### 🐛 Баг #22 — «Сохранить PDF» в действительности сохраняет HTML и заставляет пользователя печатать вручную

| Поле | Значение |
|---|---|
| **Приоритет** | 🟠 Серьёзный (UX) |
| **Файл** | [`main.py:92-164`](main.py:92), [`ui/index.html:26`](ui/index.html:26), [`ui/app.js:296-310`](ui/app.js:296) |
| **Зависимости** | Связан с #18 (если правится через прямую генерацию PDF, проблема дробей #18 решается автоматически). |

**Симптом (подтверждён пользователем):** Пользователь нажимает кнопку **«Сохранить PDF»**. Ожидает получить PDF-файл. Но фактически:
1. Открывается диалог сохранения файла с расширением `.html`.
2. После сохранения появляется alert: «HTML сохранён. Откройте файл в браузере и нажмите Ctrl+P → "Сохранить как PDF"».
3. Пользователю приходится:
   - найти сохранённый файл,
   - открыть в браузере,
   - нажать Ctrl+P,
   - в диалоге печати выбрать «Сохранить как PDF» (на Windows — это виртуальный принтер «Microsoft Print to PDF» в системном диалоге),
   - выбрать имя и место для итогового PDF.

Это **5 ручных действий вместо одного**. И PDF получается «кривоватым» (см. #18 — дроби могут не отрендериться, если открыть быстро).

**Кнопка с надписью «Сохранить PDF» — обманывает пользователя** относительно того, что произойдёт. Это не баг кода, это **архитектурное решение**, давно ставшее ограничением.

**Корень проблемы:** `pywebview` сам по себе **не умеет** генерировать PDF из HTML. Чтобы дать пользователю настоящий PDF, нужна одна из стратегий:

#### Вариант A (рекомендуется) — генерация PDF на стороне Python через `weasyprint`

`weasyprint` — это Python-библиотека для рендера HTML+CSS в PDF, поддерживает большинство современных CSS-фишек, включая `@page`, `page-break-inside`, кастомные шрифты. KaTeX-разметку он умеет (т.к. это обычный HTML с CSS).

```python
# requirements.txt
weasyprint>=60.0
```

```python
# main.py — новый метод
from weasyprint import HTML, CSS

def save_pdf(self, detailed=False, hidden_steps=None):
    if not self.last_problem or not self.last_steps:
        return {"error": "Нет решенной задачи"}
    try:
        # 1. Генерируем self-contained HTML (как и сейчас, но с inline-ресурсами — см. баг #18, Вариант A)
        full_html = self._build_full_html(detailed, hidden_steps)
        
        # 2. Открываем диалог сохранения PDF
        window = webview.windows[0]
        file_path = window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory='',
            save_filename='solution.pdf'
        )
        if not file_path:
            return {"success": False, "reason": "cancelled"}
        if isinstance(file_path, (tuple, list)):
            file_path = file_path[0]
        
        # 3. Рендер HTML → PDF
        HTML(string=full_html).write_pdf(str(file_path))
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}
```

В UI оставить кнопку «Сохранить PDF», которая зовёт `pywebview.api.save_pdf(...)` — пользователь получает **настоящий PDF одним кликом**.

**Минусы weasyprint:**
- Дополнительная зависимость ≈10 МБ;
- Для KaTeX-математики нужны встроенные шрифты `.woff2` (через `@font-face` с base64 — см. вариант A бага #18);
- На Windows для PyInstaller-сборки нужно явно прокидывать `--collect-data weasyprint` и `--collect-binaries libgobject-2.0-0.dll` (GTK runtime). Это создаёт нагрузку на DevOps.

#### Вариант B (компромисс) — переименовать кнопку и оставить как есть

Минимальная правка с честной коммуникацией:
1. Переименовать кнопку в **«Сохранить HTML для печати»** в [`ui/index.html:26`](ui/index.html:26).
2. Обновить tooltip и alert: убрать обещание PDF.
3. Не вводить пользователя в заблуждение — пусть текущий поток «HTML → ручная печать» остаётся, но **явно**.

Этот вариант не решает основную проблему, но делает поведение предсказуемым.

#### Вариант C (промежуточный) — вызвать `window.print()` сразу после рендера

В [`ui/app.js`](ui/app.js:296) после `pywebview.api.save_html(...)` (или вместо него) делать `window.print()`. Это откроет браузерный диалог печати **прямо из приложения**, и пользователь сразу выберет «Сохранить как PDF». Шагов всё ещё 3, но не 5.

**Проблема:** pywebview использует системный WebView (Edge/WebKit), и `window.print()` в нём может вести себя неконсистентно. На Windows иногда открывается системный диалог печати без опции «PDF».

#### Рекомендация

**Вариант A** — единственный, который реально решает заявленную функциональность. Если объём работы пугает (нужно собрать `weasyprint` для всех платформ), как промежуточный шаг — **Вариант B** (хотя бы перестать обманывать пользователя).

**Тест:**
- Ручной: нажать «Сохранить PDF», убедиться что появляется диалог «Сохранить .pdf файл», после Save — открыть его и проверить корректность дробей и вёрстки.
- Автоматический: добавить smoke-тест на `Api.save_pdf()` через mock диалога.

---

## 📋 Финальная сводка

| # | Приоритет | Файл | Краткое описание | Зависит от |
|---|---|---|---|---|
| 1 | 🔴 | [`core/solver.py:138-179`](core/solver.py:138) | UB игнорируется при `lb≠0` | — |
| 2 | 🔴 | [`core/solver.py:95-189`](core/solver.py:95) | Рассинхрон `_var_map` ↔ `A` | — |
| 3 | 🔴 | [`core/solver.py:535`](core/solver.py:535) | `IndexError` в `recover_original_x` | #2 |
| 4 | 🔴 | [`core/solver.py:482`](core/solver.py:482) | Неверная константа `compute_final_answer` | #2 |
| 5 | 🟠 | [`core/solver.py:429`](core/solver.py:429) | Скрытое `self.N[-1]` | — |
| 6 | 🟠 | [`core/solver.py:342`](core/solver.py:342) | Лишний инкремент `iteration_counter` | — |
| 7 | 🟠 | [`ui/app.js:210`](ui/app.js:210) | `NaN` при пустых полях | — |
| 8 | 🟠 | [`ui/index.html:69`](ui/index.html:69) | Мёртвый блок UI | — |
| 9 | 🟠 | [`build.py`](build.py:1) | Конфликт `.spec` vs `build.py` | — |
| 10 | 🟡 | [`core/exporter.py:213`](core/exporter.py:213) | `or True` тавтология | — |
| 11 | 🟡 | [`core/exporter.py:33`](core/exporter.py:33) | Хрупкое форматирование коэффициентов | — |
| 12 | 🟡 | [`core/solver.py:591`](core/solver.py:591) | `j in list` O(n) + потенц. вырождение | — |
| 13 | 🟡 | [`main.py:3`](main.py:3) | Дублирующиеся `import sys` | — |
| 14 | 🟡 | [`requirements.txt`](requirements.txt:1) | Не подтверждена консистентность | — |
| 15 | 🟠 | [`core/models.py:8`](core/models.py:8) | Нет валидации размерностей | — |
| 16 | 🟠 | [`core/solver.py:482`](core/solver.py:482) | Возможная двойная инверсия знака для `min` | #2, #4 |
| 17 | 🟡 | [`main.py:150`](main.py:150) | Deprecated `webview.SAVE_DIALOG` | — |
| 18 | 🔴 | [`main.py:130`](main.py:130) | **Дроби в сохранённом PDF склеиваются** (CDN не догрузился) | — |
| 19 | 🟡 | [`ui/app.js:352`](ui/app.js:352) | `dynamic-print-style` не удаляется | — |
| 20 | 🔴 | [`core/solver.py`](core/solver.py:1) + [`main.py:64`](main.py:64) | Нет валидации выходного `x*` относительно границ | желательно после #1-#4 |
| 21 | 🟠 | [`main.py:19`](main.py:19) + [`ui/app.js:210`](ui/app.js:210) | Потеря точности через `parseFloat`/`limit_denominator` | — |
| 22 | 🟠 | [`main.py:92`](main.py:92) + [`ui/index.html:26`](ui/index.html:26) | «Сохранить PDF» сохраняет HTML и заставляет печатать вручную | связан с #18 |

---

## 🚀 Рекомендация по делегированию

**Параллельные треки (могут вестись независимо одновременно):**

### Трек «Математика» (1 опытный агент, последовательно)
- Спринт 1: **#2 → #3 → #4 → #1** одним PR (логически связаны через `_var_map`).
- Спринт 2: **#16** (рефакторинг `compute_final_answer` через `recover_original_x`).

### Трек «Защитная сеть» (1 агент, параллельно с математикой)
- Спринт 1: **#20** (валидация выходного `x*`) — позволит увидеть, что починили математические баги.
- Спринт 1: **#15** (валидация `LinearProblem` на входе).

### Трек «Экспорт / PDF» (1 агент, параллельно)
- Спринт 1: **#18 + #22 одним PR** — встроить KaTeX/Tailwind как inline-ресурсы (решает дробями склеиваются), плюс заменить `save_html` на `save_pdf` через `weasyprint`. Это решает обе пользовательские жалобы:
  > «у дробей склеены числитель с знаменателем»
  > «сразу PDF не даёт, только через программу для печати»
- Альтернатива (если weasyprint слишком тяжёл): вариант B бага #22 + вариант A бага #18.

### Трек «UI» (1 агент, параллельно)
- Спринт 1: **#7** (NaN при пустых полях) + **#21** (точность ввода через строки) — оба касаются формы ввода.
- Спринт 2: **#8** (мёртвый блок UI), **#19** (CSS-мусор после resetApp).

### Трек «Качество кода» (1 агент, параллельно)
- Спринт 1: **#5** (защитный if), **#6** (счётчик итераций).
- Спринт 2 (косметика): **#9** (билд), **#10**, **#11**, **#12**, **#13**, **#14**, **#17**.

---

### Сводка приоритетов по треку

| Трек | Спринт 1 (critical) | Спринт 2 (nice-to-have) |
|---|---|---|
| Математика | #1, #2, #3, #4 | #16 |
| Защитная сеть | #15, #20 | — |
| Экспорт / PDF | #18, #22 | — |
| UI | #7, #21 | #8, #19 |
| Качество кода | #5, #6 | #9, #10, #11, #12, #13, #14, #17 |

---

## ✅ Контрольный регрессионный тест

Перед merge **любого** PR — прогнать оба следующих кейса. Они должны давать одинаковый результат до и после изменений (известно: правильно):

```python
def test_xample_md_regression():
    """Контрольный кейс из xample.md: f*=7280, x*=[40, 250, 210]."""
    p = LinearProblem(
        c=[Fraction(46), Fraction(10), Fraction(14)],
        A=[[Fraction(1), Fraction(1), Fraction(1)],
           [Fraction(81), Fraction(2), Fraction(6)],
           [Fraction(5), Fraction(22), Fraction(6)]],
        b=[Fraction(500), Fraction(5000), Fraction(7000)],
        signs=['=', '>=', '<='],
        is_max=False,
        lower_bounds=[Fraction(0), Fraction(0), Fraction(100)],
        upper_bounds=[None, Fraction(250), None],
    )
    s = SimplexSolver(p)
    last = list(s.solve())[-1]
    assert last.is_optimal
    assert s.compute_final_answer(last) == Fraction(7280)
    x = s.recover_original_x(last.x_full)
    assert x == [Fraction(40), Fraction(250), Fraction(210)]


def test_all_existing_pass():
    """Прогон всех 50 существующих тестов:
       pytest tests/ --ignore=tests/test_api.py
       должно остаться 50/50 проходящих."""
```
