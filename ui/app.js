let currentProblemData = null;

function buildForm() {
    const numVars = parseInt(document.getElementById('num-vars').value) || 2;
    const numConstraints = parseInt(document.getElementById('num-constraints').value) || 3;
    const canonicalMode = document.getElementById('canonical-mode').checked;

    // Build Objective
    const objContainer = document.getElementById('objective-container');
    objContainer.innerHTML = '';
    for (let i = 0; i < numVars; i++) {
        const wrap = document.createElement('div');
        wrap.className = 'flex items-center space-x-1';

        if (i > 0) {
            const plus = document.createElement('span');
            plus.innerText = '+';
            plus.className = 'text-gray-500 font-bold mx-1';
            objContainer.appendChild(plus);
        }

        const input = document.createElement('input');
        input.type = 'number';
        input.className = 'obj-coeff border border-gray-300 rounded px-2 py-1 w-20 text-center focus:ring-2 focus:ring-indigo-500 outline-none';
        input.value = '1';
        wrap.appendChild(input);

        const label = document.createElement('span');
        label.innerHTML = `x<sub>${i+1}</sub>`;
        label.className = 'font-semibold text-gray-700';
        wrap.appendChild(label);

        objContainer.appendChild(wrap);
    }

    const targetWrap = document.createElement('div');
    targetWrap.className = 'flex items-center space-x-2 ml-4';
    targetWrap.innerHTML = `
        <span class="text-gray-500 font-bold">➔</span>
        <select id="obj-target" class="border border-gray-300 rounded px-2 py-1 bg-white focus:ring-2 focus:ring-indigo-500 outline-none">
            <option value="max">max</option>
            <option value="min">min</option>
        </select>
    `;
    objContainer.appendChild(targetWrap);

    // Build Constraints
    const constrContainer = document.getElementById('constraints-container');
    constrContainer.innerHTML = '';
    for (let i = 0; i < numConstraints; i++) {
        const row = document.createElement('div');
        row.className = 'flex flex-wrap items-center space-x-2 p-2 bg-gray-50 rounded border border-gray-100';

        for (let j = 0; j < numVars; j++) {
            if (j > 0) {
                const plus = document.createElement('span');
                plus.innerText = '+';
                plus.className = 'text-gray-500 font-bold';
                row.appendChild(plus);
            }

            const wrap = document.createElement('div');
            wrap.className = 'flex items-center space-x-1';

            const input = document.createElement('input');
            input.type = 'number';
            input.className = `constr-coeff constr-${i} border border-gray-300 rounded px-2 py-1 w-20 text-center focus:ring-2 focus:ring-indigo-500 outline-none`;
            input.value = '1';
            wrap.appendChild(input);

            const label = document.createElement('span');
            label.innerHTML = `x<sub>${j+1}</sub>`;
            label.className = 'font-semibold text-gray-700 text-sm';
            wrap.appendChild(label);

            row.appendChild(wrap);
        }

        // В канонической форме все ограничения — равенства
        if (canonicalMode) {
            const eqLabel = document.createElement('span');
            eqLabel.innerText = '=';
            eqLabel.className = 'font-bold text-gray-600 ml-2';
            // Скрытый select со значением '='
            const signSelect = document.createElement('select');
            signSelect.className = `constr-sign constr-sign-${i} hidden`;
            signSelect.innerHTML = `<option value="=" selected>=</option>`;
            row.appendChild(eqLabel);
            row.appendChild(signSelect);
        } else {
            const signSelect = document.createElement('select');
            signSelect.className = `constr-sign constr-sign-${i} border border-gray-300 rounded px-2 py-1 bg-white focus:ring-2 focus:ring-indigo-500 outline-none ml-2`;
            signSelect.innerHTML = `
                <option value="<=">&le;</option>
                <option value=">=">&ge;</option>
                <option value="=">=</option>
            `;
            row.appendChild(signSelect);
        }

        const bInput = document.createElement('input');
        bInput.type = 'number';
        bInput.className = `constr-b constr-b-${i} border border-gray-300 rounded px-2 py-1 w-20 text-center focus:ring-2 focus:ring-indigo-500 outline-none ml-2`;
        bInput.value = '10';
        row.appendChild(bInput);

        constrContainer.appendChild(row);
    }

    // Build Bounds
    buildBoundsBlock(numVars, canonicalMode);
}

function buildBoundsBlock(numVars, canonicalMode) {
    const boundsContainer = document.getElementById('bounds-container');
    boundsContainer.innerHTML = '';

    for (let j = 0; j < numVars; j++) {
        const row = document.createElement('div');
        row.className = 'flex flex-wrap items-center gap-2 p-2 bg-gray-50 rounded border border-gray-100';

        const varLabel = document.createElement('span');
        varLabel.innerHTML = `x<sub>${j+1}</sub>:`;
        varLabel.className = 'font-semibold text-gray-600 w-10';
        row.appendChild(varLabel);

        // Нижняя граница
        const lbWrap = document.createElement('div');
        lbWrap.className = 'flex items-center gap-1';
        const lbLabel = document.createElement('span');
        lbLabel.className = 'text-xs text-gray-500';
        lbLabel.innerText = 'от:';
        lbWrap.appendChild(lbLabel);

        const lbInput = document.createElement('input');
        lbInput.type = 'text';
        lbInput.className = `var-lb var-lb-${j} border border-gray-300 rounded px-2 py-1 w-24 text-center focus:ring-2 focus:ring-indigo-500 outline-none text-sm`;
        // В канонической форме нижняя граница всегда 0
        lbInput.value = '0';
        lbInput.placeholder = '0';
        if (canonicalMode) {
            lbInput.disabled = true;
            lbInput.className += ' bg-gray-100 text-gray-400';
        }
        lbWrap.appendChild(lbInput);
        row.appendChild(lbWrap);

        // Верхняя граница
        const ubWrap = document.createElement('div');
        ubWrap.className = 'flex items-center gap-1';
        const ubLabel = document.createElement('span');
        ubLabel.className = 'text-xs text-gray-500';
        ubLabel.innerText = 'до:';
        ubWrap.appendChild(ubLabel);

        const ubInput = document.createElement('input');
        ubInput.type = 'text';
        ubInput.className = `var-ub var-ub-${j} border border-gray-300 rounded px-2 py-1 w-24 text-center focus:ring-2 focus:ring-indigo-500 outline-none text-sm`;
        ubInput.value = '';
        ubInput.placeholder = '+inf';
        if (canonicalMode) {
            ubInput.disabled = true;
            ubInput.className += ' bg-gray-100 text-gray-400';
        }
        ubWrap.appendChild(ubInput);
        row.appendChild(ubWrap);

        // Подсказка о типе переменной
        const hint = document.createElement('span');
        hint.className = `var-hint-${j} text-xs text-indigo-500 italic ml-2`;
        hint.innerText = 'x ≥ 0';
        row.appendChild(hint);

        // Обновляем подсказку при изменении границ
        const updateHint = () => {
            const lb = lbInput.value.trim().toLowerCase();
            const ub = ubInput.value.trim().toLowerCase();
            const lbInf = lb === '-inf' || lb === '-infinity';
            const ubInf = ub === '' || ub === 'inf' || ub === '+inf' || ub === 'infinity';
            if (lbInf && ubInf) {
                hint.innerText = 'свободная';
                hint.className = `var-hint-${j} text-xs text-purple-500 italic ml-2`;
            } else if (lb === '0' && ubInf) {
                hint.innerText = 'x ≥ 0';
                hint.className = `var-hint-${j} text-xs text-indigo-500 italic ml-2`;
            } else if (!ubInf) {
                hint.innerText = `${lb || '0'} ≤ x ≤ ${ub}`;
                hint.className = `var-hint-${j} text-xs text-amber-600 italic ml-2`;
            } else {
                hint.innerText = `x ≥ ${lb}`;
                hint.className = `var-hint-${j} text-xs text-green-600 italic ml-2`;
            }
        };
        lbInput.addEventListener('input', updateHint);
        ubInput.addEventListener('input', updateHint);

        boundsContainer.appendChild(row);
    }
}

async function solve() {
    const errDiv = document.getElementById('error-message');
    errDiv.classList.add('hidden');
    errDiv.innerText = '';

    const numVars = parseInt(document.getElementById('num-vars').value) || 2;
    const numConstraints = parseInt(document.getElementById('num-constraints').value) || 3;
    const canonicalMode = document.getElementById('canonical-mode').checked;

    // Очищаем подсветку с прошлой попытки.
    document.querySelectorAll('.input-invalid').forEach(el => {
        el.classList.remove('input-invalid');
    });

    // Валидация полей: пустое или нечисловое значение — ошибка с подсветкой.
    const missing = [];
    const parseRequiredNumber = (el, label) => {
        if (!el) {
            missing.push(label);
            return NaN;
        }
        const raw = (el.value || '').trim();
        if (raw === '') {
            el.classList.add('input-invalid');
            missing.push(label);
            return NaN;
        }
        const v = parseFloat(raw);
        if (!Number.isFinite(v)) {
            el.classList.add('input-invalid');
            missing.push(`${label} (нечисловое значение «${raw}»)`);
            return NaN;
        }
        return raw;
    };

    const c = Array.from(document.querySelectorAll('.obj-coeff'))
        .map((el, j) => parseRequiredNumber(el, `c_${j+1}`));
    const is_max = document.getElementById('obj-target').value === 'max';

    const A = [];
    const b = [];
    const signs = [];

    for (let i = 0; i < numConstraints; i++) {
        const row = Array.from(document.querySelectorAll(`.constr-${i}`))
            .map((el, j) => parseRequiredNumber(el, `A[${i+1}][${j+1}]`));
        A.push(row);
        b.push(parseRequiredNumber(
            document.querySelector(`.constr-b-${i}`),
            `b_${i+1}`,
        ));
        signs.push(document.querySelector(`.constr-sign-${i}`).value);
    }

    // Сбор границ переменных
    const lower_bounds = [];
    const upper_bounds = [];
    let hasCustomBounds = false;
    let boundsInvalid = false;

    for (let j = 0; j < numVars; j++) {
        const lbEl = document.querySelector(`.var-lb-${j}`);
        const ubEl = document.querySelector(`.var-ub-${j}`);

        const lbStr = lbEl ? lbEl.value.trim().toLowerCase() : '0';
        const ubStr = ubEl ? ubEl.value.trim().toLowerCase() : '';

        // Нижняя граница
        let lb = null;
        if (lbStr === '' || lbStr === '0') {
            lb = 0;
        } else if (lbStr === '-inf' || lbStr === '-infinity') {
            lb = null; // свободная снизу
            hasCustomBounds = true;
        } else {
            const lbNum = parseFloat(lbStr);
            if (!Number.isFinite(lbNum)) {
                if (lbEl) lbEl.classList.add('input-invalid');
                missing.push(`нижняя граница x_${j+1} («${lbStr}»)`);
                boundsInvalid = true;
            } else {
                lb = lbStr;
                if (lbStr !== '0') hasCustomBounds = true;
            }
        }

        // Верхняя граница
        let ub = null;
        if (ubStr === '' || ubStr === 'inf' || ubStr === '+inf' || ubStr === 'infinity') {
            ub = null;
        } else {
            const ubNum = parseFloat(ubStr);
            if (!Number.isFinite(ubNum)) {
                if (ubEl) ubEl.classList.add('input-invalid');
                missing.push(`верхняя граница x_${j+1} («${ubStr}»)`);
                boundsInvalid = true;
            } else {
                ub = ubStr;
                hasCustomBounds = true;
            }
        }

        lower_bounds.push(lb);
        upper_bounds.push(ub);
    }

    if (missing.length > 0 || boundsInvalid) {
        errDiv.innerText = "Заполните все поля корректными числами. "
            + "Проблемные поля выделены красным: " + missing.join(", ") + ".";
        errDiv.classList.remove('hidden');
        return;
    }

    const problemData = {
        c, A, b, signs, is_max,
        canonical_mode: canonicalMode,
        detailed: document.getElementById('detailed-mode') ? document.getElementById('detailed-mode').checked : false,
    };

    // Передаём границы только если есть нестандартные
    if (hasCustomBounds) {
        problemData.lower_bounds = lower_bounds;
        problemData.upper_bounds = upper_bounds;
    }

    try {
        const resultHTML = await pywebview.api.solve(problemData);
        if (resultHTML && resultHTML.error) {
            errDiv.innerText = "Ошибка: " + resultHTML.error;
            errDiv.classList.remove('hidden');
            return;
        }

        document.getElementById('input-screen').classList.add('hidden');
        document.getElementById('result-screen').classList.remove('hidden');
        document.getElementById('export-controls').classList.remove('hidden');

        document.getElementById('solution-content').innerHTML = resultHTML;

        // Render math
        renderMath(document.getElementById('solution-content'));

    } catch (e) {
        errDiv.innerText = "Системная ошибка связи с Python";
        errDiv.classList.remove('hidden');
    }
}

async function saveHtml() {
    const detailed = document.getElementById('detailed-mode') ? document.getElementById('detailed-mode').checked : false;
    const hiddenSteps = Array.from(document.querySelectorAll('.step-visibility-toggle:not(:checked)')).map(el => parseInt(el.dataset.step));

    try {
        const result = await pywebview.api.save_html(detailed, hiddenSteps);
        if (result && result.error) {
            alert("Ошибка сохранения: " + result.error);
        } else if (result && result.success) {
            alert("HTML сохранён. Откройте файл в браузере и нажмите Ctrl+P → «Сохранить как PDF».");
        }
    } catch (e) {
        alert("Ошибка при сохранении HTML: " + e);
    }
}

async function saveMarkdown() {
    const detailed = document.getElementById('detailed-mode') ? document.getElementById('detailed-mode').checked : false;
    const hiddenSteps = Array.from(document.querySelectorAll('.step-visibility-toggle:not(:checked)')).map(el => parseInt(el.dataset.step));

    try {
        const result = await pywebview.api.save_markdown(detailed, hiddenSteps);
        if (result && result.error) {
            alert("Ошибка сохранения: " + result.error);
        } else if (result && result.success) {
            alert("Успешно сохранено!");
        }
    } catch (e) {
        alert("Ошибка при сохранении Markdown: " + e);
    }
}

function toggleStepVisibility(checkbox) {
    const stepId = checkbox.dataset.step;
    const card = document.getElementById(`step-card-${stepId}`);
    if (checkbox.checked) {
        card.classList.remove('no-print', 'opacity-60');
    } else {
        card.classList.add('no-print', 'opacity-60');
    }
}

function re_solve() {
    if (!document.getElementById('result-screen').classList.contains('hidden')) {
        solve();
    }
}

function resetApp() {
    document.getElementById('input-screen').classList.remove('hidden');
    document.getElementById('result-screen').classList.add('hidden');
    document.getElementById('export-controls').classList.add('hidden');
    document.getElementById('solution-content').innerHTML = '';
}

function updatePrintFontSize() {
    const size = document.getElementById('print-font-size').value;
    let style = document.getElementById('dynamic-print-style');
    if (!style) {
        style = document.createElement('style');
        style.id = 'dynamic-print-style';
        document.head.appendChild(style);
    }
    style.innerHTML = `@media print { html, body, #solution-content, .katex { font-size: ${size}px !important; } }`;
}

// Рендер LaTeX-формул в произвольном контейнере (общая утилита).
function renderMath(el) {
    if (!el || typeof renderMathInElement !== 'function') return;
    renderMathInElement(el, {
        delimiters: [
            {left: '$$', right: '$$', display: true},
            {left: '$',  right: '$',  display: false}
        ],
        throwOnError: false
    });
}

// Init form on load
window.onload = function () {
    buildForm();
    // Рендерим статические $...$ в форме ввода (чекбокс канонической формы,
    // подсказки про границы переменных и т.п.).
    renderMath(document.getElementById('input-screen'));
};
