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
                hidden: getCookie('Show')
            }, {
                label: 'Network',
                field: 'network',
                hidden: getCookie('Network')
            }, {
                label: 'Indexer',
                field: 'indexer',
                hidden: getCookie('Indexer')
            }, {
                label: 'Quality',
                field: 'quality',
                sortable: false,
                hidden: getCookie('Quality')
            }, {
                label: 'Downloads',
                field: 'stats.tooltip.text',
                hidden: getCookie('Downloads')
            }, {
                label: 'Size',
                type: 'number',
                field: 'stats.episodes.size',
                hidden: getCookie('Size')
            }, {
                label: 'Active',
                field: this.fealdFnActive,
                type: 'boolean',
                hidden: getCookie('Active')
            }, {
                label: 'Status',
                field: 'status',
                hidden: getCookie('Status')
            }, {
                label: 'Xem',
                field: this.fealdFnXem,
                type: 'boolean',
                hidden: getCookie('Xem')
            }]
        };
    },
    computed: {
        ...mapState({
            config: state => state.config,
            indexerConfig: state => state.indexers.indexers,
            stateLayout: state => state.layout
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        })
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
            if ((x === null || y === null) && x !== y) {
                return x < y ? 1 : -1;
            }
            return (x < y ? -1 : (x > y ? 1 : 0));
        },
        sortDatePrev(x, y) {
            if ((x === null || y === null) && x !== y) {
                return x < y ? 1 : -1;
            }
            return (x < y ? -1 : (x > y ? 1 : 0));
        }
    }
};
