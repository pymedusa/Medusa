import test from 'ava';
import { mount } from '@vue/test-utils';
import { NotFound } from '../../../static/js/templates';

test('renders not-found page', t => {
    const wrapper = mount(NotFound);

    t.snapshot(wrapper.html());
});
