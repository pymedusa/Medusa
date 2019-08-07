import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { AddShowOptions } from '../../src/components';
import constsModule from '../../src/store/modules/consts';
import fixtures from '../__fixtures__/common';

describe('AddShowOptions.test.js', () => {
    let localVue;
    let store;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        store = new Store({
            modules: {
                consts: constsModule
            }
        });
        store.replaceState(state);
    });

    it('renders with `enable-anime-options` disabled', () => {
        const wrapper = mount(AddShowOptions, {
            localVue,
            store,
            stubs: [
                'quality-chooser',
                'toggle-button'
            ],
            propsData: {
                enableAnimeOptions: false
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with `enable-anime-options` enabled', () => {
        const wrapper = mount(AddShowOptions, {
            localVue,
            store,
            stubs: [
                'quality-chooser',
                'toggle-button'
            ],
            propsData: {
                enableAnimeOptions: true
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
