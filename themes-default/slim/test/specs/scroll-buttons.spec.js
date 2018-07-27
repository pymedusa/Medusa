import test from 'ava';
import { createLocalVue, mount } from '@vue/test-utils';

// Needs to be required otherwise nyc won't see it
const ScrollButtons = require('../../static/js/templates/scroll-buttons.vue');

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
});

test('renders', t => {
    const { localVue } = t.context;
    const wrapper = mount(ScrollButtons, {
        localVue,
        data() {
            return {
                showToTop: true,
                showLeftRight: true
            };
        }
    });

    t.snapshot(wrapper.html());
});
