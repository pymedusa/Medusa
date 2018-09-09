import test from 'ava';
import { createLocalVue, mount } from '@vue/test-utils';
import { StateSwitch } from '../../src/components';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
});

test('renders', t => {
    const { localVue } = t.context;

    t.snapshot(mount(StateSwitch, {
        localVue,
        propsData: {
            state: null
        }
    }).html(), 'loading with `null`');

    t.snapshot(mount(StateSwitch, {
        localVue,
        propsData: {
            state: 'loading'
        }
    }).html(), 'loading with string');

    t.snapshot(mount(StateSwitch, {
        localVue,
        propsData: {
            theme: 'light',
            state: 'loading'
        }
    }).html(), 'loading with `theme` prop');

    t.snapshot(mount(StateSwitch, {
        localVue,
        propsData: {
            state: true
        }
    }).html(), 'yes with `true`');

    t.snapshot(mount(StateSwitch, {
        localVue,
        propsData: {
            state: 'yes'
        }
    }).html(), 'yes with string');

    t.snapshot(mount(StateSwitch, {
        localVue,
        propsData: {
            state: false
        }
    }).html(), 'no with `false`');

    t.snapshot(mount(StateSwitch, {
        localVue,
        propsData: {
            state: 'no'
        }
    }).html(), 'no with string');
});
