import Vuex from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import { SubtitleSearch } from '../../src/components';
import { SubtitleSearchResults } from '../__fixtures__/subtitle-search';

describe('SubtitleSearch.test.js', () => {
    let localVue;
    let store;
    let routerBase;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);
        routerBase = '/'; // This might be '/webroot'
    });

    it('renders subtitle component, no subtitles found', () => {
        const manualSearch = () => {
            const { results: manualSubtitleSearchResults } = SubtitleSearchResults;

            this.displayQuestion = false;
            this.loading = false;
            this.subtitles.push(...manualSubtitleSearchResults);
        };

        const wrapper = shallowMount(SubtitleSearch, {
            localVue,
            store,
            methods: { manualSearch }
        });

        expect(wrapper.element).toMatchSnapshot();
    });
});
