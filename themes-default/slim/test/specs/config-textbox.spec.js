import test from 'ava';
import { createLocalVue, mount } from '@vue/test-utils';

// Needs to be required otherwise nyc won't see it
const NamePattern = require('../../static/js/templates/config-textbox.vue');

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
});

test('renders', t => {
    const { localVue } = t.context;
    const wrapper = mount(NamePattern, {
        localVue,
        propsData: {
            label: 'test-label',
            explanations: [
                'explanation 1',
                'explanation 2'
            ],
            value: 'initial value',
            id: 'test-id'
        }
    });

    t.snapshot(wrapper.html());
});
