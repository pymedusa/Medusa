import { createLocalVue, mount } from '@vue/test-utils';
import { ConfigTextbox } from '../../src/components';

describe('ConfigTextbox.test.js', () => {
    let localVue;

    beforeEach(() => {
        localVue = createLocalVue();
    });

    it('renders', () => {
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

        expect(wrapper.element).toMatchSnapshot();
    });
});
