<script>
export default {
    name: 'status',
    template: '#status-template',
    mounted() {
        $('#schedulerStatusTable').tablesorter({
            widgets: ['saveSort', 'zebra'],
            textExtraction: {
                5(node) {
                    return $(node).data('seconds');
                },
                6(node) {
                    return $(node).data('seconds');
                }
            },
            headers: {
                5: {
                    sorter: 'digit'
                },
                6: {
                    sorter: 'digit'
                }
            }
        });
        $('#queueStatusTable').tablesorter({
            widgets: ['saveSort', 'zebra'],
            sortList: [[3, 0], [4, 0], [2, 1]]
        });
    }
};
</script>

<style>

</style>
