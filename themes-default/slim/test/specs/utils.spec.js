import {
    combineQualities,
    convertDateFormat
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
