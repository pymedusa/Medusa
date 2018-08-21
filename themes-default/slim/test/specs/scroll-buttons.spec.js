import test from 'ava';
import { createLocalVue, mount } from '@vue/test-utils';
import { ScrollButtons } from '../../src/components';

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
