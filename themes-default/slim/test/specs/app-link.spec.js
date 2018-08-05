import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { AppLink } from '../../static/js/templates';
import fixtures from '../__fixtures__/app-link';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
    t.context.localVue.use(Vuex);
    t.context.localVue.use(VueRouter);

    const { state } = fixtures;
    const { Store } = Vuex;
    t.context.state = state;
    t.context.store = new Store({ state });
    t.context.routerBase = '/'; // This might be '/webroot'
});

test('renders external link', t => {
    const { localVue, store, state } = t.context;
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

    t.snapshot(wrapper.html());
    t.is(wrapper.attributes().href, 'https://google.com');
    t.is(wrapper.attributes().target, '_blank');
    t.is(wrapper.attributes().rel, 'noreferrer');
});

test('renders anonymised external link', t => {
    const { localVue, store, state } = t.context;
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

    t.snapshot(wrapper.html());
    t.is(wrapper.attributes().href, 'https://anon-redirect.tld/?url=https://google.com');
    t.is(wrapper.attributes().target, '_blank');
    t.is(wrapper.attributes().rel, 'noreferrer');
});

test('renders internal link', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(AppLink, {
        localVue,
        store,
        propsData: {
            href: './config'
        }
    });

    t.snapshot(wrapper.html());
    t.is(wrapper.attributes().href, 'http://localhost:8081/config');
    t.is(wrapper.attributes().target, '_self');
    t.is(wrapper.attributes().rel, undefined);
});

test('renders router-link from to (string)', t => {
    const { routerBase, localVue, store } = t.context;
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

    t.snapshot(wrapper.html());
    t.is(wrapper.attributes().href, '/config');
    t.is(wrapper.attributes().target, undefined);
    t.is(wrapper.attributes().rel, undefined);
});

test('renders router-link from to (object)', t => {
    const { routerBase, localVue, store } = t.context;
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

    t.snapshot(wrapper.html());
    t.is(wrapper.attributes().href, '/config');
    t.is(wrapper.attributes().target, undefined);
    t.is(wrapper.attributes().rel, undefined);
});

test('renders "false-link" anchor', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(AppLink, {
        localVue,
        store,
        attrs: {
            name: 'season-3'
        }
    });

    t.snapshot(wrapper.html());
    t.is(wrapper.attributes().name, 'season-3');
    t.is(wrapper.attributes()['false-link'], 'true');
});

test('renders simple anchor', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(AppLink, {
        localVue,
        store,
        attrs: {
            class: 'my-class'
        }
    });

    t.snapshot(wrapper.html());
    t.is(wrapper.attributes().class, 'my-class');
    t.is(wrapper.attributes()['false-link'], undefined);
});
