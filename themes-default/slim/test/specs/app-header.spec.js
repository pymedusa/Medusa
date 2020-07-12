import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { AppHeader } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('AppHeader.test.js', () => {
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
        const wrapper = shallowMount(AppHeader, {
            localVue,
            store,
            computed: {
                topMenu() {
                    return 'home';
                }
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
