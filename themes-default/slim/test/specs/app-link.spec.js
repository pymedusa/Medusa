import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { AppLink } from '../../src/components';
import fixtures from '../__fixtures__/app-link';

describe('AppLink.test.js', () => {
    let localVue;
    let store;
    let routerBase;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        const { Store } = Vuex;
        store = new Store({ state });
        routerBase = '/'; // This might be '/webroot'
    });

    it('renders external link', () => {
        const { state } = fixtures;
        const wrapper = mount(AppLink, {
            localVue,
            store,
            propsData: {
                href: 'https://google.com'
            },
            computed: {
                config() {
                    return Object.assign(state.config, {
                        anonRedirect: ''
                    });
                }
            }
        });

        expect(wrapper.element).toMatchSnapshot();
        expect(wrapper.attributes().href).toEqual('https://google.com');
        expect(wrapper.attributes().target).toEqual('_blank');
        expect(wrapper.attributes().rel).toEqual('noreferrer');
    });

    it('renders anonymised external link', () => {
        const { state } = fixtures;
        const wrapper = mount(AppLink, {
            localVue,
            store,
            propsData: {
                href: 'https://google.com'
            },
            computed: {
                config() {
                    return Object.assign(state.config, {
                        anonRedirect: 'https://anon-redirect.tld/?url='
                    });
                }
            }
        });

        expect(wrapper.element).toMatchSnapshot();
        expect(wrapper.attributes().href).toEqual('https://anon-redirect.tld/?url=https://google.com');
        expect(wrapper.attributes().target).toEqual('_blank');
        expect(wrapper.attributes().rel).toEqual('noreferrer');
    });

    it('renders internal link', () => {
        const wrapper = mount(AppLink, {
            localVue,
            store,
            propsData: {
                href: './config'
            }
        });

        expect(wrapper.element).toMatchSnapshot();
        expect(wrapper.attributes().href).toEqual('http://localhost:8081/config');
        expect(wrapper.attributes().target).toEqual('_self');
        expect(wrapper.attributes().rel).toEqual(undefined);
    });

    it('renders router-link from to (string)', () => {
        const router = new VueRouter({
            base: routerBase,
            mode: 'history',
            routes: [{
                path: '/config',
                name: 'config'
            }]
        });
        const wrapper = mount(AppLink, {
            localVue,
            store,
            router,
            propsData: {
                to: 'config'
            }
        });

        expect(wrapper.element).toMatchSnapshot();
        expect(wrapper.attributes().href).toEqual('/config');
        expect(wrapper.attributes().target).toEqual(undefined);
        expect(wrapper.attributes().rel).toEqual(undefined);
    });

    it('renders router-link from to (object)', () => {
        const router = new VueRouter({
            base: routerBase,
            mode: 'history',
            routes: [{
                path: '/config',
                name: 'config'
            }]
        });
        const wrapper = mount(AppLink, {
            localVue,
            store,
            router,
            propsData: {
                to: {
                    path: '/config'
                }
            }
        });

        expect(wrapper.element).toMatchSnapshot();
        expect(wrapper.attributes().href).toEqual('/config');
        expect(wrapper.attributes().target).toEqual(undefined);
        expect(wrapper.attributes().rel).toEqual(undefined);
    });

    it('renders "false-link" anchor', () => {
        const wrapper = mount(AppLink, {
            localVue,
            store,
            attrs: {
                name: 'season-3'
            }
        });

        expect(wrapper.element).toMatchSnapshot();
        expect(wrapper.attributes().name).toEqual('season-3');
        expect(wrapper.attributes()['false-link']).toEqual('true');
    });

    it('renders simple anchor', () => {
        const wrapper = mount(AppLink, {
            localVue,
            store,
            attrs: {
                class: 'my-class'
            }
        });

        expect(wrapper.element).toMatchSnapshot();
        expect(wrapper.attributes().class).toEqual('my-class');
        expect(wrapper.attributes()['false-link']).toEqual(undefined);
    });
});
