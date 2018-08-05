import test from 'ava';
import { createLocalVue, mount } from '@vue/test-utils';
import { ConfigTextbox } from '../../static/js/templates';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
});

test('renders', t => {
    const { localVue } = t.context;
    const wrapper = mount(ConfigTextbox, {
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
