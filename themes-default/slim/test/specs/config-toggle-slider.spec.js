import test from 'ava';
import { createLocalVue, mount } from '@vue/test-utils';
import { ConfigToggleSlider } from '../../static/js/templates';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
});

test('renders', t => {
    const { localVue } = t.context;
    const wrapper = mount(ConfigToggleSlider, {
        localVue,
        stubs: ['ToggleButton'],
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
