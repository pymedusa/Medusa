import { createLocalVue, mount } from '@vue/test-utils';
import { ConfigTextboxNumber } from '../../src/components';

describe('ConfigTextboxNumber.test.js', () => {
    let localVue;

    beforeEach(() => {
        localVue = createLocalVue();
    });

    it('renders', () => {
        const wrapper = mount(ConfigTextboxNumber, {
            localVue,
            propsData: {
                label: 'test-label',
                explanations: [
                    'explanation 1',
                    'explanation 2'
                ],
                value: 30,
                id: 'test-id',
                min: 20,
                step: 0.5
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with min and max', () => {
        const wrapper = mount(ConfigTextboxNumber, {
            localVue,
            propsData: {
                label: 'test-label',
                explanations: [
                    'explanation 1',
                    'explanation 2'
                ],
                value: 30,
                id: 'test-id',
                min: 20,
                step: 0.5,
                max: 100
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
