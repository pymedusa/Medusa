import pretty from 'pretty-bytes';
import { mapGetters, mapState } from 'vuex';

/**
 * Vue bindings for the simple, small poster and banner layouts.
 * @returns {void}
 */
export const showlistTableMixin = {
    data() {
        const { getCookie } = this;
        return {
            columns: [{
                label: 'Next Ep',
                field: 'nextAirDate',
                type: 'date',
                sortable: true,
                dateInputFormat: 'yyyy-MM-dd\'T\'HH:mm:ssXXX',
                dateOutputFormat: 'yyyy-MM-dd\'T\'HH:mm:ssXXX',
                sortFn: this.sortDateNext,
                hidden: getCookie('Next Ep')
            }, {
                label: 'Prev Ep',
                field: 'prevAirDate',
                type: 'date',
                sortable: true,
                dateInputFormat: 'yyyy-MM-dd\'T\'HH:mm:ssXXX',
                dateOutputFormat: 'yyyy-MM-dd\'T\'HH:mm:ssXXX',
                sortFn: this.sortDatePrev,
                hidden: getCookie('Prev Ep')
            }, {
                label: 'Show',
                field: 'title',
                filterOptions: {
                    enabled: true
                },
                sortFn: this.sortTitle,
                hidden: getCookie('Show')
            }, {
                label: 'Network',
                field: 'network',
                filterOptions: {
                    enabled: true
                },
                hidden: getCookie('Network')
            }, {
                label: 'Indexer',
                field: 'indexer',
                filterOptions: {
                    enabled: true,
                    filterDropdownItems: ['tvdb', 'tvmaze', 'tmdb']
                },
                hidden: getCookie('Indexer')
            }, {
                label: 'Quality',
                field: 'config.qualities',
                filterOptions: {
                    enabled: true,
                    filterFn: this.qualityColumnFilterFn
                },
                sortable: false,
                hidden: getCookie('Quality')
            }, {
                label: 'Downloads',
                field: 'stats.tooltip.percentage',
                sortFn: this.sortDownloads,
                type: 'boolean',
                hidden: getCookie('Downloads')
            }, {
                label: 'Size',
                type: 'number',
                field: 'stats.episodes.size',
                hidden: getCookie('Size')
            }, {
                label: 'Active',
                field: this.fealdFnActive,
                filterOptions: {
                    enabled: true,
                    filterDropdownItems: [
                        { value: true, text: 'yes' },
                        { value: false, text: 'no' }
                    ]
                },
                type: 'boolean',
                hidden: getCookie('Active')
            }, {
                label: 'Status',
                field: 'status',
                filterOptions: {
                    enabled: true
                },
                hidden: getCookie('Status')
            }, {
                label: 'Xem',
                field: this.fealdFnXem,
                filterOptions: {
                    enabled: true,
                    filterDropdownItems: [
                        { value: true, text: 'yes' },
                        { value: false, text: 'no' }
                    ]
                },
                type: 'boolean',
                hidden: getCookie('Xem')
            }]
        };
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            indexerConfig: state => state.config.indexers.indexers,
            stateLayout: state => state.config.layout,
            qualityValues: state => state.config.consts.qualities.values
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime',
            showsInLists: 'showsInLists'
        }),
        maxNextAirDate() {
            const { shows } = this;
            return Math.max(...shows.filter(show => show.nextAirDate).map(show => Date.parse(show.nextAirDate)));
        }
    },
    methods: {
        prettyBytes: bytes => pretty(bytes),
        showIndexerUrl(show) {
            const { indexerConfig } = this;
            if (!show.indexer) {
                return;
            }

            const id = show.id[show.indexer];
            const indexerUrl = indexerConfig[show.indexer].showUrl;

            return `${indexerUrl}${id}`;
        },
        parsePrevDateFn(row) {
            const { fuzzyParseDateTime } = this;
            if (row.prevAirDate) {
                console.log(`Calculating time for show ${row.title} prev date: ${row.prevAirDate}`);
                return fuzzyParseDateTime(row.prevAirDate);
            }

            return '';
        },
        parseNextDateFn(row) {
            const { fuzzyParseDateTime } = this;
            if (row.nextAirDate) {
                console.log(`Calculating time for show ${row.title} next date: ${row.nextAirDate}`);
                return fuzzyParseDateTime(row.nextAirDate);
            }

            return '';
        },
        fealdFnXem(row) {
            return row.xemNumbering && row.xemNumbering.length !== 0;
        },
        fealdFnActive(row) {
            return row.config && !row.config.paused && row.status === 'Continuing';
        },
        sortDateNext(x, y) {
            const { maxNextAirDate } = this;

            if (x === null && y === null) {
                return 0;
            }

            if (x === null || y === null) {
                return x === null ? 1 : -1;
            }

            // Convert to timestamps
            x = Date.parse(x);
            y = Date.parse(y);

            // This next airdate lies in the past. We need to correct this.
            if (x < Date.now()) {
                x += maxNextAirDate;
            }

            if (y < Date.now()) {
                y += maxNextAirDate;
            }

            return (x < y ? -1 : (x > y ? 1 : 0));
        },
        sortDatePrev(x, y) {
            if (x === null && y === null) {
                return 0;
            }

            // Standardize dates and nulls
            x = x ? Date.parse(x) : 0;
            y = y ? Date.parse(y) : 0;

            if (x === null || y === null) {
                return x === null ? -1 : 1;
            }

            const xTsDiff = x - Date.now();
            const yTsDiff = y - Date.now();

            return xTsDiff < yTsDiff ? -1 : (xTsDiff > yTsDiff ? 1 : 0);
        },
        sortTitle(x, y) {
            const { stateLayout } = this;
            const { sortArticle } = stateLayout;

            let titleX = x;
            let titleY = y;

            if (sortArticle) {
                titleX = titleX.replace(/^((?:a(?!\s+to)n?)|the)\s/i, '').toLowerCase();
                titleY = titleY.replace(/^((?:a(?!\s+to)n?)|the)\s/i, '').toLowerCase();
            }

            return (titleX < titleY ? -1 : (titleX > titleY ? 1 : 0));
        },
        sortDownloads(x, y, _, rowX, rowY) {
            if ((x === 0 || x === 100) && x === y) {
                return rowX.stats.episodes.total < rowY.stats.episodes.total ? -1 : (rowX.stats.episodes.total < rowY.stats.episodes.total ? 1 : 0);
            }

            return x < y ? -1 : (x > y ? 1 : 0);
        },
        qualityColumnFilterFn(data, filterString) {
            const { qualityValues } = this;
            return [...data.allowed, ...data.preferred].map(q => qualityValues.find(qv => qv.value === q).name.includes(filterString)).some(isTrue => isTrue);
        }
    }
};
