import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { AppLink, AppHeader } from '../../static/js/templates';
import fixtures from '../__fixtures__/app-header';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
    t.context.localVue.use(Vuex);
    t.context.localVue.use(VueRouter);
    t.context.localVue.component('app-link', AppLink);

    const { state } = fixtures;
    const { Store } = Vuex;
    t.context.state = state;
    t.context.store = new Store({ state });
});

test('renders', t => {
    const { localVue, store, state } = t.context;
    const wrapper = mount(AppHeader, {
        localVue,
        store,
        computed: {
            config() {
                return Object.assign(state.config, {
                });
            }
        }
    });

    t.snapshot(wrapper.html());
});
