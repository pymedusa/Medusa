import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { ShowSelector } from '../../static/js/templates';
import { state } from '../__fixtures__/common';
import { shows } from '../__fixtures__/shows';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
    t.context.localVue.use(Vuex);
    t.context.localVue.use(VueRouter);

    const { Store } = Vuex;
    t.context.state = state;
    t.context.store = new Store({ state });
});

test('renders "loading..." with empty show array', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(ShowSelector, {
        localVue,
        computed: {
            shows() {
                return [];
            },
            config() {
                return {
                    animeSplitHome: false,
                    sortArticle: 'asc'
                };
            }
        },
        store
    });

    t.snapshot(wrapper.html());
});

test('renders with shows', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(ShowSelector, {
        localVue,
        computed: {
            shows() {
                return shows;
            },
            config() {
                return {
                    animeSplitHome: false,
                    sortArticle: true
                };
            }
        },
        store
    });

    t.snapshot(wrapper.html());
});

test('renders with articles(The|A|An) ignored', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(ShowSelector, {
        localVue,
        computed: {
            shows() {
                return shows;
            },
            config() {
                return {
                    animeSplitHome: false,
                    sortArticle: false
                };
            }
        },
        store
    });

    t.snapshot(wrapper.html());
});

test('renders with split sections', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(ShowSelector, {
        localVue,
        computed: {
            shows() {
                return shows;
            },
            config() {
                return {
                    animeSplitHome: false,
                    sortArticle: 'asc'
                };
            }
        },
        store
    });

    t.snapshot(wrapper.html());
});
