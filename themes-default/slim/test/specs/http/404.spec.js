import test from 'ava';
import { mount } from '@vue/test-utils';
import { NotFound } from '../../../src/components';

test('renders not-found page', t => {
    const wrapper = mount(NotFound);

    t.snapshot(wrapper.html());
});
