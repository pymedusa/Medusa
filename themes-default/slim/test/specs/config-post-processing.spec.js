import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { ConfigPostProcessing } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('ConfigPostProcessing.test.js', () => {
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
        // Prevents `TypeError: $(...).tabs is not a function`
        ConfigPostProcessing.beforeMount = () => {};

        const wrapper = mount(ConfigPostProcessing, {
            localVue,
            store,
            stubs: [
                'app-link',
                'file-browser',
                'name-pattern',
                'select-list',
                'toggle-button'
            ]
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
