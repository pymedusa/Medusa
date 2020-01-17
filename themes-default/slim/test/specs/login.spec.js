import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { Login } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('Login.test.js', () => {
    let localVue;
    let store;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        const { state } = fixtures;
        store = new Store({ state });
    });

    test('renders', () => {
        const wrapper = mount(Login, {
            localVue,
            store
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
