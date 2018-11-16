import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { AppHeader } from '../../src/components';
import fixtures from '../__fixtures__/app-header';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
    t.context.localVue.use(Vuex);
    t.context.localVue.use(VueRouter);

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
                return {
                    ...state.config
                };
            },
            topMenu() {
                return 'home';
            }
        }
    });

    t.snapshot(wrapper.html());
});
