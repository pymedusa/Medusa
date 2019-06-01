export const isDevelopment = process.env.NODE_ENV === 'development';

/**
 * Calculate the combined value of the selected qualities.
 * @param {number[]} allowedQualities - Array of allowed qualities.
 * @param {number[]} [preferredQualities=[]] - Array of preferred qualities.
 * @returns {number} An unsigned integer.
 */
export const combineQualities = (allowedQualities, preferredQualities = []) => {
    const reducer = (accumulator, currentValue) => accumulator | currentValue;
    const allowed = allowedQualities.reduce(reducer, 0);
    const preferred = preferredQualities.reduce(reducer, 0);

    return (allowed | (preferred << 16)) >>> 0; // Unsigned int
};

/**
 * Return a human readable representation of the provided size.
 * @param {number} bytes - The size in bytes to convert
 * @param {boolean} [useDecimal=false] - Use decimal instead of binary prefixes (e.g. kilo = 1000 instead of 1024)
 * @returns {string} The converted size.
 */
export const humanFileSize = (bytes, useDecimal = false) => {
    if (bytes === undefined) {
        return;
    }

    const thresh = useDecimal ? 1000 : 1024;
    if (Math.abs(bytes) < thresh) {
        return bytes + ' B';
    }
    const units = ['KB', 'MB', 'GB', 'TB', 'PB'];
    let u = -1;
    do {
        bytes /= thresh;
        ++u;
    } while (Math.abs(bytes) >= thresh && u < units.length - 1);

    return `${bytes.toFixed(2)} ${units[u]}`;
};


/**
 * Map dateformat of pythons datetime.strftime() to that of javascripts dateFns.
 * @param {String} dateFormatString - pythons strftime format
 * @returns {String} mapped format that can be used by dateFns
 */
export const mapDateFormat = dateFormatString => {
    const dateMap = new Map(
        [
            ['%a', 'ddd'],
            ['%A', 'dddd'],
            ['%w', 'E'],
            ['%d', 'DD'],
            ['%-d', 'DD'],
            ['%b', 'MMM'],
            ['%B', 'MMMM'],
            ['%m', 'MM'],
            ['%-m', 'M'],
            ['%y', 'YY'],
            ['%Y', 'YYYY'],
            ['%H', 'HH'],
            ['%-H', 'H'],
            ['%I', 'hh'],
            ['%-I', 'h'],
            ['%p', 'A'],
            ['%M', 'mm'],
            ['%-M', 'm'],
            ['%S', 'ss'],
            ['%-S', 's']
        ]
    );

    dateMap.forEach((value, key, _) => {
        dateFormatString = dateFormatString.replace(key, value);
    })

    return dateFormatString;
}

/**
 * Create an array with unique strings
 * @param {Array} array - array with strings
 * @returns {Array} array with unique strings
 */
export const arrayUnique = array => {
    var a = array.concat();
    for (let i=0; i < a.length; ++i) {
        for (let j = i + 1; j < a.length; ++j) {
            if (a[i] === a[j]) {
                a.splice(j--, 1);
            }
        }
    }
    return a;
}

/**
 * Exclude strings out of the array `exclude` compared to the strings in the array baseArray.
 * @param {Array} baseArray - array of strings
 * @param {Array} eclude - array of strings which we want to exclude in baseArray
 * @returns {Array} reduced array
 */
export const arrayExclude = (baseArray, exclude) => {
    let newArray = [];
    for (let i=0; i < baseArray.length; i++) {
        if (!exclude.includes(baseArray[i])) {
            newArray.push(baseArray[i]);
        }
    }
    return newArray;
}

/**
 * A simple wait function.
 * @param {number} ms - Time to wait.
 * @returns {Promise<number>} Resolves when done waiting.
 */
export const wait = /* istanbul ignore next */ ms => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Returns when `check` evaluates as truthy.
 * @param {function} check - Function to evaluate every poll interval.
 * @param {number} [poll=100] - Interval to check, in milliseconds.
 * @param {number} [timeout=3000] - Timeout to stop waiting after, in milliseconds.
 * @returns {Promise<number>} The approximate amount of time waited, in milliseconds.
 * @throws Will throw an error when the timeout has been exceeded.
 */
export const waitFor = /* istanbul ignore next */ async (check, poll = 100, timeout = 3000) => {
    let ms = 0;
    while (!check()) {
        await wait(poll); // eslint-disable-line no-await-in-loop
        ms += poll;
        if (ms > timeout) {
            throw new Error(`waitFor timed out (${timeout}ms)`);
        }
    }
    return ms;
};
