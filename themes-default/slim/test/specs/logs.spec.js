import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { Logs } from '../../src/components';
import fixtures from '../__fixtures__/common';
import exampleLogs from '../__fixtures__/example-logs';

describe('Logs.test.js', () => {
    let localVue;
    let store;
    let routerBase;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        store = new Store({ state });

        routerBase = '/'; // This might be '/webroot'
    });

    it('renders', () => {
        const router = new VueRouter({
            base: routerBase,
            mode: 'history'
        });
        const wrapper = shallowMount(Logs, {
            localVue,
            store,
            router
        });

        wrapper.setData({
            logLines: exampleLogs
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
