<template>
    <div class="history-wrapper">
        <div class="row">
            <div class="col-md-6 pull-right"> <!-- Controls -->
                <div class="layout-controls pull-right">
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
        <backstretch :slug="config.randomShowSlug" />
    </div>
</template>
<script>

import { mapActions, mapGetters, mapState } from 'vuex';
import { humanFileSize } from '../utils/core';
import HistoryDetailed from './history-detailed.vue';
import HistoryCompact from './history-compact.vue';
import Backstretch from './backstretch.vue';

export default {
    name: 'show-history',
    components: {
        Backstretch,
        HistoryCompact,
        HistoryDetailed
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
    }
};
</script>
<style scoped>
</style>
