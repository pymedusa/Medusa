import { mount } from '@vue/test-utils';
import { NotFound } from '../../../src/components';

describe('NotFound.test.js', () => {
    it('renders not-found page', () => {
        const wrapper = mount(NotFound);

        expect(wrapper.element).toMatchSnapshot();
    });
});
