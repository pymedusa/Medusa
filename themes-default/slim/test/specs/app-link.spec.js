import test from 'ava';
import Puex from 'puex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import fixtures from '../__fixtures__/app-link';

// Needs to be required otherwise nyc won't see it
const AppLink = require('../../static/js/templates/app-link.vue');

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
    t.context.localVue.use(Puex);
    t.context.localVue.use(VueRouter);

    const { state } = fixtures;
    t.context.state = state;
    t.context.store = new Puex({ state });
    t.context.base = 'http://localhost:8081/';
});

test('renders external link', t => {
    const { base, localVue, store, state } = t.context;
    const wrapper = mount(AppLink, {
        localVue,
        store,
        propsData: {
            base,
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
    const { base, localVue, store, state } = t.context;
    const wrapper = mount(AppLink, {
        localVue,
        store,
        propsData: {
            base,
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
    const { base, localVue, store } = t.context;
    const wrapper = mount(AppLink, {
        localVue,
        store,
        propsData: {
            base,
            href: './config'
        }
    });

    t.snapshot(wrapper.html());
    t.is(wrapper.attributes().href, 'http://localhost:8081/config');
    t.is(wrapper.attributes().target, '_self');
    t.is(wrapper.attributes().rel, undefined);
});

test.failing('renders router-link from href string', t => {
    const { base, localVue, store } = t.context;
    const router = new VueRouter({
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
            base,
            to: 'config'
        }
    });

    t.snapshot(wrapper.html());
    t.is(wrapper.attributes().href, 'http://localhost:8081/config');
    t.is(wrapper.attributes().target, '_self');
    t.is(wrapper.attributes().rel, undefined);
});
