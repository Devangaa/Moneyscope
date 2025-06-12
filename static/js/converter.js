const currencyFromSelect = document.getElementById('currencyFrom');
const amountFromInput = document.getElementById('amountFrom');
const currencyToInput = document.getElementById('currencyTo');
const amountToInput = document.getElementById('amountTo');
const swapBtn = document.getElementById('swapBtn');

let swapped = false; // false = left: foreign currency, right: IDR

function setupDefaultMode() {
    const currencyFromSelect = document.getElementById('currencyFrom');
    const amountFromInput = document.getElementById('amountFrom');
    const amountToInput = document.getElementById('amountTo');

    function convert() {
        let fromPrice = parseFloat(currencyFromSelect.value);
        let amount = parseFloat(amountFromInput.value) || 0;
        amountToInput.value = (amount * fromPrice).toLocaleString('id-ID', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }

    amountFromInput.addEventListener('input', convert);
    currencyFromSelect.addEventListener('change', convert);
    convert();
}

function setupSwappedMode() {
    const amountFromInput = document.getElementById('amountFromInput');
    const currencyToSelect = document.getElementById('currencyToSelect');
    const amountToInput = document.getElementById('amountTo');

    function convert() {
        let amount = parseFloat(amountFromInput.value) || 0;
        let toPrice = parseFloat(currencyToSelect.value);
        amountToInput.value = (amount / toPrice).toLocaleString('id-ID', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }

    amountFromInput.addEventListener('input', convert);
    currencyToSelect.addEventListener('change', convert);
    convert();
}

function renderDefaultMode() {
    document.getElementById('left-side').innerHTML = `
    <label for="currencyFrom" class="form-label fw-bold">Mata Uang Konversi</label>
    <select id="currencyFrom" class="form-select mb-2">
        ${currencies.map(c => `<option value="${c.price}">${c.code.split('_')[0]}</option>`).join('')}
    </select>
    <input type="number" id="amountFrom" class="form-control" step="0.01" value="1" min="0" />
    `;
    document.getElementById('right-side').innerHTML = `
    <label for="currencyTo" class="form-label fw-bold">Mata Uang Hasil</label>
    <input type="text" class="form-control mb-2" id="currencyTo" value="IDR" disabled />
    <input type="text" class="form-control" id="amountTo" disabled />
    `;
    setupDefaultMode();
}

function renderSwappedMode() {
    document.getElementById('left-side').innerHTML = `
    <label for="amountFromInput" class="form-label fw-bold">Mata Uang Konversi</label>
    <input type="text" class="form-control mb-2" id="amountFrom" value="IDR" disabled />
    <input type="number" id="amountFromInput" class="form-control" step="0.01" value="1" min="0" />
    `;
    document.getElementById('right-side').innerHTML = `
    <label for="currencyToSelect" class="form-label fw-bold">Mata Uang Hasil</label>
    <select id="currencyToSelect" class="form-select mb-2">
        ${currencies.map(c => `<option value="${c.price}">${c.code.split('_')[0]}</option>`).join('')}
    </select>
    <input type="text" class="form-control" id="amountTo" disabled />
    `;
    setupSwappedMode();
}

renderDefaultMode();

swapBtn.addEventListener('click', () => {
    swapped = !swapped;
    if (swapped) {
        renderSwappedMode();
    } else {
        renderDefaultMode();
    }
});

