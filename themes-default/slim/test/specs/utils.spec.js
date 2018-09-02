import test from 'ava';
import { combineQualities } from '../../src/utils';

const testCases = [
    /* C0 */ { allowed: [1, 2, 4], preferred: [], expected: 7 },
    /* C1 */ { allowed: [1], preferred: [2, 4], expected: 393217 },
    /* C2 */ { allowed: [32768], preferred: [32768], expected: 2147516416 }
];
testCases.forEach(({ allowed, preferred, expected }, caseIndex) => {
    const testTitle = `[C${caseIndex}] combineQualities(${JSON.stringify(allowed)}, ${JSON.stringify(preferred)})`;
    test(testTitle, t => {
        const actual = combineQualities(allowed, preferred);
        t.is(actual, expected);
    });
});
