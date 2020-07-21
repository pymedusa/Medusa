import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount, mount } from '@vue/test-utils';
import { SubtitleSearch } from '../../src/components';
import history from '../../src/store/modules/history';
import show from '../__fixtures__/show-detailed';
import { result as subtitleResult } from '../__fixtures__/subtitle-search';
import episodeHistory from '../__fixtures__/episode-history';
import episode from '../__fixtures__/show-episode';
import fixtures from '../__fixtures__/common';

describe('SubtitleSearch', () => {
    let localVue;
    let store;
    const state = {
        history: {
            history: [],
            page: 0,
            showHistory: {},
            episodeHistory: {
                tvdb5692427: {
                    s04e06: episodeHistory
                }
            }
        },
        config: {
            general: fixtures.state.config.general
        }
    };

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);

        store = new Store({
            modules: {
                history: {
                    getters: history.getters,
                    state: state.history
                },
                config: {
                    state: state.config
                }
            }
        });
        store.replaceState(state);
    });

    it('renders subtitle component with question', async () => {
        const wrapper = shallowMount(SubtitleSearch, {
            localVue,
            store,
            propsData: {
                show,
                episode
            }
        });

        wrapper.setData({
            displayQuestion: true
        });

        await wrapper.vm.$nextTick();
        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders subtitle component with manual subtitle results', async () => {
        const wrapper = mount(SubtitleSearch, {
            localVue,
            store,
            propsData: {
                show,
                episode
            }
        });

        wrapper.setData({
            subtitles: subtitleResult[0].subtitles,
            displayQuestion: false
        });

        await wrapper.vm.$nextTick();
        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders empty subtitle component', async () => {
        const wrapper = shallowMount(SubtitleSearch, {
            localVue,
            store,
            propsData: {
                show,
                episode
            }
        });

        wrapper.setData({
            displayQuestion: false
        });

        await wrapper.vm.$nextTick();
        expect(wrapper.element).toMatchSnapshot();
    });
});
