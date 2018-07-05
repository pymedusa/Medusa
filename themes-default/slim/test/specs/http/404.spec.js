import test from 'ava';
import { mount } from '@vue/test-utils';

// Needs to be required otherwise nyc won't see it
const NotFound = require('../../static/js/templates/http/404.vue');

test('renders not-found page', t => {
    const wrapper = mount(NotFound);

    t.snapshot(wrapper.html());
});
