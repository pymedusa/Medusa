import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import tk from 'timekeeper';

import { AppFooter } from '../../src/components';
import consts from '../../src/store/modules/config/consts';
import system from '../../src/store/modules/config/system';
import fixtures from '../__fixtures__/common';

describe('AppFooter', () => {
    let localVue;
    let store;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        store = new Store({
            modules: {
                consts: {
                    getters: consts.getters,
                    state: state.config.consts
                },
                system: {
                    getters: system.getters,
                    state: state.config.system
                },
                config: {
                    state: state.config
                },
                stats: {
                    state: state.stats
                }
            }
        });
    });

    it('renders', () => {
        tk.travel(new Date(2019, 6, 10, 9, 51, 21, 300));

        const wrapper = shallowMount(AppFooter, {
            localVue,
            store
        });

        expect(wrapper.element).toMatchSnapshot();

        tk.reset();
    });
});
