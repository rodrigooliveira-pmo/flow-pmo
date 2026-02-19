/**
 * Substitui o stepper de ano do DatePickerRange por um dropdown <select>.
 * Modifica o input nativo do ano e dispara eventos React para atualizar.
 */
(function () {
    const MIN_YEAR = 2020;
    const MAX_YEAR = 2030;

    // Setter nativo do input para contornar o override do React
    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype, 'value'
    ).set;

    function setReactInputValue(input, value) {
        nativeInputValueSetter.call(input, value);
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        // Simular blur para confirmar o valor
        input.dispatchEvent(new Event('blur', { bubbles: true }));
    }

    function getYearInput(controls) {
        // O input do ano é o .dash-input-element dentro de .dash-input
        var dashInput = controls.querySelector('.dash-input');
        if (dashInput) {
            return dashInput.querySelector('.dash-input-element');
        }
        return null;
    }

    function getCurrentYear(controls) {
        var input = getYearInput(controls);
        if (input && input.value) {
            return parseInt(input.value);
        }
        // Fallback: ler do header
        var wrapper = controls.closest('.dash-datepicker-calendar-wrapper');
        if (wrapper) {
            var header = wrapper.querySelector('.dash-datepicker-calendar-month-header');
            if (header) {
                var match = header.textContent.match(/(\d{4})/);
                if (match) return parseInt(match[1]);
            }
        }
        return new Date().getFullYear();
    }

    function createYearSelect(controls) {
        if (controls.querySelector('.year-select-custom')) return;

        var currentYear = getCurrentYear(controls);
        var select = document.createElement('select');
        select.className = 'year-select-custom';

        for (var y = MIN_YEAR; y <= MAX_YEAR; y++) {
            var opt = document.createElement('option');
            opt.value = y;
            opt.textContent = y;
            if (y === currentYear) opt.selected = true;
            select.appendChild(opt);
        }

        select.addEventListener('change', function () {
            var newYear = parseInt(this.value);
            var yearInput = getYearInput(controls);

            if (yearInput) {
                // Dar foco, mudar valor, e disparar eventos React
                yearInput.focus();
                setReactInputValue(yearInput, String(newYear));
            }
        });

        // Inserir antes do último botão de navegação (→)
        var navButtons = controls.querySelectorAll('.dash-datepicker-month-nav');
        if (navButtons.length >= 2) {
            controls.insertBefore(select, navButtons[navButtons.length - 1]);
        } else {
            controls.appendChild(select);
        }
    }

    function syncDropdowns() {
        document.querySelectorAll('.dash-datepicker-controls').forEach(function (controls) {
            var select = controls.querySelector('.year-select-custom');
            if (select) {
                var year = getCurrentYear(controls);
                if (parseInt(select.value) !== year) {
                    select.value = year;
                }
            }
        });
    }

    var observer = new MutationObserver(function () {
        var controlsList = document.querySelectorAll('.dash-datepicker-controls');
        controlsList.forEach(function (controls) {
            createYearSelect(controls);
        });
        // Sincronizar valor do dropdown com o ano atual após re-render
        setTimeout(syncDropdowns, 150);
    });

    observer.observe(document.body, { childList: true, subtree: true });
})();
