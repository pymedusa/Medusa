import { createLocalVue, mount } from '@vue/test-utils';
import { ConfigToggleSlider } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('ConfigToggleSlider.test.js', () => {
    let localVue;
    let $store;

    beforeEach(() => {
        localVue = createLocalVue();
        const { state } = fixtures;
        $store = {
            state
        };
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
            },
            mocks: {
                $store
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with experimental flag, experimental features disabled', () => {
        $store.state.config.general.experimental = false;
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
                id: 'test-id',
                experimental: true
            },
            mocks: {
                $store
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with experimental flag, experimental features enabled', () => {
        $store.state.config.general.experimental = true;
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
                id: 'test-id',
                experimental: true
            },
            mocks: {
                $store
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
