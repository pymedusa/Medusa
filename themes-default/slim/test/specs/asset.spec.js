import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { Asset } from '../../src/components';

describe('Asset.test.js', () => {
    let localVue;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);
    });

    it('renders default content for network', () => {
        const wrapper = mount(Asset, {
            localVue,
            propsData: {
                type: 'network',
                defaultSrc: 'https://default_website.tld/img.png'
            }
        });

        expect(wrapper.element).toMatchSnapshot();
        expect(wrapper.find('img').attributes().src).toEqual('https://default_website.tld/img.png');
    });

    it('renders image with API v2 path for network', () => {
        const wrapper = mount(Asset, {
            localVue,
            propsData: {
                type: 'network',
                showSlug: 'tvdb1000',
                defaultSrc: 'https://default_website.tld/img.png'
            }
        });

        expect(wrapper.element).toMatchSnapshot();
        expect(wrapper.find('img').attributes().src).toEqual(expect.stringContaining('/api/v2/series/tvdb1000/asset/network?api_key='));
    });

    it('renders image with API v2 path for network with lazy loading', () => {
        const wrapper = mount(Asset, {
            localVue,
            propsData: {
                type: 'posterThumb',
                lazy: true,
                showSlug: 'tvdb1000',
                defaultSrc: 'https://default_website.tld/img.png',
                cls: 'show-image',
                link: false
            }
        });

        expect(wrapper.element).toMatchSnapshot();
        expect(wrapper.find('img').attributes()['data-src']).toEqual(expect.stringContaining('/api/v2/series/tvdb1000/asset/posterThumb?api_key='));
        expect(wrapper.find('img').attributes()['data-loaded']).toEqual(expect.stringContaining('true'));
    });
});
