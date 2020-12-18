import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { SubMenu } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('SubMenu.test.js', () => {
    let localVue;
    let store;
    let routerBase;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        store = new Store({ state });

        routerBase = '/'; // This might be '/webroot'
    });

    it('renders simple sub menu', () => {
        const router = new VueRouter({
            base: routerBase,
            mode: 'history',
            routes: [{
                path: '/',
                name: '',
                meta: {
                    subMenu: [
                        { title: 'General', path: 'config/general/', icon: 'menu-icon-config' },
                        { title: 'Anime', path: 'config/anime/', icon: 'menu-icon-anime' }
                    ]
                }
            }]
        });
        const wrapper = shallowMount(SubMenu, {
            localVue,
            store,
            router
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders function-based sub menu', () => {
        const router = new VueRouter({
            base: routerBase,
            mode: 'history',
            routes: [{
                path: '/',
                name: '',
                meta: {
                    subMenu: vm => {
                        const { recentShows } = vm.$store.state.config.general;
                        return recentShows.map((show, index) => {
                            return {
                                title: show.name,
                                path: `home/displayShow?indexername=${show.indexerName}&seriesid=${show.showId}`,
                                requires: index % 2,
                                icon: 'menu-icon-addshow'
                            };
                        });
                    }
                }
            }]
        });
        const wrapper = shallowMount(SubMenu, {
            localVue,
            store,
            router
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
