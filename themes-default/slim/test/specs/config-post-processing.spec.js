import Vuex, { Store } from 'vuex';
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

        // Need to set metadataProviderSelected explicitely, as the watch won't trigger in jest.
        wrapper.setData({
            metadataProviderSelected: wrapper.vm.getFirstEnabledMetadataProvider()
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
