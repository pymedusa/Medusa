import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { QualityPill } from '../../src/components';
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

test('1080p WEB-DL', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(QualityPill, {
        localVue,
        store,
        propsData: {
            quality: 128
        }
    });

    t.snapshot(wrapper.html());
});

test('HD = all 720p and all 1080p, allowed', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(QualityPill, {
        localVue,
        store,
        propsData: {
            quality: 8 | 32 | 64 | 128 | 256 | 512
        }
    });

    t.snapshot(wrapper.html());
});

test('WEB-DL 720p + 4K UHD WEB-DL, allowed', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(QualityPill, {
        localVue,
        store,
        propsData: {
            quality: 128 | 2048
        }
    });

    t.snapshot(wrapper.html());
});

test('720p WEB-DL allowed + 1080p WEB-DL preferred + show title', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(QualityPill, {
        localVue,
        store,
        propsData: {
            quality: 64 | (128 << 16),
            showTitle: true
        }
    });

    t.snapshot(wrapper.html());
});

test('Custom "Proper" pill', t => {
    const { localVue, store } = t.context;
    const wrapper = mount(QualityPill, {
        localVue,
        store,
        propsData: {
            quality: 0,
            override: {
                class: 'quality Proper',
                text: 'Proper'
            }
        }
    });

    t.snapshot(wrapper.html());
});
