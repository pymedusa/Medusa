import Vue from 'vue';
import Vuex, { Store } from 'vuex';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { NewShowsExisting } from '../../src/components';

describe('NewShowsExisting language handling', () => {
    it('passes general.indexerDefaultLanguage as providedInfo.indexerLanguage when mounting NewShow', async () => {
        const localVue = createLocalVue();
        localVue.use(Vuex);

        const extendSpy = jest.spyOn(Vue, 'extend').mockImplementation(() => {
            return function({ propsData }) {
                this.propsData = propsData;
                this.$on = jest.fn();
                this.$mount = jest.fn();
                this.$destroy = jest.fn();
                this.$el = document.createElement('div');
                this.$el.closest = () => ({ remove: jest.fn() });
            };
        });

        const store = new Store({
            state: {
                config: {
                    general: {
                        indexerDefault: 0,
                        indexerDefaultLanguage: 'es'
                    },
                    indexers: {
                        indexers: {}
                    }
                },
                shows: {
                    queueitems: []
                },
                auth: {
                    client: {
                        api: {
                            get: jest.fn()
                        }
                    }
                }
            }
        });

        try {
            const wrapper = shallowMount(NewShowsExisting, {
                localVue,
                store
            });

            await wrapper.setData({
                dirList: [{
                    path: '/shows/Some Show',
                    alreadyAdded: false,
                    selected: true,
                    metadata: {
                        indexer: 1,
                        seriesId: 123,
                        seriesName: 'Some Show'
                    }
                }]
            });

            wrapper.vm.$refs['curdirindex-0'] = [{ after: jest.fn() }];
            wrapper.vm.openAddNewShow(0, true);

            expect(wrapper.vm.addShowComponents['curdirindex-0'].propsData.providedInfo.indexerLanguage).toBe('es');
        } finally {
            extendSpy.mockRestore();
        }
    });
});
