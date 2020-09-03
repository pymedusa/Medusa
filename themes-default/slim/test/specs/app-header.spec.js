import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { AppHeader } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('AppHeader.test.js', () => {
    let localVue;
    let store;
    let routerBase;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);

        const { state } = fixtures;
        store = new Store({ state });
    });

    it('renders', () => {
        const router = new VueRouter({
            base: routerBase,
            mode: 'history',
            routes: [{
                path: '/home/displayShow',
                name: 'show',
                query: {
                    indexername: 'tvdb',
                    seriesid: 253463
                }
            }]
        });

        const wrapper = shallowMount(AppHeader, {
            localVue,
            store,
            computed: {
                topMenu() {
                    return 'home';
                }
            },
            router
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
