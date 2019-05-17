import {
    combineQualities,
    convertDateFormat,
    humanFileSize
} from '../../src/utils/core';

describe('combineQualities', () => {
    const testCases = [
        /* C0 */ { allowed: [1, 2, 4], preferred: [], expected: 7 },
        /* C1 */ { allowed: [1], preferred: [2, 4], expected: 393217 },
        /* C2 */ { allowed: [32768], preferred: [32768], expected: 2147516416 },
        /* C3 */ { allowed: [1, 2, 4], preferred: undefined, expected: 7 }
    ];

    testCases.forEach(({ allowed, preferred, expected }, caseIndex) => {
        const testTitle = `[C${caseIndex}] combineQualities(${JSON.stringify(allowed)}, ${JSON.stringify(preferred)})`;
        it(testTitle, () => {
            const actual = combineQualities(allowed, preferred);
            expect(actual).toEqual(expected);
        });
    });
});

describe('convertDateFormat', () => {
    it('converts simple Python date format', () => {
        expect(convertDateFormat('%Y-%m-%d %H:%M:%S')).toEqual('yyyy-MM-dd HH:mm:ss');
    });

    it('escapes non-token characters', () => {
        expect(convertDateFormat("It's%% %Y-%m-%d %H:%M:%S t2 100%% hello")).toEqual("'It''s'% yyyy-MM-dd HH:mm:ss 't'2 100% 'hello'");
    });

    it('throws error when invalid tokens are found', () => {
        expect(() => convertDateFormat('%u')).toThrow('Unrecognized token');
        expect(() => convertDateFormat('%d %')).toThrow('Single % at end of format string');
    });
});

describe('humanFileSize returns correct values', () => {
    const KiB = 2 ** 10; // Kibibyte
    const MiB = 2 ** 20; // Mebibyte
    const GiB = 2 ** 30; // Gibibyte
    const TiB = 2 ** 40; // Tebibyte
    const PiB = 2 ** 50; // Pebibyte
    const EiB = 2 ** 60; // Exbibyte
    const testCases = [
        /* C0 */ { value: null, expected: '0.00 B' },
        /* C1 */ { value: '', expected: '0.00 B' },
        /* C2 */ { value: '1024', expected: '1.00 KB' },
        /* C3 */ { value: '1024.5', expected: '1.00 KB' },
        /* C4 */ { value: -42.5, expected: '0.00 B' },
        /* C5 */ { value: -42, expected: '0.00 B' },
        /* C6 */ { value: 0, expected: '0.00 B' },
        /* C7 */ { value: 25, expected: '25.00 B' },
        /* C8 */ { value: 25.5, expected: '25.50 B' },
        /* C9 */ { value: KiB, expected: '1.00 KB' },
        /* C10 */ { value: (50 * KiB) + 25, expected: '50.02 KB' },
        /* C11 */ { value: MiB, expected: '1.00 MB' },
        /* C12 */ { value: (100 * MiB) + (50 * KiB) + 25, expected: '100.05 MB' },
        /* C13 */ { value: GiB, expected: '1.00 GB' },
        /* C14 */ { value: (200 * GiB) + (100 * MiB) + (50 * KiB) + 25, expected: '200.10 GB' },
        /* C15 */ { value: TiB, expected: '1.00 TB' },
        /* C16 */ { value: (400 * TiB) + (200 * GiB) + (100 * MiB) + (50 * KiB) + 25, expected: '400.20 TB' },
        /* C17 */ { value: PiB, expected: '1.00 PB' },
        /* C18 */ { value: (800 * PiB) + (400 * TiB) + (200 * GiB) + (100 * MiB) + (50 * KiB) + 25, expected: '800.39 PB' },
        /* C19 */ { value: EiB, expected: '1024.00 PB' }
    ];

    testCases.forEach(({ value, expected }, caseIndex) => {
        const testTitle = `[C${caseIndex}] humanFileSize(${String(value)})`;
        it(testTitle, () => {
            const actual = humanFileSize(value);
            expect(actual).toEqual(expected);
        });
    });

    it('applies `useDecimal` option', () => {
        const actual = humanFileSize((100 * MiB) + (50 * KiB) + 25, true);
        expect(actual).toEqual('104.91 MB');
    });
});
