import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { AppHeader } from '../../src/components';
import fixtures from '../__fixtures__/app-header';

describe('AppHeader.test.js', () => {
    let localVue;
    let store;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        const { Store } = Vuex;
        store = new Store({ state });
    });

    it('renders', () => {
        const { state } = fixtures;
        const wrapper = shallowMount(AppHeader, {
            localVue,
            store,
            computed: {
                config() {
                    return {
                        ...state.config
                    };
                },
                topMenu() {
                    return 'home';
                }
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
