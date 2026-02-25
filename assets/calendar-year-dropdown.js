/**
 * Substitui o stepper de ano do DatePickerRange por um dropdown <select>.
 * Modifica o input nativo do ano e dispara eventos React para atualizar.
 */
(function () {
    const MIN_YEAR = 2020;
    const MAX_YEAR = 2030;
    const CONTROLS_SELECTORS = [
        '.dash-datepicker-controls',
        '.DatePicker_caption',
        '.CalendarMonth_caption',
    ];

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

    function closestCalendarRoot(node) {
        if (!node) return null;
        return node.closest(
            '.dash-datepicker-calendar-wrapper, .DateRangePicker_picker, .SingleDatePicker_picker, .DayPicker, [class*="datepicker"]'
        );
    }

    function getYearInput(controls) {
        // Dash antigo: stepper embutido em .dash-input
        var dashInput = controls.querySelector('.dash-input');
        if (dashInput) {
            var dashInputElement = dashInput.querySelector('.dash-input-element');
            if (dashInputElement) return dashInputElement;
        }

        // Dash/react-datepicker novo: procurar input numérico de ano no popup atual
        var root = closestCalendarRoot(controls);
        if (root) {
            var candidates = root.querySelectorAll('input');
            for (var i = 0; i < candidates.length; i++) {
                var input = candidates[i];
                var hint = (
                    (input.getAttribute('aria-label') || '') + ' ' +
                    (input.getAttribute('placeholder') || '') + ' ' +
                    (input.getAttribute('name') || '')
                ).toLowerCase();
                if (input.type === 'number' || /year|ano/.test(hint)) {
                    return input;
                }
            }
        }
        return null;
    }

    function getCurrentYear(controls) {
        var input = getYearInput(controls);
        if (input && input.value) {
            return parseInt(input.value);
        }
        // Fallback: ler do header
        var wrapper = closestCalendarRoot(controls);
        if (wrapper) {
            var header = wrapper.querySelector(
                '.dash-datepicker-calendar-month-header, .DatePicker_caption, .CalendarMonth_caption, [class*="month"][class*="header"], [class*="caption"]'
            );
            if (header) {
                var match = (header.textContent || '').match(/(\d{4})/);
                if (match) return parseInt(match[1]);
            }
            var anyMatch = (wrapper.textContent || '').match(/\b(20\d{2}|19\d{2})\b/);
            if (anyMatch) return parseInt(anyMatch[1]);
        }
        return new Date().getFullYear();
    }

    function getNavButtons(controls) {
        var localButtons = controls.querySelectorAll(
            '.dash-datepicker-month-nav, .DayPickerNavigation_button, button'
        );
        if (localButtons.length) return Array.from(localButtons);
        var root = closestCalendarRoot(controls);
        if (!root) return [];
        return Array.from(root.querySelectorAll('.DayPickerNavigation_button, button'));
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

        // Inserir antes do último botão de navegação (→), suportando layouts antigos/novos
        var navButtons = getNavButtons(controls);
        if (navButtons.length >= 2) {
            var rightButton = navButtons[navButtons.length - 1];
            if (rightButton.parentNode === controls) {
                controls.insertBefore(select, rightButton);
            } else if (rightButton.parentNode) {
                rightButton.parentNode.insertBefore(select, rightButton);
            } else {
                controls.appendChild(select);
            }
        } else {
            controls.appendChild(select);
        }
    }

    function listControls() {
        var all = [];
        CONTROLS_SELECTORS.forEach(function (sel) {
            document.querySelectorAll(sel).forEach(function (node) {
                if (all.indexOf(node) === -1) all.push(node);
            });
        });
        return all;
    }

    function hasOpenCalendar() {
        return !!document.querySelector(
            '.dash-datepicker-calendar-wrapper, .DateRangePicker_picker, .SingleDatePicker_picker, .DayPicker'
        );
    }

    function syncDropdowns() {
        listControls().forEach(function (controls) {
            var select = controls.querySelector('.year-select-custom');
            if (select) {
                var year = getCurrentYear(controls);
                if (parseInt(select.value) !== year) {
                    select.value = year;
                }
            }
        });
    }

    var syncTimer = null;
    var observer = new MutationObserver(function (mutations) {
        // Evita trabalho pesado quando o calendário não está aberto.
        if (!hasOpenCalendar()) return;

        // Ignora mutações causadas apenas pelo próprio dropdown customizado.
        var relevant = false;
        for (var i = 0; i < mutations.length; i++) {
            var m = mutations[i];
            if (m.target && m.target.closest && m.target.closest('.year-select-custom')) {
                continue;
            }
            relevant = true;
            break;
        }
        if (!relevant) return;

        if (syncTimer) {
            clearTimeout(syncTimer);
        }
        syncTimer = setTimeout(function () {
            listControls().forEach(function (controls) {
                createYearSelect(controls);
            });
            syncDropdowns();
            syncTimer = null;
        }, 80);
    });

    observer.observe(document.body, { childList: true, subtree: true });
})();
