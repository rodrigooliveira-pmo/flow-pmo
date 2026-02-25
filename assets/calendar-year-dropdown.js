/**
 * Substitui o stepper de ano do DatePickerRange por um dropdown <select>.
 * Modifica o input nativo do ano e dispara eventos React para atualizar.
 */
(function () {
    const MIN_YEAR = 2020;
    const MAX_YEAR = 2030;
    const LEGACY_CONTROLS_SELECTOR = '.dash-datepicker-controls';
    const MODERN_PICKER_ROOTS_SELECTOR = '.DateRangePicker_picker, .SingleDatePicker_picker, .DayPicker';

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

        document.querySelectorAll(LEGACY_CONTROLS_SELECTOR).forEach(function (node) {
            if (all.indexOf(node) === -1) all.push(node);
        });

        // React-dates/Dash moderno pode renderizar vários meses (incluindo buffers ocultos).
        // Seleciona apenas captions visíveis e limita a quantidade por calendário aberto.
        document.querySelectorAll(MODERN_PICKER_ROOTS_SELECTOR).forEach(function (root) {
            var rootRect = root.getBoundingClientRect ? root.getBoundingClientRect() : null;
            var visibleCaptions = Array.from(
                root.querySelectorAll('.CalendarMonth_caption, .DatePicker_caption')
            ).filter(function (node) {
                if (!node) return false;
                var style = window.getComputedStyle ? window.getComputedStyle(node) : null;
                if (style && (style.display === 'none' || style.visibility === 'hidden')) {
                    return false;
                }
                var rect = node.getBoundingClientRect ? node.getBoundingClientRect() : null;
                if (!rect || rect.width <= 0 || rect.height <= 0) return false;
                // Só usa captions na faixa superior do popup (cabeçalho visível do mês).
                if (rootRect && rect.top - rootRect.top > 90) return false;
                return true;
            });

            // Mantém só os primeiros cabeçalhos visíveis (DatePickerRange geralmente mostra 1 ou 2).
            visibleCaptions.slice(0, 2).forEach(function (node) {
                if (all.indexOf(node) === -1) all.push(node);
            });
        });

        return all;
    }

    function cleanupDuplicateYearSelects() {
        document.querySelectorAll(MODERN_PICKER_ROOTS_SELECTOR).forEach(function (root) {
            var keep = new Set();
            listControls().forEach(function (ctrl) {
                if (root.contains(ctrl)) keep.add(ctrl);
            });
            root.querySelectorAll('.year-select-custom').forEach(function (sel) {
                var parent = sel.parentElement;
                if (!parent || !keep.has(parent)) {
                    sel.remove();
                }
            });
        });
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
            cleanupDuplicateYearSelects();
            listControls().forEach(function (controls) {
                createYearSelect(controls);
            });
            syncDropdowns();
            syncTimer = null;
        }, 80);
    });

    observer.observe(document.body, { childList: true, subtree: true });
})();
