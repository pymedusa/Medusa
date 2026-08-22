const historyTextWrappers = new Set(['\'', '"', '`']);
const historySizeMaxInput = 8589934591.99;

/**
 * Normalize Episode or Provider text, retaining matched wrappers for backend literal-space handling.
 * @param {string} value - Raw text input.
 * @returns {{filterValue: string, malformed: boolean, clearInput: boolean}} Normalized filter state.
 */
export const normalizeHistoryTextFilter = value => {
    const normalized = value.trim();
    const first = normalized[0];
    const last = normalized[normalized.length - 1];
    const hasFirstWrapper = historyTextWrappers.has(first);
    const hasLastWrapper = historyTextWrappers.has(last);

    if (!hasFirstWrapper && !hasLastWrapper) {
        return {
            filterValue: normalized,
            malformed: false,
            clearInput: false
        };
    }

    if (hasFirstWrapper && first === last && normalized.length >= 2) {
        const isEmptyPair = normalized.length === 2;
        return {
            filterValue: isEmptyPair ? '' : normalized,
            malformed: isEmptyPair,
            clearInput: false
        };
    }

    let cleaned = normalized;
    while (cleaned && historyTextWrappers.has(cleaned[0])) {
        cleaned = cleaned.slice(1);
    }
    while (cleaned && historyTextWrappers.has(cleaned[cleaned.length - 1])) {
        cleaned = cleaned.slice(0, -1);
    }
    cleaned = cleaned.trim();

    return {
        filterValue: cleaned,
        malformed: true,
        clearInput: false
    };
};

/**
 * Normalize a raw History Size input without changing the text shown while it is edited.
 * @param {string} value - Raw text input.
 * @returns {{filterValue: string, valid: boolean, clearFilter: boolean}} Normalized filter state.
 */
export const normalizeHistorySizeFilter = value => {
    if (typeof value !== 'string') {
        return {
            filterValue: '',
            valid: false,
            clearFilter: false
        };
    }

    const trimmed = value.trim();
    if (!trimmed) {
        return {
            filterValue: '',
            valid: false,
            clearFilter: true
        };
    }

    let normalized = trimmed;
    if (historyTextWrappers.has(normalized[0])) {
        if (normalized.length < 2 || normalized[normalized.length - 1] !== normalized[0]) {
            return {
                filterValue: '',
                valid: false,
                clearFilter: false
            };
        }
        normalized = normalized.slice(1, -1).trim();
    }

    if (!normalized) {
        return {
            filterValue: '',
            valid: false,
            clearFilter: true
        };
    }

    const match = normalized.match(/^([<>])\s*(\d{1,10}(?:\.\d{1,2})?)(?:\s*(mb|gb))?$/i);
    if (!match || Number(match[2]) > historySizeMaxInput) {
        return {
            filterValue: '',
            valid: false,
            clearFilter: false
        };
    }

    const unit = match[3] ? ` ${match[3].toUpperCase()}` : '';
    return {
        filterValue: `${match[1]} ${match[2]}${unit}`,
        valid: true,
        clearFilter: false
    };
};
