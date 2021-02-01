import Vue from 'vue';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { AppHeader } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('AppHeader.test.js', () => {
    let localVue;
    let $store;
    let routerBase;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);
        const { state } = fixtures;

        $store = {
            state
        };

        routerBase = '/'; // This might be '/webroot'
    });

    it('renders', () => {
        const router = new VueRouter({
            base: routerBase,
            routes: [{
                path: '/home/displayShow',
                name: 'show',
                query: {
                    showslug: 'tvdb253463'
                },
                meta: {
                    topMenu: 'home'
                }
            }]
        });

        const wrapper = shallowMount(AppHeader, {
            localVue,
            router,
            mocks: {
                $store
            }
        });

        // We need to puth the query params on the route. Therefor we push a new route.
        // The query params cannot be pulled from the routes: [{..}]. It has to be passed.
        const route = {
            path: '/home/displayShow',
            name: 'show',
            query: {
                showslug: 'tvdb253463'
            }
        };

        wrapper.vm.$router.push(route);

        Vue.nextTick(() => {
            expect(wrapper.element).toMatchSnapshot();
        });
    });
});
