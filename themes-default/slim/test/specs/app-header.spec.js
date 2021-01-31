import Vue from 'vue';
import Vuex, { Store, createStore } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount, shallowMount } from '@vue/test-utils';
import { AppHeader } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('AppHeader.test.js', () => {
    let localVue;
    let $store;
    let routerBase;
    let route;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);
        const { state } = fixtures;

        $store = {
            state
        };
        routerBase = '/';

        route = {
            path: '/home/displayShow',
            // name: 'home',
            query: {
                showslug: 'tvdb253463'
            }
            // meta: {
            //     topMenu: 'home',
            //     converted: true,
            //     nocache: true // Use this flag, to have the router-view use :key="$route.fullPath"
            // }
        };
    });

    it('renders', () => {
        const router = new VueRouter({
            routes: [{
                path: '/home/displayShow',
                name: 'show',
                query: {
                    showslug: 'tvdb253463'
                },
                meta: {
                    topMenu: 'home',
                    converted: true,
                    nocache: true // Use this flag, to have the router-view use :key="$route.fullPath"
                }
            }]
        });

        const wrapper = shallowMount(AppHeader, {
            localVue: localVue,
            router: router,
            mocks: {
                $store
            },
        });
        wrapper.vm.$router.push(route);

        Vue.nextTick(() => {
            expect(wrapper.element).toMatchSnapshot();
        });
    });
});
