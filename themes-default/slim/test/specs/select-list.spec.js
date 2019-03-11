import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { SelectList } from '../../src/components';
import fixtures from '../__fixtures__/common';

describe('SelectList.test.js', () => {
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
        const wrapper = mount(SelectList, {
            localVue,
            store,
            propsData: {
                listItems: []
            }
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders with values', () => {
        const wrapper = mount(SelectList, {
            localVue,
            store
        });

        const expectedItems = [
            'abc',
            'bcd',
            'test'
        ];

        expectedItems.forEach(item => {
            wrapper.setData({ newItem: item });
            wrapper.vm.addNewItem();
        });

        expect(wrapper.element).toMatchSnapshot();
        const inputWrapperArray = wrapper.findAll('li input[type="text"]');
        expect(inputWrapperArray.length).toEqual(expectedItems.length);

        wrapper.vm.editItems.forEach((item, index) => {
            expect(item.value).toEqual(expectedItems[index]);
        });
    });
});
