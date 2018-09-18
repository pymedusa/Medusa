import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { AddShowOptions } from '../../src/components';
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

test('renders with `enable-anime-options` disabled', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(AddShowOptions, {
        localVue,
        store,
        stubs: [
            'quality-chooser',
            'toggle-button'
        ],
        propsData: {
            enableAnimeOptions: false
        }
    });

    t.snapshot(wrapper.html());
});

test('renders with `enable-anime-options` enabled', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(AddShowOptions, {
        localVue,
        store,
        stubs: [
            'quality-chooser',
            'toggle-button'
        ],
        propsData: {
            enableAnimeOptions: true
        }
    });

    t.snapshot(wrapper.html());
});
