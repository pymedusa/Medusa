import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { AppLink, AddRecommended } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('AddRecommended.test.js', () => {
    let wrapper;

    beforeEach(() => {
        const localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);
        localVue.component('app-link', AppLink);

        const { state } = fixtures;
        const { Store } = Vuex;
        const store = new Store({ state });

        wrapper = shallowMount(AddRecommended, {
            localVue,
            store
        });
    });

    it('renders', () => {
        expect(wrapper.element).toMatchSnapshot();
    });
});
