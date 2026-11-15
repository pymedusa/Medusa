import shows from '../../src/store/modules/shows';
import {
    ADD_SHOW,
    ADD_SHOW_CONFIG,
    ADD_SHOW_EPISODE,
    ADD_SHOW_SCENE_EXCEPTION,
    REMOVE_SHOW_SCENE_EXCEPTION,
    ADD_SHOW_CONFIG_TEMPLATE,
    REMOVE_SHOW_CONFIG_TEMPLATE
} from '../../src/store/mutation-types';

const makeShow = indexer => ({
    indexer,
    id: { [indexer]: 1399, slug: `${indexer}1399` },
    title: indexer === 'tvmaze' ? 'Big Giant Swords' : 'Game of Thrones',
    config: { aliases: [], searchTemplates: [], paused: false },
    seasons: []
});

describe.each([
    ['tvmaze', 'tmdb'],
    ['tmdb', 'tvmaze']
])('show mutations with %s before %s', (firstIndexer, secondIndexer) => {
    let state;
    let first;
    let second;
    let firstSnapshot;

    beforeEach(() => {
        first = makeShow(firstIndexer);
        second = makeShow(secondIndexer);
        state = { shows: [first, second] };
        firstSnapshot = JSON.parse(JSON.stringify(first));
    });

    const expectSeparateShows = () => {
        expect(state.shows[0]).toEqual(firstSnapshot);
        expect(state.shows.map(show => show.id.slug)).toEqual([first.id.slug, second.id.slug]);
    };

    it('adds different shows with equal numeric IDs without merging them', () => {
        state.shows = [];
        shows.mutations[ADD_SHOW](state, first);
        shows.mutations[ADD_SHOW](state, second);

        expectSeparateShows();
        expect(state.shows).toEqual([first, second]);
    });

    it('updates only the matching slug and preserves detailed data and search templates', () => {
        const template = { title: 'Existing template' };
        second.config.searchTemplates.push(template);
        const seasons = [{ season: 1, children: [{ slug: `${second.id.slug}s1e1`, season: 1, episode: 1 }] }];
        second.seasons = seasons;
        const update = { ...makeShow(secondIndexer), title: 'Updated title', config: {} };
        delete update.seasons;

        shows.mutations[ADD_SHOW](state, update);

        expectSeparateShows();
        expect(state.shows[1].title).toBe('Updated title');
        expect(state.shows[1].seasons).toEqual(seasons);
        expect(state.shows[1].config.searchTemplates).toEqual([template]);
    });

    it('updates configuration only for the matching slug', () => {
        shows.mutations[ADD_SHOW_CONFIG](state, { show: second, config: { paused: true } });

        expectSeparateShows();
        expect(state.shows[1].config.paused).toBe(true);
    });

    it('adds episodes only to the matching slug', () => {
        const episode = { slug: `${second.id.slug}s1e1`, season: 1, episode: 1 };

        shows.mutations[ADD_SHOW_EPISODE](state, { show: second, episodes: [episode] });

        expectSeparateShows();
        expect(state.shows[1].seasons[0].children).toEqual([episode]);
    });

    it('updates cached episodes only for the matching slug', () => {
        const episode = { slug: `${second.id.slug}s1e1`, season: 1, episode: 1, title: 'Updated' };
        second.seasons = [{ season: 1, children: [{ ...episode, title: 'Original' }] }];

        shows.mutations[ADD_SHOW_EPISODE](state, { show: second, episodes: [episode] });

        expectSeparateShows();
        expect(state.shows[1].seasons[0].children).toEqual([episode]);
    });

    it('adds aliases only to the matching slug', () => {
        const exception = { title: 'Alternative title', season: 1 };

        shows.mutations[ADD_SHOW_SCENE_EXCEPTION](state, { show: second, exception });

        expectSeparateShows();
        expect(second.config.aliases).toEqual([exception]);
    });

    it('removes aliases only from the matching slug', () => {
        const exception = { title: 'Alternative title', season: 1 };
        first.config.aliases.push({ ...exception });
        firstSnapshot = JSON.parse(JSON.stringify(first));
        second.config.aliases.push(exception);

        shows.mutations[REMOVE_SHOW_SCENE_EXCEPTION](state, { show: second, exception });

        expectSeparateShows();
        expect(second.config.aliases).toEqual([]);
    });

    it('adds search templates only to the matching slug', () => {
        const template = { title: 'Template', template: 'Search text', season: 1, seasonSearch: false };

        shows.mutations[ADD_SHOW_CONFIG_TEMPLATE](state, { show: second, template });

        expectSeparateShows();
        expect(second.config.searchTemplates).toEqual([template]);
    });

    it.each([true, false])('removes search templates only from the matching slug (with ID: %s)', withId => {
        const template = { title: 'Template', template: 'Search text', season: 1, seasonSearch: false };
        if (withId) {
            template.id = 1;
        }
        first.config.searchTemplates.push({ ...template });
        firstSnapshot = JSON.parse(JSON.stringify(first));
        second.config.searchTemplates.push(template);

        shows.mutations[REMOVE_SHOW_CONFIG_TEMPLATE](state, { show: second, template });

        expectSeparateShows();
        expect(second.config.searchTemplates).toEqual([]);
    });
});
