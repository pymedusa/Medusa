import TestRename from '../../src/components/test-rename.vue';

describe('Returning to a show after renaming episodes', () => {
    let context;

    beforeEach(() => {
        context = {
            showSlug: 'tvdb123',
            episodeRenameList: [{ slug: 's1e1', selected: true }, { slug: 's1e2', selected: false }],
            client: { api: { post: jest.fn().mockResolvedValue({}) } },
            $store: { commit: jest.fn() },
            $router: { push: jest.fn() },
            $snotify: { error: jest.fn() }
        };
    });

    it('invalidates the renamed show before opening its new page instance', async () => {
        const rename = TestRename.methods.renameSelected.call(context);
        context.showSlug = 'tvdb456';
        await rename;

        expect(context.client.api.post).toHaveBeenCalledWith('series/tvdb123/operation', {
            type: 'RENAME_EPISODES', episodes: ['s1e1']
        }, { timeout: 120000 });
        expect(context.$store.commit).toHaveBeenCalledWith('invalidateShowEpisodeCache', { showSlug: 'tvdb123' });
        expect(context.$router.push).toHaveBeenCalledWith({ name: 'show', query: { showslug: 'tvdb123' } });
        expect(context.$store.commit.mock.invocationCallOrder[0]).toBeLessThan(context.$router.push.mock.invocationCallOrder[0]);
        expect(context.loading).toBe(false);
    });

    it('keeps the cache and page unchanged when renaming fails', async () => {
        context.client.api.post.mockRejectedValue(new Error('Rename failed'));

        await TestRename.methods.renameSelected.call(context);

        expect(context.$store.commit).not.toHaveBeenCalled();
        expect(context.$router.push).not.toHaveBeenCalled();
        expect(context.$snotify.error).toHaveBeenCalledTimes(1);
        expect(context.loading).toBe(false);
    });
});
