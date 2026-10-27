import Vuex, { Store } from 'vuex';
import { createLocalVue } from '@vue/test-utils';
import historyModule from '../../src/store/modules/history';

describe('Downloaded history updates', () => {
    let store;
    let refreshShowFiles;

    beforeEach(() => {
        const localVue = createLocalVue();
        localVue.use(Vuex);
        refreshShowFiles = jest.fn().mockResolvedValue(undefined);
        store = new Store({
            state: { config: { layout: { history: 'detailed' } } },
            actions: { refreshShowFiles },
            modules: {
                history: {
                    ...historyModule,
                    state: JSON.parse(JSON.stringify(historyModule.state))
                }
            }
        });
    });

    it.each(['compact', 'detailed'])('refreshes show files after a download in %s history', async layout => {
        store.state.config.layout.history = layout;
        const history = { series: 'tvdb123', statusName: 'Downloaded', season: 1, episode: 2 };

        await store.dispatch('updateHistory', history);

        expect(refreshShowFiles).toHaveBeenCalledWith(expect.any(Object), {
            showSlug: 'tvdb123',
            episodes: true,
            season: 1
        });
        expect(store.state.history.remote.rows).toEqual(layout === 'compact' ? [] : [history]);
    });

    it.each([0, undefined])('preserves the download season for specials or unknown seasons (%s)', async season => {
        await store.dispatch('updateHistory', { series: 'tvdb123', statusName: 'Downloaded', season, episode: 1 });

        expect(refreshShowFiles).toHaveBeenCalledWith(expect.any(Object), {
            showSlug: 'tvdb123', episodes: true, season
        });
    });

    it.each(['Snatched', 'Subtitled', 'Failed'])('does not refresh show files for %s history', async statusName => {
        const history = { series: 'tvdb123', statusName };

        await store.dispatch('updateHistory', history);

        expect(refreshShowFiles).not.toHaveBeenCalled();
        expect(store.state.history.remote.rows).toEqual([history]);
    });
});
