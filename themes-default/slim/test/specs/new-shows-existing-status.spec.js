import Vuex, { Store } from 'vuex';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import NewShowsExisting from '../../src/components/new-shows-existing.vue';
import showsModule from '../../src/store/modules/shows';

describe('NewShowsExisting queue status', () => {
    it.each([['Failed', false], ['Added', true]])('updates a running row to %s after a queue event', async (label, success) => {
        const localVue = createLocalVue();
        localVue.use(Vuex);
        const queueItem = { identifier: 'add-show-1', name: 'ADD', success: null, step: ['Queued'] };
        const store = new Store({
            state: {
                config: {
                    general: { indexerDefault: 0, indexerDefaultLanguage: 'en' },
                    indexers: { indexers: {} }
                },
                auth: { client: { api: { get: jest.fn() } } }
            },
            modules: {
                shows: { ...showsModule, state: { queueitems: [{ ...queueItem }] } }
            }
        });
        const wrapper = shallowMount(NewShowsExisting, {
            localVue, store,
            data() {
                return {
                    rootDirs: [{ path: '/shows', selected: true }],
                    dirList: [{ path: '/shows/Example', alreadyAdded: false, selected: true, metadata: {} }],
                    addedShowQueueItems: [{ ...queueItem, providedInfo: { curDirIndex: 0 } }]
                };
            }
        });
        try {
            const row = wrapper.find('#addRootDirTable tbody tr');
            expect(row.isVisible()).toBe(true);
            expect(row.find('.step-container > div').text()).toBe('Running...');

            await store.dispatch('updateShowQueueItem', {
                identifier: queueItem.identifier, name: 'ADD', success, inProgress: false,
                step: [success ? 'Show added' : 'Unable to add show']
            });
            await localVue.nextTick();

            expect(wrapper.find('#addRootDirTable tbody tr').element).toBe(row.element);
            expect(row.find('.step-container > div').text()).toBe(label);
            expect(row.text()).not.toContain('Running');
        } finally {
            wrapper.destroy();
        }
    });
});
