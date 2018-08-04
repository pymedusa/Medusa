import test from 'ava';
import { createLocalVue, mount } from '@vue/test-utils';

// Needs to be required otherwise nyc won't see it
const configTextbox = require('../../static/js/templates/config-textbox-number.vue');

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
});

test('renders', t => {
    const { localVue } = t.context;
    const wrapper = mount(configTextbox, {
        localVue,
        propsData: {
            label: 'test-label',
            explanations: [
                'explanation 1',
                'explanation 2'
            ],
            value: '30.5',
            id: 'test-id',
            min: 20,
            step: 0.5
        }
    });

    t.snapshot(wrapper.html());
});
