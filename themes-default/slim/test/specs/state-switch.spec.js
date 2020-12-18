/* eslint jest/expect-expect: ["error", { "assertFunctionNames": ["expect", "stateTestCase"] }] */
import { createLocalVue } from '@vue/test-utils';
import { StateSwitch } from '../../src/components';
import { generatePropTest } from '../helpers/generators';

describe('StateSwitch.test.js', () => {
    let localVue;
    const store = {};

    beforeEach(() => {
        localVue = createLocalVue();
    });

    const stateTestCase = generatePropTest(StateSwitch);

    it('renders', () => {
        stateTestCase(localVue, store, 'loading with `null`', {
            state: null
        });

        stateTestCase(localVue, store, 'loading with string', {
            state: 'loading'
        });

        stateTestCase(localVue, store, 'loading with `theme` prop', {
            theme: 'light',
            state: 'loading'
        });

        stateTestCase(localVue, store, 'yes with `true`', {
            state: true
        });

        stateTestCase(localVue, store, 'yes with string', {
            state: 'yes'
        });

        stateTestCase(localVue, store, 'no with `false`', {
            state: false
        });

        stateTestCase(localVue, store, 'no with string', {
            state: 'no'
        });
    });
});
