import { createLocalVue, mount } from '@vue/test-utils';
import { ScrollButtons } from '../../src/components';

describe('ScrollButtons.test.js', () => {
    let localVue;

    beforeEach(() => {
        localVue = createLocalVue();
    });

    it('renders', () => {
        const wrapper = mount(ScrollButtons, {
            localVue,
            data() {
                return {
                    showToTop: true,
                    showLeftRight: true
                };
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
