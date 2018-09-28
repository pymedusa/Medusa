const isDevelopment = process.env.NODE_ENV === 'development';

/**
 * Calculate the combined value of the selected qualities.
 * @param {number[]} allowedQualities - Array of allowed qualities.
 * @param {number[]} preferredQualities - Array of preferred qualities.
 * @returns {number} - An unsigned integer.
 */
const combineQualities = (allowedQualities, preferredQualities) => {
    const reducer = (accumulator, currentValue) => accumulator | currentValue;
    const allowed = allowedQualities.reduce(reducer, 0);
    const preferred = preferredQualities.reduce(reducer, 0);

    return (allowed | (preferred << 16)) >>> 0; // Unsigned int
};

export {
    combineQualities,
    isDevelopment
};
