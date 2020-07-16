import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import vueCookies from 'vue-cookies';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { ShowHistory } from '../../src/components';
import historyModule from '../../src/store/modules/history';
import show from '../__fixtures__/show-detailed';
import episodeHistory from '../__fixtures__/episode-history';
import fixtures from '../__fixtures__/common';

describe('ShowHistory.test.js', () => {
    let localVue;
    let store;
    let { state } = fixtures;
    state = {
        ...state,
        ...{ history: {
            history: [],
            page: 0,
            showHistory: {},
            episodeHistory: {
                tvdb5692427: {
                    s04e06: episodeHistory
                }
            }
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
                    state: state.config.general
                },
                history: {
                    getters: historyModule.getters,
                    state: state.history,
                    actions: {
                        getShowEpisodeHistory: jest.fn(),
                        getShowHistory: jest.fn()
                    }
                },
                config: {
                    state: state.config
                }
            }
        });
    });

    it('renders show-history component', async () => {
        const wrapper = shallowMount(ShowHistory, {
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
