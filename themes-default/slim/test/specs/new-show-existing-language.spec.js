import Vuex, { Store } from 'vuex';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { NewShow } from '../../src/components';

describe('NewShow existing-show language handling', () => {
    it('uses general.indexerDefaultLanguage when providedInfo.indexerLanguage is missing', async () => {
        const localVue = createLocalVue();
        localVue.use(Vuex);

        const post = jest.fn().mockResolvedValue({ data: { identifier: 'queue-item' } });

        const store = new Store({
            state: {
                config: {
                    general: {
                        indexerDefaultLanguage: 'es'
                    },
                    indexers: {}
                },
                auth: {
                    client: {
                        api: {
                            post
                        }
                    }
                }
            },
            getters: {
                indexerIdToName: () => () => 'tvdb'
            }
        });

        const wrapper = shallowMount(NewShow, {
            localVue,
            store,
            propsData: {
                providedInfo: {
                    use: true,
                    showId: 123,
                    showName: 'Some Show',
                    showDir: '/shows/Some Show',
                    indexerId: 1,
                    indexerLanguage: null,
                    unattended: false
                }
            },
            mocks: {
                $route: { name: 'addExistingShow' },
                $router: { push: jest.fn() },
                $snotify: { warning: jest.fn(), error: jest.fn() }
            }
        });

        await wrapper.vm.submitForm();

        expect(post).toHaveBeenCalledWith(
            'series',
            expect.objectContaining({
                options: expect.objectContaining({
                    language: 'es'
                })
            }),
            expect.any(Object)
        );
    });
});

