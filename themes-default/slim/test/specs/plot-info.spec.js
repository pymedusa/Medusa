import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import fixtures from '../__fixtures__/app-header';

// Needs to be required otherwise nyc won't see it
const PlotInfo = require('../../static/js/templates/plot-info.vue');

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
