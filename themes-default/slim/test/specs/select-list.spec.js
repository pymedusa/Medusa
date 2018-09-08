import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { SelectList } from '../../src/components';
import fixtures from '../__fixtures__/common';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
    t.context.localVue.use(Vuex);
    t.context.localVue.use(VueRouter);

    const { state } = fixtures;
    const { Store } = Vuex;
    t.context.state = state;
    t.context.store = new Store({ state });
});

test('renders', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(SelectList, {
        localVue,
        store,
        propsData: {
            listItems: []
        }
    });

    t.snapshot(wrapper.html());
});

test.failing('renders with values', t => {
    const { localVue, store } = t.context;

    const listItems = [
        'abc',
        'bcd',
        'test'
    ];

    const wrapper = mount(SelectList, {
        localVue,
        store,
        propsData: {
            listItems
        }
    });

    const expectedItems = listItems;
    const inputWrapperArray = wrapper.findAll('li input[type="text"]');

    t.is(inputWrapperArray.length, expectedItems.length);

    inputWrapperArray.wrappers.forEach((inputWrapper, index) => {
        const { element } = inputWrapper;
        t.is(element.value, expectedItems[index]);
    });

    t.snapshot(wrapper.html());
});

test.failing('renders with Python dict values (v0.2.9 bug)', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(SelectList, {
        localVue,
        store,
        propsData: {
            listItems: [
                `{u'id': 0, u'value': u'!sync'}`, // eslint-disable-line quotes
                `{u'id': 1, u'value': u'lftp-pget-status'}` // eslint-disable-line quotes
            ]
        }
    });

    const expectedItems = [
        '!sync',
        'lftp-pget-status'
    ];

    const inputWrapperArray = wrapper.findAll('li input[type="text"]');

    t.is(inputWrapperArray.length, expectedItems.length);

    inputWrapperArray.wrappers.forEach((inputWrapper, index) => {
        const { element } = inputWrapper;
        t.is(element.value, expectedItems[index]);
    });

    t.snapshot(wrapper.html());
});
