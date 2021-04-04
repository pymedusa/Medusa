<template>
    <div class="horizontal-scroll">
        <vue-good-table v-if="getScheduleFlattened.length > 0"
                        :columns="columns"
                        :rows="getScheduleFlattened"
                        :class="{fanartOpacity: layout.fanartBackgroundOpacity}"
        >
            <template slot="table-row" slot-scope="props">
                <span v-if="props.column.label == 'Airdate'" class="align-center">
                    {{props.row.airdate ? fuzzyParseDateTime(props.row.airdate) : ''}}
                </span>

                <span v-else-if="props.column.label === 'Ends'" class="align-center">
                    {{props.row.airdate ? fuzzyParseDateTime(props.row.airdate) : ''}}
                </span>

                <span v-else-if="props.column.label === 'Quality'" class="align-center">
                    {{props.row.quality}}
                </span>

                <span v-else class="align-center">
                    {{props.formattedRow[props.column.field]}}
                </span>
            </template>
        </vue-good-table>

    </div> <!-- .horizontal-scroll -->
</template>
<script>
import { mapGetters, mapState } from 'vuex';
import { AppLink, ProgressBar, QualityPill } from '../helpers';
import { VueGoodTable } from 'vue-good-table';
import { manageCookieMixin } from '../../mixins/manage-cookie';

export default {
    name: 'list',
    components: {
        AppLink,
        ProgressBar,
        QualityPill,
        VueGoodTable
    },
    mixins: [
        manageCookieMixin('schedule'),
    ],
    // props: {
    //     layout: {
    //         validator: val => val === null || typeof val === 'string',
    //         required: true
    //     }
    // },
    data() {
        const { getCookie } = this;

        return {
            columns: [{
                label: 'Airdate',
                field: 'airdate',
                dateInputFormat: 'yyyy-MM-dd', // E.g. 07-09-2017 19:16:25
                dateOutputFormat: 'yyyy-MM-dd HH:mm:ss',
                type: 'date',
                hidden: getCookie('Airdate')
            }, {
                label: 'Ends',
                field: 'ends',
                hidden: getCookie('Ends')
            }, {
                label: 'Show',
                field: 'show_name',
                hidden: getCookie('Show')
            }, {
                label: 'Next Ep',
                field: 'nextEp',
                hidden: getCookie('Next Ep')
            }, {
                label: 'Next Ep Name',
                field: 'ep_name',
                hidden: getCookie('Next Ep Name')
            }, {
                label: 'Network',
                field: 'network',
                hidden: getCookie('Network')
            }, {
                label: 'Runtime',
                field: 'runtime',
                hidden: getCookie('Runtime')
            }, {
                label: 'Network',
                field: 'network',
                hidden: getCookie('Network')
            }, {
                label: 'Quality',
                field: 'quality',
                hidden: getCookie('Quality')
            }, {
                label: 'Indexers',
                field: 'indexers',
                hidden: getCookie('Indexers')
            }, {
                label: 'Search',
                field: 'search',
                hidden: getCookie('Search')
            }]
        }
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout 
        }),
        ...mapGetters([
            'getScheduleFlattened',
            'fuzzyParseDateTime'
        ])
    }
};
</script>

<style>
</style>
