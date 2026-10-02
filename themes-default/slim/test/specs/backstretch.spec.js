import $ from 'jquery';
import Vuex, { Store } from 'vuex';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import Backstretch from '../../src/components/backstretch.vue';

describe('Backstretch', () => {
    let localVue;
    let store;
    let wrappers;
    let $wrap;
    let originalBackstretch;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        store = new Store({
            state: {
                config: { layout: { fanartBackground: true, fanartBackgroundOpacity: 0.5 } },
                auth: { apiKey: 'test-key' }
            }
        });
        wrappers = [];
        $wrap = { css: jest.fn().mockReturnThis(), fadeIn: jest.fn().mockReturnThis() };
        originalBackstretch = $.backstretch;
        $('body').removeData('backstretch');
        $.backstretch = jest.fn(image => {
            const current = $('body').data('backstretch');
            if (image === 'destroy' && current) {
                current.destroy();
                return undefined;
            }
            // Without an instance, even 'destroy' falls through to image initialization.
            if (current) {
                current.destroy(true);
            }
            const instance = {
                $wrap,
                destroy: jest.fn(() => $('body').removeData('backstretch'))
            };
            $('body').data('backstretch', instance);
            return instance;
        });
    });

    afterEach(() => {
        wrappers.forEach(wrapper => wrapper.destroy());
        $('body').removeData('backstretch');
        $.backstretch = originalBackstretch;
    });

    const mountBackground = async (slug = 'tvdb-123') => {
        const wrapper = shallowMount(Backstretch, { localVue, store, propsData: { slug } });
        wrappers.push(wrapper);
        await wrapper.vm.$nextTick();
        return wrapper;
    };

    it('creates and configures a nonreactive background instance', async () => {
        const wrapper = await mountBackground();
        const instance = $('body').data('backstretch');
        expect($.backstretch).toHaveBeenCalledWith('api/v2/series/tvdb-123/asset/fanart?api_key=test-key');
        expect(wrapper.vm.backstretchInstance).toBe(instance);
        expect(instance).not.toHaveProperty('__ob__');
        expect($wrap.css).toHaveBeenCalledWith('top', '50px');
        expect($wrap.css).toHaveBeenCalledWith('opacity', 0.5);
        expect($wrap.fadeIn).toHaveBeenCalledWith(500);
    });

    it('destroys the current owner without invoking the global factory', async () => {
        const wrapper = await mountBackground();
        const instance = $('body').data('backstretch');
        $.backstretch.mockClear();
        wrapper.destroy();
        expect(instance.destroy).toHaveBeenCalledTimes(1);
        expect($.backstretch).not.toHaveBeenCalled();
        expect($('body').data('backstretch')).toBeUndefined();
        expect(wrapper.vm.backstretchInstance).toBeNull();
    });

    it('does not initialize a destroy image when the global instance is missing', async () => {
        const wrapper = await mountBackground();
        const instance = $('body').data('backstretch');
        $('body').removeData('backstretch');
        $.backstretch.mockClear();
        wrapper.destroy();
        expect($.backstretch).not.toHaveBeenCalled();
        expect(instance.destroy).not.toHaveBeenCalled();
        expect($('body').data('backstretch')).toBeUndefined();
    });

    it('leaves a newer owner intact even when the plugin reuses its wrapper', async () => {
        const previous = await mountBackground();
        const oldInstance = $('body').data('backstretch');
        await mountBackground('tvdb-456');
        const current = $('body').data('backstretch');
        expect(current.$wrap).toBe(oldInstance.$wrap);
        oldInstance.destroy.mockClear();
        $.backstretch.mockClear();
        previous.destroy();
        expect(oldInstance.destroy).not.toHaveBeenCalled();
        expect(current.destroy).not.toHaveBeenCalled();
        expect($.backstretch).not.toHaveBeenCalled();
        expect($('body').data('backstretch')).toBe(current);
    });

    it('handles repeated deactivation and destruction harmlessly', async () => {
        const wrapper = await mountBackground();
        const instance = $('body').data('backstretch');
        $.backstretch.mockClear();
        wrapper.vm.$options.deactivated[0].call(wrapper.vm);
        wrapper.vm.$options.deactivated[0].call(wrapper.vm);
        wrapper.destroy();
        expect(instance.destroy).toHaveBeenCalledTimes(1);
        expect($.backstretch).not.toHaveBeenCalled();
    });

    it('updates opacity on the currently owned background', async () => {
        const wrapper = await mountBackground();
        $wrap.css.mockClear();
        $wrap.fadeIn.mockClear();
        store.state.config.layout.fanartBackgroundOpacity = 0.8;
        await wrapper.vm.$nextTick();
        expect($wrap.css).toHaveBeenCalledWith('opacity', 0.8);
        expect($wrap.fadeIn).toHaveBeenCalledWith(500);
    });

    it.each(['missing', 'replaced'])('ignores opacity changes when the global instance is %s', async state => {
        const wrapper = await mountBackground();
        if (state === 'replaced') {
            $.backstretch('new-background');
        } else {
            $('body').removeData('backstretch');
        }
        $wrap.css.mockClear();
        $wrap.fadeIn.mockClear();
        store.state.config.layout.fanartBackgroundOpacity = 0.8;
        await wrapper.vm.$nextTick();
        expect($wrap.css).not.toHaveBeenCalled();
        expect($wrap.fadeIn).not.toHaveBeenCalled();
    });
});
