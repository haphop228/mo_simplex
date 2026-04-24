let currentProblemData = null;

function buildForm() {
    const numVars = parseInt(document.getElementById('num-vars').value) || 2;
    const numConstraints = parseInt(document.getElementById('num-constraints').value) || 3;

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

        const signSelect = document.createElement('select');
        signSelect.className = `constr-sign constr-sign-${i} border border-gray-300 rounded px-2 py-1 bg-white focus:ring-2 focus:ring-indigo-500 outline-none ml-2`;
        signSelect.innerHTML = `
            <option value="<=">&le;</option>
            <option value=">=">&ge;</option>
            <option value="=">=</option>
        `;
        row.appendChild(signSelect);

        const bInput = document.createElement('input');
        bInput.type = 'number';
        bInput.className = `constr-b constr-b-${i} border border-gray-300 rounded px-2 py-1 w-20 text-center focus:ring-2 focus:ring-indigo-500 outline-none ml-2`;
        bInput.value = '10';
        row.appendChild(bInput);

        constrContainer.appendChild(row);
    }
}

async function solve() {
    const errDiv = document.getElementById('error-message');
    errDiv.classList.add('hidden');
    errDiv.innerText = '';

    const numVars = parseInt(document.getElementById('num-vars').value) || 2;
    const numConstraints = parseInt(document.getElementById('num-constraints').value) || 3;

    const c = Array.from(document.querySelectorAll('.obj-coeff')).map(el => parseFloat(el.value));
    const is_max = document.getElementById('obj-target').value === 'max';

    const A = [];
    const b = [];
    const signs = [];

    for (let i = 0; i < numConstraints; i++) {
        const row = Array.from(document.querySelectorAll(`.constr-${i}`)).map(el => parseFloat(el.value));
        A.push(row);
        b.push(parseFloat(document.querySelector(`.constr-b-${i}`).value));
        signs.push(document.querySelector(`.constr-sign-${i}`).value);
    }

    const problemData = { 
        c, A, b, signs, is_max,
        detailed: document.getElementById('detailed-mode') ? document.getElementById('detailed-mode').checked : false
    };

    try {
        const resultHTML = await pywebview.api.solve(problemData);
        if (resultHTML.error) {
            errDiv.innerText = "Ошибка: " + resultHTML.error;
            errDiv.classList.remove('hidden');
            return;
        }

        document.getElementById('input-screen').classList.add('hidden');
        document.getElementById('result-screen').classList.remove('hidden');
        document.getElementById('export-controls').classList.remove('hidden');
        
        document.getElementById('solution-content').innerHTML = resultHTML;
        
        // Render math
        renderMathInElement(document.getElementById('solution-content'), {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false}
            ],
            throwOnError: false
        });

    } catch (e) {
        errDiv.innerText = "Системная ошибка связи с Python";
        errDiv.classList.remove('hidden');
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

// Init form on load
window.onload = buildForm;
