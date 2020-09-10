<script>
import { mapActions, mapState } from 'vuex';
import { AppLink } from './helpers';

export default {
    name: 'schedule',
    template: '#schedule-template',
    components: {
        AppLink
    },
    data() {
        return {
            layoutOptions: [
                { value: 'poster', text: 'Poster' },
                { value: 'calendar', text: 'Calendar' },
                { value: 'banner', text: 'Banner' },
                { value: 'list', text: 'List' }
            ]
        };
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            // Renamed because of the computed property 'layout'.
            stateLayout: state => state.config.layout
        }),
        header() {
            return this.$route.meta.header;
        },
        scheduleLayout: {
            get() {
                const { stateLayout } = this;
                return stateLayout.schedule;
            },
            set(layout) {
                const { setLayout } = this;
                const page = 'schedule';
                setLayout({ page, layout });
            }
        },
        themeSpinner() {
            const { stateLayout } = this;
            return stateLayout.themeName === 'dark' ? '-dark' : '';
        }
    },
    mounted() {
        // $store.dispatch('getShows');

        this.$root.$once('loaded', () => {
            const { scheduleLayout, stateLayout, themeSpinner } = this;
            const { comingEps } = stateLayout;
            if (scheduleLayout === 'list') {
                const sortCodes = {
                    date: 0,
                    show: 2,
                    network: 5
                };
                const { sort } = comingEps;
                const sortList = (sort in sortCodes) ? [[sortCodes[sort], 0]] : [[0, 0]];

                $('#showListTable:has(tbody tr)').tablesorter({
                    widgets: ['stickyHeaders', 'filter', 'columnSelector', 'saveSort'],
                    sortList,
                    textExtraction: {
                        0: node => $(node).find('time').attr('datetime'),
                        1: node => $(node).find('time').attr('datetime'),
                        7: node => $(node).find('span').text().toLowerCase(),
                        8: node => $(node).find('a[data-indexer-name]').attr('data-indexer-name')
                    },
                    headers: {
                        0: { sorter: 'realISODate' },
                        1: { sorter: 'realISODate' },
                        2: { sorter: 'loadingNames' },
                        4: { sorter: 'loadingNames' },
                        7: { sorter: 'quality' },
                        8: { sorter: 'text' },
                        9: { sorter: false, filter: false }
                    },
                    widgetOptions: {
                        filter_columnFilters: true, // eslint-disable-line camelcase
                        filter_hideFilters: true, // eslint-disable-line camelcase
                        filter_saveFilters: true, // eslint-disable-line camelcase
                        columnSelector_mediaquery: false // eslint-disable-line camelcase
                    }
                });

                $.ajaxEpSearch();
            }

            if (['banner', 'poster'].includes(scheduleLayout)) {
                $.ajaxEpSearch({
                    size: 16,
                    loadingImage: `loading16${themeSpinner}.gif`
                });
                $('.ep_summary').hide();
                $('.ep_summaryTrigger').on('click', function() {
                    $(this).next('.ep_summary').slideToggle('normal', function() {
                        $(this).prev('.ep_summaryTrigger').prop('src', function(i, src) {
                            return $(this).next('.ep_summary').is(':visible') ? src.replace('plus', 'minus') : src.replace('minus', 'plus');
                        });
                    });
                });
            }

            $('#popover').popover({
                placement: 'bottom',
                html: true, // Required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', () => { // Bootstrap popover event triggered when the popover opens
                // call this function to copy the column selection code into the popover
                $.tablesorter.columnSelector.attachTo($('#showListTable'), '#popover-target');
            });
        });
    },
    methods: {
        ...mapActions({
            setLayout: 'setLayout'
        })
    }
};
</script>

<style scoped>
/* Also defined in style.css and dark.css, but i'm overwriting for light and dark, because the schedule table has coloring. */
td.tvShow a {
    color: rgb(0, 0, 0);
    text-decoration: none;
}

td.tvShow a:hover {
    cursor: pointer;
    color: rgb(66, 139, 202);
}
</style>
