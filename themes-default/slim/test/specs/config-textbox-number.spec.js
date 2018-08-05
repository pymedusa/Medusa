import test from 'ava';
import { createLocalVue, mount } from '@vue/test-utils';
import { ConfigTextboxNumber } from '../../static/js/templates';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
});

test('renders', t => {
    const { localVue } = t.context;
    const wrapper = mount(ConfigTextboxNumber, {
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
