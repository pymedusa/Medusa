<script>
import { mapActions, mapState } from 'vuex';

export default {
    name: 'history',
    template: '#history-template',
    data() {
        return {
            layoutOptions: [
                { value: 'compact', text: 'Compact' },
                { value: 'detailed', text: 'Detailed' }
            ]
        };
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            // Renamed because of the computed property 'layout'.
            stateLayout: state => state.config.layout
        }),
        historyLayout: {
            get() {
                const { stateLayout } = this;
                return stateLayout.history;
            },
            set(layout) {
                const { setLayout } = this;
                const page = 'history';
                setLayout({ page, layout });
            }
        }
    },
    mounted() {
        const unwatch = this.$watch('stateLayout.history', () => {
            unwatch();
            const { historyLayout: layout, config } = this;

            $('#historyTable:has(tbody tr)').tablesorter({
                widgets: ['saveSort', 'zebra', 'filter'],
                sortList: [[0, 1]],
                textExtraction: (function() {
                    if (layout === 'detailed') {
                        return {
                            // 0: Time, 1: Episode, 2: Action, 3: Provider, 4: Quality
                            0: node => $(node).find('time').attr('datetime'),
                            1: node => $(node).find('a').text(),
                            4: node => $(node).attr('quality')
                        };
                    }
                    // 0: Time, 1: Episode, 2: Snatched, 3: Downloaded
                    const compactExtract = {
                        0: node => $(node).find('time').attr('datetime'),
                        1: node => $(node).find('a').text(),
                        2: node => $(node).find('img').attr('title') === undefined ? '' : $(node).find('img').attr('title'),
                        3: node => $(node).text()
                    };
                    if (config.subtitles.enabled) {
                        // 4: Subtitled, 5: Quality
                        compactExtract[4] = node => $(node).find('img').attr('title') === undefined ? '' : $(node).find('img').attr('title');
                        compactExtract[5] = node => $(node).attr('quality');
                    } else {
                        // 4: Quality
                        compactExtract[4] = node => $(node).attr('quality');
                    }
                    return compactExtract;
                })(),
                headers: (function() {
                    if (layout === 'detailed') {
                        return {
                            0: { sorter: 'realISODate' }
                        };
                    }
                    return {
                        0: { sorter: 'realISODate' },
                        2: { sorter: 'text' }
                    };
                })()
            });
        });

        $('#history_limit').on('change', function() {
            window.location.href = $('base').attr('href') + 'history/?limit=' + $(this).val();
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
</style>
