<template>
    <div class="history-wrapper">
        <div class="row">
            <div class="col-md-6 pull-right"> <!-- Controls -->
                <div class="layout-controls pull-right">
                    <div class="show-option">
                        <span>Limit:</span>
                        <select v-model="stateLayout.historyLimit" name="history_limit" id="history_limit" class="form-control form-control-inline input-sm">
                            <option value="10">10</option>
                            <option value="25">25</option>
                            <option value="50">50</option>
                            <option value="100">100</option>
                            <option value="250">250</option>
                            <option value="500">500</option>
                            <option value="750">750</option>
                            <option value="1000">1000</option>
                            <option value="0">All</option>
                        </select>
                    </div>
                    <div class="show-option">
                        <span> Layout:
                            <select v-model="layout" name="layout" class="form-control form-control-inline input-sm">
                                <option :value="option.value" v-for="option in layoutOptions" :key="option.value">{{ option.text }}</option>
                            </select>
                        </span>
                    </div>
                </div> <!-- layout controls -->
            </div>
        </div> <!-- row -->
        
        <div v-if="layout" class="row horizontal-scroll" :class="{ fanartBackground: stateLayout.fanartBackground }">
            <div class="col-md-12 top-15">
                <history-detailed v-if="layout === 'detailed'" />
                <history-compact v-else />
            </div>
        </div>
    </div>
</template>
<script>

import { mapActions, mapGetters, mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';
import { humanFileSize } from '../utils/core';
import QualityPill from './helpers/quality-pill.vue';
import HistoryDetailed from './history-detailed.vue';
import HistoryCompact from './history-compact.vue';

export default {
    name: 'show-history',
    components: {
        HistoryCompact,
        HistoryDetailed,
        VueGoodTable,
        QualityPill
    },
    data() {
        return {
            loading: false,
            loadingMessage: '',
            layoutOptions: [
                { value: 'compact', text: 'Compact' },
                { value: 'detailed', text: 'Detailed' }
            ]
        };
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            stateLayout: state => state.config.layout
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        layout: {
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
    methods: {
        humanFileSize,
        ...mapActions({
            setLayout: 'setLayout'
        }),
        close() {
            this.$emit('close');
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.remove();
        }
    },
    beforeCreate() {
        this.$store.dispatch('initHistoryStore');
	}
};
</script>
<style scoped>
</style>
