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

/**
 * Return a human readable representation of the provided size.
 * @param {number} bytes - The size in bytes to convert
 * @param {boolean} [useDecimal=false] - Use decimal instead of binary prefixes (e.g. kilo = 1000 instead of 1024)
 * @returns {string} The converted size.
 */
const humanFileSize = (bytes, useDecimal = false) => {
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
const mapDateFormat = dateFormatString => {
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
const arrayUnique = array => {
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
const arrayExclude = (baseArray, exclude) => {
    let newArray = [];
    for (let i=0; i < baseArray.length; i++) {
        if (!exclude.includes(baseArray[i])) {
            newArray.push(baseArray[i]);
        }
    }
    return newArray;
}

export {
    combineQualities,
    humanFileSize,
    mapDateFormat,
    isDevelopment,
    arrayUnique,
    arrayExclude
};
