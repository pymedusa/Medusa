import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { PlotInfo } from '../../src/components';
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
    const wrapper = mount(PlotInfo, {
        localVue,
        store,
        propsData: {
            seriesSlug: '',
            season: '',
            episode: ''
        }
    });

    t.snapshot(wrapper.html());
});
