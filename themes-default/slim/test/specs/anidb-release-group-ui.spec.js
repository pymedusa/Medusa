import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { AnidbReleaseGroupUi } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('AnidbReleaseGroupUi.test.js', () => {
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
        const wrapper = shallowMount(AnidbReleaseGroupUi, {
            localVue,
            store,
            propsData: {
                showName: ''
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
