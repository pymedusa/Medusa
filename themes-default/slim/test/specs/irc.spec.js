import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { IRC } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('IRC.test.js', () => {
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
        const wrapper = mount(IRC, {
            localVue,
            store
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with username', () => {
        const wrapper = mount(IRC, {
            localVue,
            store,
            computed: {
                gitUsername() {
                    return 'pymedusa';
                }
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
