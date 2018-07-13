import test from 'ava';
import Puex from 'puex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import fixtures from '../__fixtures__/app-header';

// Needs to be required otherwise nyc won't see it
const AppHeader = require('../../static/js/templates/app-header.vue');

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
    t.context.localVue.use(Puex);
    t.context.localVue.use(VueRouter);

    const { state } = fixtures;
    t.context.state = state;
    t.context.store = new Puex({ state });
});

test('renders', t => {
    const { localVue, store, state } = t.context;
    const wrapper = mount(AppHeader, {
        localVue,
        store,
        stubs: ['app-link'],
        computed: {
            config() {
                return Object.assign(state.config, {
                });
            }
        }
    });

    t.snapshot(wrapper.html());
});
