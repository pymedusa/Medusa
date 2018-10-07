import test from 'ava';
import { createLocalVue } from '@vue/test-utils';
import { StateSwitch } from '../../src/components';
import { generatePropTest } from '../helpers/generators';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
});

const stateTestCase = generatePropTest(StateSwitch);

test('renders', t => {
    stateTestCase(t, 'loading with `null`', {
        state: null
    });

    stateTestCase(t, 'loading with string', {
        state: 'loading'
    });

    stateTestCase(t, 'loading with `theme` prop', {
        theme: 'light',
        state: 'loading'
    });

    stateTestCase(t, 'yes with `true`', {
        state: true
    });

    stateTestCase(t, 'yes with string', {
        state: 'yes'
    });

    stateTestCase(t, 'no with `false`', {
        state: false
    });

    stateTestCase(t, 'no with string', {
        state: 'no'
    });
});
