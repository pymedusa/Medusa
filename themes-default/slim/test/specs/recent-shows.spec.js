import Vuex, { Store } from 'vuex';
import { createLocalVue } from '@vue/test-utils';
import generalModule from '../../src/store/modules/config/general';

describe('Recent show configuration writes', () => {
    let store;
    let patch;
    let shows;

    beforeEach(() => {
        const localVue = createLocalVue();
        localVue.use(Vuex);
        shows = [1, 2, 3, 4, 5, 6].map(id => ({ showSlug: `tvdb${id}`, name: `Show ${id}` }));
        patch = jest.fn().mockResolvedValue({ data: {} });
        store = new Store({
            state: { auth: { client: { api: { patch } } } },
            modules: {
                general: { ...generalModule, state: { recentShows: shows.slice(0, 3) } }
            }
        });
    });

    it('does not write configuration when the same show is already first', async () => {
        await store.dispatch('setRecentShow', { ...shows[0] });

        expect(patch).not.toHaveBeenCalled();
        expect(store.state.general.recentShows).toEqual(shows.slice(0, 3));
    });

    it('compares show values without depending on object property order', async () => {
        await store.dispatch('setRecentShow', { name: shows[0].name, showSlug: shows[0].showSlug });

        expect(patch).not.toHaveBeenCalled();
    });

    it('writes once when a new show is visited repeatedly', async () => {
        await store.dispatch('setRecentShow', shows[4]);
        await store.dispatch('setRecentShow', { ...shows[4] });

        expect(patch).toHaveBeenCalledTimes(1);
        expect(patch).toHaveBeenCalledWith('config/main', {
            recentShows: [shows[4], ...shows.slice(0, 3)]
        });
    });

    it('persists an existing show moving to the first position', async () => {
        await store.dispatch('setRecentShow', shows[2]);

        expect(patch).toHaveBeenCalledWith('config/main', {
            recentShows: [shows[2], shows[0], shows[1]]
        });
    });

    it('persists a renamed show even if its slug is already first', async () => {
        const renamed = { ...shows[0], name: 'Renamed Show' };

        await store.dispatch('setRecentShow', renamed);

        expect(patch).toHaveBeenCalledTimes(1);
        expect(patch.mock.calls[0][1].recentShows[0]).toEqual(renamed);
    });

    it('preserves the five-show limit when adding a new show', async () => {
        store.state.general.recentShows = shows.slice(0, 5);

        await store.dispatch('setRecentShow', shows[5]);

        expect(patch).toHaveBeenCalledWith('config/main', {
            recentShows: [shows[5], ...shows.slice(0, 4)]
        });
    });

    it('persists truncation even when the visited show is already first', async () => {
        store.state.general.recentShows = shows;

        await store.dispatch('setRecentShow', shows[0]);

        expect(patch).toHaveBeenCalledWith('config/main', { recentShows: shows.slice(0, 5) });
    });

    it('persists duplicate removal even when the visited show is already first', async () => {
        store.state.general.recentShows = [shows[0], shows[1], shows[0]];

        await store.dispatch('setRecentShow', shows[0]);

        expect(patch).toHaveBeenCalledWith('config/main', { recentShows: shows.slice(0, 2) });
    });

    it('retries a failed save even after an identical visit while it was pending', async () => {
        let rejectSave;
        patch.mockImplementationOnce(() => new Promise((resolve, reject) => {
            rejectSave = reject;
        }));
        const failedSave = store.dispatch('setRecentShow', shows[4]).catch(error => error);
        await store.dispatch('setRecentShow', { ...shows[4] });
        rejectSave(new Error('Save failed'));
        await expect(failedSave).resolves.toEqual(new Error('Save failed'));

        expect(patch).toHaveBeenCalledTimes(1);
        expect(store.state.general.recentShows).toEqual(shows.slice(0, 3));
        await store.dispatch('setRecentShow', shows[4]);
        expect(patch).toHaveBeenCalledTimes(2);
        expect(store.state.general.recentShows[0]).toEqual(shows[4]);
    });

    it('does not overwrite a newer successful visit when an older save fails', async () => {
        let rejectSave;
        patch.mockImplementationOnce(() => new Promise((resolve, reject) => {
            rejectSave = reject;
        }));
        const failedSave = store.dispatch('setRecentShow', shows[3]).catch(error => error);
        await store.dispatch('setRecentShow', shows[4]);
        const latestShows = store.state.general.recentShows;
        rejectSave(new Error('Older save failed'));
        await expect(failedSave).resolves.toEqual(new Error('Older save failed'));

        expect(store.state.general.recentShows).toBe(latestShows);
        expect(store.state.general.recentShows[0]).toEqual(shows[4]);
    });

    it('retries when two failed saves leave an earlier unsaved list restored', async () => {
        let rejectFirst;
        let rejectSecond;
        patch.mockImplementationOnce(() => new Promise((resolve, reject) => {
            rejectFirst = reject;
        })).mockImplementationOnce(() => new Promise((resolve, reject) => {
            rejectSecond = reject;
        }));
        const firstSave = store.dispatch('setRecentShow', shows[3]).catch(error => error);
        const secondSave = store.dispatch('setRecentShow', shows[4]).catch(error => error);
        rejectFirst(new Error('First save failed'));
        await expect(firstSave).resolves.toEqual(new Error('First save failed'));
        rejectSecond(new Error('Second save failed'));
        await expect(secondSave).resolves.toEqual(new Error('Second save failed'));

        await store.dispatch('setRecentShow', shows[3]);
        await store.dispatch('setRecentShow', { ...shows[3] });

        expect(patch).toHaveBeenCalledTimes(3);
        expect(store.state.general.recentShows[0]).toEqual(shows[3]);
    });
});
