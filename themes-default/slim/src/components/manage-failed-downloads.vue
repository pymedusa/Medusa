<template>
    <div id="failed-downloads">
        <div class="row">
            <div class="col-lg-12">
                <button :disabled="!selected.length" class="btn-medusa btn-inline remove" @click="remove">
                    Remove Selected<span v-if="selected.length"> ({{selected.length}})</span>
                </button>

                <div class="h2footer pull-right" style="margin-bottom: 0.5em">
                    <b>Limit:</b>
                    <select v-model="limit" name="limit" id="limit" class="form-control form-control-inline input-sm">
                        <option value="100">100</option>
                        <option value="250">250</option>
                        <option value="500">500</option>
                        <option value="0">All</option>
                    </select>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-lg-12 vgt-table-styling">
                <vue-good-table
                    :columns="columns"
                    :rows="data"
                    :selectOptions="{
                        enabled: true,
                        selectOnCheckboxOnly: true, // only select when checkbox is clicked instead of the row
                        selectionInfoClass: 'select-info',
                        selectionText: 'selected',
                        clearSelectionText: 'clear'
                    }"
                    styleClass="vgt-table condensed"
                    @on-selected-rows-change="selected = $event.selectedRows"
                >
                    <template slot="table-row" slot-scope="props">
                        <span v-if="props.column.label === 'Provider'" class="align-center">
                            <img :src="`images/providers/${props.row.provider.imageName}`"
                                 :alt="props.row.provider.name" width="16"
                                 :title="props.row.provider.name"
                                 v-tooltip.right="props.row.provider.name"
                                 onError="this.onerror=null;this.src='images/providers/missing.png';"
                            >
                        </span>

                        <span v-else>
                            {{props.formattedRow[props.column.field]}}
                        </span>
                    </template>
                </vue-good-table>

            </div>
        </div>
    </div>
</template>

<script>
import { mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';
import { VTooltip } from 'v-tooltip';
import { humanFileSize } from '../utils/core';

export default {
    name: 'manage-failed-downloads',
    components: {
        VueGoodTable
    },
    directives: {
        tooltip: VTooltip
    },
    data() {
        return {
            limit: 100,
            data: [],
            columns: [{
                label: 'Release',
                field: 'release'
            }, {
                label: 'Size',
                field: 'size',
                formatFn: humanFileSize,
                type: 'number'
            }, {
                label: 'Provider',
                field: 'provider.name'
            }],
            selected: []
        };
    },
    mounted() {
        this.getFailed();
    },
    computed: {
        ...mapState({
            client: state => state.auth.client
        })
    },
    methods: {
        humanFileSize,
        async getFailed() {
            const { client, limit } = this;
            try {
                const { data } = await client.api.get('internal/getFailed', { params: { limit } });
                this.data = data;
            } catch (error) {
                this.$snotify.warning('error', 'Could not get failed logs');
            }
        },
        async remove() {
            const { client, selected } = this;
            if (selected.length === 0) {
                return;
            }

            try {
                await client.api.post('internal/removeFailed', {
                    remove: selected.map(row => row.id)
                });
                this.$snotify.success('removed', `Removed ${selected.length} failed rows`);
                this.getFailed();
            } catch (error) {
                this.$snotify.warning('error', 'Error while trying to removed failed');
            }
        }
    },
    watch: {
        limit() {
            this.getFailed();
        }
    }
};
</script>

<style scoped>
.remove {
    line-height: 1.5em;
}
</style>
