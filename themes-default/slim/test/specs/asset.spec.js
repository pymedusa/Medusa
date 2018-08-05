import test from 'ava';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { Asset } from '../../static/js/templates';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
    t.context.localVue.use(Vuex);
    t.context.localVue.use(VueRouter);
});

test('renders default content for network', t => {
    const { localVue } = t.context;
    const wrapper = mount(Asset, {
        localVue,
        propsData: {
            type: 'network',
            default: 'https://default_website.tld/img.png'
        }
    });

    const html = wrapper.html();

    t.snapshot(html);
    t.true(html.includes('https://default_website.tld/img.png'));
});

test('renders image with API v2 path for network', t => {
    const { localVue } = t.context;
    const wrapper = mount(Asset, {
        localVue,
        propsData: {
            type: 'network',
            seriesSlug: 'tvdb1000',
            default: 'https://default_website.tld/img.png'
        }
    });

    const html = wrapper.html();

    t.snapshot(html);
    t.true(html.includes('/api/v2/series/tvdb1000/asset/network?api_key='));
});
