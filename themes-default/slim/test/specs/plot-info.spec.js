import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { PlotInfo } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('PlotInfo.test.js', () => {
    let localVue;
    let store;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        const { Store } = Vuex;
        store = new Store({ state });
    });

    it('renders', () => {
        const wrapper = mount(PlotInfo, {
            localVue,
            store,
            propsData: {
                showSlug: '',
                season: '',
                episode: ''
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
