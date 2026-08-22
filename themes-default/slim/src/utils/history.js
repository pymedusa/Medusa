const historyTextWrappers = new Set(['\'', '"', '`']);

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
            malformed: false,
            clearInput: isEmptyPair
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
