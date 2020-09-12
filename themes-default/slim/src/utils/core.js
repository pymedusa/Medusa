export const isDevelopment = process.env.NODE_ENV === 'development';

/**
 * Calculate the combined value of the selected qualities.
 * @param {number[]} allowedQualities - Array of allowed qualities.
 * @param {number[]} [preferredQualities=[]] - Array of preferred qualities.
 * @returns {number} An unsigned integer.
 */
export const combineQualities = (allowedQualities, preferredQualities = []) => {
    const reducer = (accumulator, currentValue) => accumulator | currentValue;
    const allowed = allowedQualities.reduce((a, c) => reducer(a, c), 0);
    const preferred = preferredQualities.reduce((a, c) => reducer(a, c), 0);

    return (allowed | (preferred << 16)) >>> 0; // Unsigned int
};

/**
 * Return a human readable representation of the provided size.
 * @param {number} bytes - The size in bytes to convert
 * @param {boolean} [useDecimal=false] - Use decimal instead of binary prefixes (e.g. kilo = 1000 instead of 1024)
 * @returns {string} The converted size.
 */
export const humanFileSize = (bytes, useDecimal = false) => {
    if (!bytes) {
        bytes = 0;
    }

    bytes = Math.max(bytes, 0);

    const thresh = useDecimal ? 1000 : 1024;
    if (Math.abs(bytes) < thresh) {
        return bytes.toFixed(2) + ' B';
    }
    const units = ['KB', 'MB', 'GB', 'TB', 'PB'];
    let u = -1;
    do {
        bytes /= thresh;
        ++u;
    } while (Math.abs(bytes) >= thresh && u < units.length - 1);

    return `${bytes.toFixed(2)} ${units[u]}`;
};

// Maps Python date/time tokens to date-fns tokens
// Python: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
// date-fns: https://date-fns.org/v2.0.0-alpha.27/docs/format
const datePresetMap = {
    '%a': 'ccc', // Weekday name, short
    '%A': 'cccc', // Weekday name, full
    '%w': 'c', // Weekday number
    '%d': 'dd', // Day of the month, zero-padded
    '%b': 'LLL', // Month name, short
    '%B': 'LLLL', // Month name, full
    '%m': 'MM', // Month number, zero-padded
    '%y': 'yy', // Year without century, zero-padded
    '%Y': 'yyyy', // Year with century
    '%H': 'HH', // Hour (24-hour clock), zero-padded
    '%I': 'hh', // Hour (12-hour clock), zero-padded
    '%p': 'a', // AM / PM
    '%M': 'mm', // Minute, zero-padded
    '%S': 'ss', // Second, zero-padded
    '%f': 'SSSSSS', // Microsecond, zero-padded
    '%z': 'xx', // UTC offset in the form +HHMM or -HHMM
    // '%Z': '', // [UNSUPPORTED] Time zone name
    '%j': 'DDD', // Day of the year, zero-padded
    '%U': 'II', // Week number of the year (Sunday as the first day of the week), zero padded
    '%W': 'ww', // Week number of the year (Monday as the first day of the week)
    '%c': 'Pp', // Locale's appropriate date and time representation
    '%x': 'P', // Locale's appropriate date representation
    '%X': 'p', // Locale's appropriate time representation
    '%%': '%' // Literal '%' character
};

/**
 * Convert a Python date format to a DateFns compatible date format.
 * Automatically escapes non-token characters.
 * @param {string} format - The Python date format.
 * @returns {string} The new format.
 */
export const convertDateFormat = format => {
    let newFormat = '';
    let index = 0;
    let escaping = false;
    while (index < format.length) {
        const chr = format.charAt(index);
        // Escape single quotes
        if (chr === "'") {
            newFormat += chr + chr;
        } else if (chr === '%') {
            if (escaping) {
                escaping = false;
                newFormat += "'";
            }

            ++index;
            if (index === format.length) {
                throw new Error(`Single % at end of format string: ${format}`);
            }
            const chr2 = format.charAt(index);
            const tokenKey = chr + chr2;
            const token = datePresetMap[tokenKey];
            if (token === undefined) {
                throw new Error(`Unrecognized token "${tokenKey}" in format string: ${format}`);
            }
            newFormat += token;
        // Only letters need to escaped
        } else if (/[^a-z]/i.test(chr)) {
            if (escaping) {
                escaping = false;
                newFormat += "'";
            }
            newFormat += chr;
        // Escape anything else
        } else {
            if (!escaping) {
                escaping = true;
                newFormat += "'";
            }
            newFormat += chr;
        }

        ++index;

        if (index === format.length && escaping) {
            newFormat += "'";
        }
    }
    return newFormat;
};

/**
 * Create an array with unique strings
 * @param {string[]} array - array with strings
 * @returns {string[]} array with unique strings
 */
export const arrayUnique = array => {
    return array.reduce((result, item) => {
        return result.includes(item) ? result : result.concat(item);
    }, []);
};

/**
 * Exclude strings out of the array `exclude` compared to the strings in the array baseArray.
 * @param {string[]} baseArray - array of strings
 * @param {string[]} exclude - array of strings which we want to exclude in baseArray
 * @returns {string[]} reduced array
 */
export const arrayExclude = (baseArray, exclude) => {
    return baseArray.filter(item => !exclude.includes(item));
};

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

/**
 * Transform a season and episode number to an episode slug.
 * If the episode number is not provided, return a season slug.
 * @param {number} season - Season number.
 * @param {number} episode - Episode number.
 * @returns {string} Episode or Season slug.
 */
export const episodeToSlug = (season, episode) => {
    if (episode) {
        return `s${season.toString().padStart(2, '0')}e${episode.toString().padStart(2, '0')}`;
    }
    return `s${season.toString().padStart(2, '0')}`;
};

/**
 * Force reload.
 * Force a reload of the page and ignore local cache.
 * window.location.reload(true) doesn't seem to work on chrome. But the self assign does.
*/
export const forceBrowserReload = () => {
    if (Boolean(window.chrome) && Boolean(window.chrome.webstore)) {
        window.location.href = window.location.href; // eslint-disable-line no-self-assign
    } else {
        window.location.reload(true);
    }
};
