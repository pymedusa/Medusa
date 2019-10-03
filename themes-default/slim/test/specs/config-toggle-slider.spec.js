import { createLocalVue, mount } from '@vue/test-utils';
import { ConfigToggleSlider } from '../../src/components';

describe('ConfigToggleSlider.test.js', () => {
    let localVue;

    beforeEach(() => {
        localVue = createLocalVue();
    });

    it('renders', () => {
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

        expect(wrapper.element).toMatchSnapshot();
    });
});
