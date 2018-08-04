import test from 'ava';
import { createLocalVue, mount } from '@vue/test-utils';

// Needs to be required otherwise nyc won't see it
const configToggleSlider = require('../../static/js/templates/config-toggle-slider.vue');

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
});

test('renders', t => {
    const { localVue } = t.context;
    const wrapper = mount(configToggleSlider, {
        localVue,
        propsData: {
            label: 'test-label',
            explanations: [
                'explanation 1',
                'explanation 2'
            ],
            checked: true,
            id: 'test-id'
        }
    });

    t.snapshot(wrapper.html());
});
