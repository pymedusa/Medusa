import test from 'ava';
import Puex from 'puex';
import { mount } from '@vue/test-utils';

// Needs to be required otherwise nyc won't see it
const AppLink = require('../../static/js/templates/app-link.vue');

test.beforeEach(t => {
    t.context.base = 'http://localhost:8081/';
    t.context.store = new Puex({
        state: {
            config: {
                anonRedirect: null
            }
        }
    });
});

test('renders external link', t => {
    const { base, store } = t.context;
    const computed = {
        config() {
            return {
                anonRedirect: ''
            };
        }
    };
    const wrapper = mount(AppLink, {
        propsData: {
            base,
            href: 'https://google.com'
        },
        mocks: {
            store,
            computed
        }
    });

    t.snapshot(wrapper.html());
    t.is(wrapper.attributes().href, 'https://google.com');
    t.is(wrapper.attributes().target, '_blank');
    t.is(wrapper.attributes().rel, 'noreferrer');
});

test('renders anonymised external link', t => {
    const { base, store } = t.context;
    const computed = {
        config() {
            return {
                anonRedirect: 'https://anon-redirect.tld/?url='
            };
        }
    };
    const wrapper = mount(AppLink, {
        propsData: {
            base,
            href: 'https://google.com'
        },
        mocks: {
            store
        },
        computed
    });

    t.snapshot(wrapper.html());
    t.is(wrapper.attributes().href, 'https://anon-redirect.tld/?url=https://google.com');
    t.is(wrapper.attributes().target, '_blank');
    t.is(wrapper.attributes().rel, 'noreferrer');
});

test('renders internal link', t => {
    const { base, store } = t.context;
    const wrapper = mount(AppLink, {
        propsData: {
            base,
            href: './config'
        },
        mocks: {
            store
        }
    });

    t.snapshot(wrapper.html());
    t.is(wrapper.attributes().href, 'http://localhost:8081/config');
    t.is(wrapper.attributes().target, '_self');
    t.is(wrapper.attributes().rel, undefined);
});
