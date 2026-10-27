import Vuex, { Store } from 'vuex';
import { createLocalVue, mount } from '@vue/test-utils';
import vueCookies from 'vue-cookies';
import $ from 'jquery';
import ShowHistory from '../../src/components/show-history.vue';
import CurrentDownloads from '../../src/components/current-downloads.vue';

const ProviderCellTable = {
    name: 'ProviderCellTable',
    props: ['columns', 'rows'],
    render(h) {
        const column = this.columns.find(({ label }) => ['Provider', 'Provider/Group'].includes(label));
        return h('div', this.rows.map(row => this.$scopedSlots['table-row']({
            column,
            row,
            formattedRow: { [column.field]: row.provider && row.provider.id }
        })));
    }
};

const surfaces = [
    ['show history', ShowHistory],
    ['current downloads', CurrentDownloads]
];

describe('provider icon cells', () => {
    let previousQtip;

    beforeEach(() => {
        previousQtip = $.fn.qtip;
        $.fn.qtip = jest.fn(function() {
            return this;
        });
    });

    afterEach(() => {
        $.fn.qtip = previousQtip;
    });

    const mountSurface = (Component, row) => {
        const localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(vueCookies);
        const downloadRow = Object.assign({
            clientStatus: { status: [], string: [] }
        }, row);
        const store = new Store({
            state: {
                config: { general: {}, layout: {} },
                history: {
                    remote: { rows: [downloadRow] },
                    showHistory: {},
                    episodeHistory: {}
                }
            },
            actions: {
                getHistory: () => Promise.resolve(),
                getShowHistory: () => Promise.resolve(),
                getShowEpisodeHistory: () => Promise.resolve()
            },
            getters: {
                getSeasonHistory: () => () => [row],
                getEpisodeHistory: () => () => [row],
                fuzzyParseDateTime: () => value => value
            }
        });
        return mount(Component, {
            localVue,
            store,
            propsData: Component === ShowHistory ? {
                show: { id: { slug: 'tvdb123' } }, season: 1
            } : {},
            stubs: {
                VueGoodTable: ProviderCellTable
            }
        });
    };

    it.each(surfaces)('%s renders the configured provider imageName before any image error', async (label, Component) => {
        const row = {
            status: 2,
            statusName: 'Snatched',
            provider: { id: 'custom-provider-id', name: 'Digital Carnage', imageName: 'prowlarr.png' }
        };
        const wrapper = mountSurface(Component, row);

        await wrapper.vm.$nextTick();

        expect(wrapper.find('img').attributes('src')).toBe('images/providers/prowlarr.png');
        wrapper.destroy();
    });

    it.each(surfaces)('%s starts unresolved providers on the missing icon without triggering onerror', async (label, Component) => {
        const row = {
            status: 2,
            statusName: 'Snatched',
            provider: { id: 'tokyo_toshokan', name: 'Tokyo Toshokan', imageName: 'missing.png' }
        };
        const wrapper = mountSurface(Component, row);

        await wrapper.vm.$nextTick();

        expect(wrapper.find('img').attributes('src')).toBe('images/providers/missing.png');
        wrapper.destroy();
    });

    it('keeps subtitle and Downloaded show-history cells on their existing paths', async () => {
        const subtitleWrapper = mountSurface(ShowHistory, {
            status: 3,
            statusName: 'Subtitled',
            resource: 'eng',
            provider: { id: 'subtitle-provider', name: 'Subtitle Provider' }
        });
        await subtitleWrapper.vm.$nextTick();
        expect(subtitleWrapper.find('img').attributes('src')).toBe('images/subtitles/subtitle-provider.png');

        const downloadedWrapper = mountSurface(ShowHistory, {
            status: 4,
            statusName: 'Downloaded',
            releaseGroup: 'Known Group',
            provider: {}
        });
        await downloadedWrapper.vm.$nextTick();
        expect(downloadedWrapper.findAll('img')).toHaveLength(0);
        expect(downloadedWrapper.text()).toContain('Known Group');
        subtitleWrapper.destroy();
        downloadedWrapper.destroy();
    });
});
