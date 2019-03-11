import { combineQualities } from '../../src/utils';

describe('combineQualities.test.js', () => {
    const testCases = [
        /* C0 */ { allowed: [1, 2, 4], preferred: [], expected: 7 },
        /* C1 */ { allowed: [1], preferred: [2, 4], expected: 393217 },
        /* C2 */ { allowed: [32768], preferred: [32768], expected: 2147516416 }
    ];

    testCases.forEach(({ allowed, preferred, expected }, caseIndex) => {
        const testTitle = `[C${caseIndex}] combineQualities(${JSON.stringify(allowed)}, ${JSON.stringify(preferred)})`;
        it(testTitle, () => {
            const actual = combineQualities(allowed, preferred);
            expect(actual).toEqual(expected);
        });
    });
});
