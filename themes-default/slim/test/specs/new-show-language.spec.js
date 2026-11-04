import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { NewShow } from '../../src/components';
import NewShowSearch from '../../src/components/new-show-search.vue';

describe('NewShow search language handling', () => {
    let localVue;
    let store;
    let post;
    const wrappers = [];

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);
        post = jest.fn().mockResolvedValue({ data: { identifier: 'queue-item' } });
        store = new Store({
            state: {
                config: {
                    general: { indexerDefaultLanguage: 'en' },
                    layout: { themeName: 'dark' },
                    indexers: { main: { validLanguages: ['en', 'de'] }, indexers: {} }
                },
                auth: { client: { api: { post } } }
            },
            getters: { indexerIdToName: () => () => 'tvdb' }
        });
    });

    afterEach(() => {
        wrappers.forEach(wrapper => wrapper.destroy());
        wrappers.length = 0;
    });

    const mount = component => {
        const wrapper = shallowMount(component, {
            localVue,
            store,
            router: new VueRouter({
                routes: [{ path: '/', name: 'addNewShow' }, { path: '/home', name: 'home' }]
            }),
            stubs: ['modal'],
            mocks: {
                $snotify: { warning: jest.fn(), error: jest.fn() }
            }
        });
        wrappers.push(wrapper);
        return wrapper;
    };

    it('emits the default language and subsequent dropdown changes', async () => {
        const search = mount(NewShowSearch);
        await search.vm.$nextTick();
        expect(search.emitted('update-language')).toEqual([['en']]);

        search.findComponent({ name: 'language-select' }).vm.$emit('update-language', 'de');
        await search.vm.$nextTick();
        expect(search.emitted('update-language')).toEqual([['en'], ['de']]);
    });

    it.each(['de', 'en'])('submits the selected language %s instead of losing it', async language => {
        const wrapper = mount(NewShow);
        await wrapper.setData({ selectedRootDir: '/tv' });
        const search = wrapper.findComponent(NewShowSearch);
        search.vm.$emit('update-language', language);
        search.vm.$emit('selected', {
            result: { slug: 'tvdb477793', indexerId: 1, showId: 477793 }
        });
        await wrapper.vm.submitForm();

        expect(post).toHaveBeenCalledWith('series', expect.objectContaining({
            id: { tvdb: 477793 },
            options: expect.objectContaining({ language })
        }), expect.any(Object));
    });

    it('uses the configured default if the search language has not been emitted', async () => {
        const wrapper = mount(NewShow);
        await wrapper.setData({
            selectedRootDir: '/tv',
            selectedShowSlug: 'tvdb477793',
            selectedShow: { indexerId: 1, showId: 477793 }
        });
        await wrapper.vm.submitForm();

        expect(post.mock.calls[0][1].options.language).toBe('en');
    });
});
