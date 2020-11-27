import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import vueCookies from 'vue-cookies';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { ShowResults } from '../../src/components';
import general from '../../src/store/modules/config/general';
import historyModule from '../../src/store/modules/history';
import providerModule from '../../src/store/modules/provider';
import show from '../__fixtures__/show-detailed';
import episodeHistory from '../__fixtures__/episode-history';
import fixtures from '../__fixtures__/common';
import provider from '../__fixtures__/providers';

describe('ShowResults.test.js', () => {
    let localVue;
    let store;
    let { state } = fixtures;
    state = {
        ...state,
        ...{ provider },
        ...{ history: {
            history: [],
            page: 0,
            showHistory: {},
            episodeHistory: {
                tvdb5692427: {
                    s04e06: episodeHistory
                }
            }
        } },
        ...{ search: {
            queueitems: []
        } }
    };

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);
        localVue.use(vueCookies);

        store = new Store({
            modules: {
                general: {
                    getters: general.getters,
                    state: state.config.general
                },
                history: {
                    getters: historyModule.getters,
                    state: state.history
                },
                provider: {
                    getters: providerModule.getters,
                    state: state.provider,
                    actions: {
                        getProviders: jest.fn(),
                        getProviderCacheResults: jest.fn().mockImplementation(() => Promise.resolve({
                            providersSearched: 0,
                            totalSearchResults: []
                        }))
                    }
                },
                config: {
                    state: state.config
                },
                search: {
                    state: state.search
                }
            }
        });
    });

    it('renders show-results component', async () => {
        const wrapper = shallowMount(ShowResults, {
            localVue,
            store,
            propsData: {
                show,
                season: 4,
                episode: 6
            }
        });

        await wrapper.vm.$nextTick();
        expect(wrapper.element).toMatchSnapshot();
    });
});
