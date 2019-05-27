import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount, mount } from '@vue/test-utils';
import { SubtitleSearch } from '../../src/components';
import show from '../__fixtures__/show-detailed';
import { result } from '../__fixtures__/subtitle-search';

describe('SubtitleSearch', () => {
    let localVue;
    let store;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);
    });

    it('renders subtitle component with question', () => {
        const wrapper = shallowMount(SubtitleSearch, {
            localVue,
            store,
            propsData: {
                show: show,
                season: 4,
                episode: 6
            }
        });

        wrapper.setData({
            displayQuestion: true
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders subtitle component with manual subtitle results', () => {
        const wrapper = mount(SubtitleSearch, {
            localVue,
            store,
            propsData: {
                show: show,
                season: 4,
                episode: 6
            }
        });

        wrapper.setData({
            subtitles: result[0].subtitles,
            displayQuestion: false
        });

        expect(wrapper.element).toMatchSnapshot();
    });

    it('renders empty subtitle component', () => {
        const wrapper = shallowMount(SubtitleSearch, {
            localVue,
            store,
            propsData: {
                show: show,
                season: 4,
                episode: 6
            }
        });

        wrapper.setData({
            displayQuestion: false
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
