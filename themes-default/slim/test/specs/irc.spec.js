import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { IRC } from '../../src/components';
import fixtures from '../__fixtures__/common';

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
    const { localVue, store } = t.context;
    const wrapper = mount(IRC, {
        localVue,
        store
    });

    t.snapshot(wrapper.html());
});

test('renders with username', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(IRC, {
        localVue,
        store,
        computed: {
            gitUserName() {
                return 'pymedusa';
            }
        }
    });

    t.snapshot(wrapper.html());
});
