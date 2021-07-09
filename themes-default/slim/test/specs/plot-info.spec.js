import Vuex, { Store } from 'vuex';
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
        store = new Store({ state });
    });

    it('renders', () => {
        const wrapper = mount(PlotInfo, {
            localVue,
            store,
            propsData: {
                description: 'This is an example for an episodes plot info'
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
