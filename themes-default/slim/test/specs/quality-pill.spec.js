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

test('renders', t => {
    const { localVue, store } = t.context;

    t.snapshot(mount(QualityPill, {
        localVue,
        store,
        propsData: {
            quality: 128
        }
    }).html(), '1080p WEB-DL');

    t.snapshot(mount(QualityPill, {
        localVue,
        store,
        propsData: {
            quality: 8 | 32 | 64 | 128 | 256 | 512
        }
    }).html(), 'HD = all 720p and all 1080p, allowed');

    t.snapshot(mount(QualityPill, {
        localVue,
        store,
        propsData: {
            quality: 128 | 2048
        }
    }).html(), 'WEB-DL 720p + 4K UHD WEB-DL, allowed');

    t.snapshot(mount(QualityPill, {
        localVue,
        store,
        propsData: {
            quality: 64 | (128 << 16),
            showTitle: true
        }
    }).html(), '720p WEB-DL allowed + 1080p WEB-DL preferred + show title');

    t.snapshot(mount(QualityPill, {
        localVue,
        store,
        propsData: {
            quality: 0,
            override: {
                class: 'quality Proper',
                text: 'Proper'
            }
        }
    }).html(), 'Custom "Proper" pill');
});
