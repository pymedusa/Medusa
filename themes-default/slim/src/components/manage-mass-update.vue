<template>
    <div class="vgt-table-styling manage-update">
        <div class="header-with-buttons">
            <h1 class="header">
                Mass Update
            </h1>
            <div class="buttons">
                <button :disabled="!selectedShows.length" class="btn-medusa btn-inline" @click="$router.push({ name: 'manageMassEdit', params: { shows: selectedShows } })">
                    Edit Selected<span v-if="selectedShows.length"> ({{selectedShows.length}})</span>
                </button>
                <button class="btn-medusa btn-inline" @click="triggerActions">Trigger Actions</button>
            </div>
        </div>

        <vue-good-table
            :columns="columns"
            :rows="filteredShows"
            :search-options="{
                enabled: false
            }"
            :sort-options="{
                enabled: true,
                initialSortBy: getSortBy()
            }"
            :column-filter-options="{
                enabled: true
            }"
            :selectOptions="{
                enabled: true,
                selectOnCheckboxOnly: true, // only select when checkbox is clicked instead of the row
                selectionInfoClass: 'select-info',
                selectionText: 'Shows selected',
                clearSelectionText: 'clear'
            }"
            styleClass="vgt-table"
            @on-sort-change="saveSorting"
            @on-selected-rows-change="selectedShows = $event.selectedRows"
        >
            <template slot="column-filter" slot-scope="props">
                <span v-if="props.column.filterOptions.customFilter">
                    <input type="checkbox" :data-action="props.column.action" @click="actionCheckAllRows">
                </span>
            </template>

            <template #table-row="props">
                <span v-if="props.column.label === 'Show name'" class="title">
                    <app-link :href="`home/displayShow?showslug=${props.row.id.slug}`"><span>{{props.row.title}}</span></app-link>
                    <span v-show="props.row.errors && props.row.errors.length" class="error"> !</span>
                    <ul v-show="props.row.errors && props.row.errors.length">
                        <li v-for="error in props.row.errors" :key="error">{{error}}</li>
                    </ul>
                </span>

                <span v-else-if="props.column.label === 'Quality'" class="align-center">
                    <quality-pill v-if="props.row.quality !== 0" :quality="combinedQualities(props.row.config.qualities)" />
                </span>

                <span v-else-if="props.column.label === 'Sports'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.sports"
                                  @click="toggleConfigOption(props.row, 'sports')" />
                </span>

                <span v-else-if="props.column.label === 'Scene'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.scene"
                                  @click="toggleConfigOption(props.row, 'scene')" />
                </span>

                <span v-else-if="props.column.label === 'Anime'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.anime"
                                  @click="toggleConfigOption(props.row, 'anime')" />
                </span>

                <span v-else-if="props.column.label === 'Season folders'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.seasonFolders"
                                  @click="toggleConfigOption(props.row, 'seasonFolders')" />
                </span>

                <span v-else-if="props.column.label === 'DVD order'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.dvdOrder"
                                  @click="toggleConfigOption(props.row, 'dvdOrder')" />
                </span>

                <span v-else-if="props.column.label === 'Paused'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.paused"
                                  @click="toggleConfigOption(props.row, 'paused')" />
                </span>

                <span v-else-if="props.column.label === 'Subtitle'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.subtitlesEnabled"
                                  @click="toggleConfigOption(props.row, 'subtitlesEnabled')" />
                </span>

                <span v-else-if="props.column.label === 'Update'" class="align-center">
                    <input :disabled="inQueueOrStarted('update', props.row.id.slug)" type="checkbox" class="bulkCheck" id="updateCheck"
                           :data-action="props.column.action" :data-show="props.row.id.slug" @input="updateActions($event, props.row.id.slug)"
                    >
                </span>

                <span v-else-if="props.column.label === 'Rescan'" class="align-center">
                    <input :disabled="inQueueOrStarted('rescan', props.row.id.slug)" type="checkbox" class="bulkCheck" id="updateRefresh"
                           :data-action="props.column.action" :data-show="props.row.id.slug" @input="updateActions($event, props.row.id.slug)"
                    >
                </span>

                <span v-else-if="props.column.label === 'Rename'" class="align-center">
                    <input :disabled="inQueueOrStarted('rename', props.row.id.slug)" type="checkbox" class="bulkCheck" id="updateRename"
                           :data-action="props.column.action" :data-show="props.row.id.slug" @input="updateActions($event, props.row.id.slug)"
                    >
                </span>

                <span v-else-if="props.column.label === 'Search subtitle'" class="align-center">
                    <input :disabled="inQueueOrStarted('subtitle', props.row.id.slug)" type="checkbox" class="bulkCheck" id="updateSubtitle"
                           :data-action="props.column.action" :data-show="props.row.id.slug" @input="updateActions($event, props.row.id.slug)"
                    >
                </span>

                <span v-else-if="props.column.label === 'Delete'" class="align-center">
                    <input :disabled="inQueueOrStarted('delete', props.row.id.slug)" type="checkbox" class="bulkCheck" id="updateDelete"
                           :data-action="props.column.action" :data-show="props.row.id.slug" @input="updateActions($event, props.row.id.slug)"
                    >
                </span>

                <span v-else-if="props.column.label === 'Remove'" class="align-center">
                    <input :disabled="inQueueOrStarted('remove', props.row.id.slug)" type="checkbox" class="bulkCheck" id="updateRemove"
                           :data-action="props.column.action" :data-show="props.row.id.slug" @input="updateActions($event, props.row.id.slug)"
                    >
                </span>

                <span v-else-if="props.column.label === 'Update image'" class="align-center">
                    <input type="checkbox" class="bulkCheck" id="updateImage" :data-action="props.column.action"
                           :data-show="props.row.id.slug" @input="updateActions($event, props.row.id.slug)"
                    >
                </span>

                <span v-else>
                    {{props.formattedRow[props.column.field]}}
                </span>
            </template>
        </vue-good-table>
    </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';
import { showlistTableMixin } from '../mixins/show-list';
import { manageCookieMixin } from '../mixins/manage-cookie';
import { combineQualities } from '../utils/core';
import { AppLink, QualityPill, StateSwitch } from './helpers';

export default {
    name: 'manage-mass-update',
    components: {
        AppLink,
        StateSwitch,
        QualityPill,
        VueGoodTable
    },
    mixins: [
        showlistTableMixin,
        manageCookieMixin('mass-update')
    ],
    data() {
        const { getCookie } = this;
        return {
            columns: [{
                label: 'Show name',
                field: 'title',
                filterOptions: {
                    enabled: true
                },
                sortFn: this.sortTitle,
                hidden: getCookie('Show name')
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
                label: 'Sports',
                field: 'config.sports',
                type: 'boolean',
                filterOptions: {
                    enabled: true,
                    placeholder: '--no filter-- ',
                    filterDropdownItems: [
                        { value: true, text: 'yes' },
                        { value: false, text: 'no' }
                    ]
                },
                hidden: getCookie('Sports')
            }, {
                label: 'Scene',
                field: 'config.scene',
                type: 'boolean',
                filterOptions: {
                    enabled: true,
                    placeholder: '--no filter-- ',
                    filterDropdownItems: [
                        { value: true, text: 'yes' },
                        { value: false, text: 'no' }
                    ]
                },
                hidden: getCookie('Scene')
            }, {
                label: 'Anime',
                field: 'config.anime',
                type: 'boolean',
                filterOptions: {
                    enabled: true,
                    placeholder: '--no filter-- ',
                    filterDropdownItems: [
                        { value: true, text: 'yes' },
                        { value: false, text: 'no' }
                    ]
                },
                hidden: getCookie('Anime')
            }, {
                label: 'Season folders',
                field: 'config.seasonFolders',
                type: 'boolean',
                filterOptions: {
                    enabled: true,
                    placeholder: '--no filter-- ',
                    filterDropdownItems: [
                        { value: true, text: 'yes' },
                        { value: false, text: 'no' }
                    ]
                },
                hidden: getCookie('Season folders')
            }, {
                label: 'DVD order',
                field: 'config.dvdOrder',
                type: 'boolean',
                filterOptions: {
                    enabled: true,
                    placeholder: '--no filter-- ',
                    filterDropdownItems: [
                        { value: true, text: 'yes' },
                        { value: false, text: 'no' }
                    ]
                },
                hidden: getCookie('DVD order')
            }, {
                label: 'Paused',
                field: 'config.paused',
                type: 'boolean',
                filterOptions: {
                    enabled: true,
                    placeholder: '--no filter-- ',
                    filterDropdownItems: [
                        { value: true, text: 'yes' },
                        { value: false, text: 'no' }
                    ]
                },
                hidden: getCookie('Paused')
            }, {
                label: 'Subtitle',
                field: 'config.subtitlesEnabled',
                type: 'boolean',
                filterOptions: {
                    enabled: true,
                    placeholder: '--no filter-- ',
                    filterDropdownItems: [
                        { value: true, text: 'yes' },
                        { value: false, text: 'no' }
                    ]
                },
                hidden: getCookie('Subtitle')
            }, {
                label: 'Default Ep Status',
                field: 'config.defaultEpisodeStatus',
                filterOptions: {
                    enabled: true,
                    placeholder: '--no filter-- ',
                    filterDropdownItems: []
                },
                hidden: getCookie('Default Ep Status')
            }, {
                label: 'Status',
                field: 'status',
                filterOptions: {
                    enabled: true,
                    placeholder: '--no filter-- ',
                    filterDropdownItems: []
                },
                hidden: getCookie('Status')
            }, {
                label: 'Update',
                field: 'update',
                filterOptions: {
                    customFilter: true
                },
                sortable: false,
                action: 'update',
                hidden: getCookie('Update')
            }, {
                label: 'Rescan',
                field: 'rescan',
                sortable: false,
                filterOptions: {
                    customFilter: true
                },
                action: 'rescan',
                hidden: getCookie('Rescan')
            }, {
                label: 'Rename',
                field: 'rename',
                sortable: false,
                filterOptions: {
                    customFilter: true
                },
                action: 'rename',
                hidden: getCookie('Rename')
            }, {
                label: 'Search subtitle',
                field: 'searchsubtitle',
                sortable: false,
                filterOptions: {
                    customFilter: true
                },
                action: 'subtitle',
                hidden: getCookie('Search subtitle')
            }, {
                label: 'Delete',
                field: 'delete',
                sortable: false,
                filterOptions: {
                    customFilter: true
                },
                action: 'delete',
                hidden: getCookie('Delete')
            }, {
                label: 'Remove',
                field: 'remove',
                sortable: false,
                filterOptions: {
                    customFilter: true
                },
                action: 'remove',
                hidden: getCookie('Remove')
            }, {
                label: 'Update image',
                field: 'updateimage',
                sortable: false,
                filterOptions: {
                    customFilter: true
                },
                action: 'image',
                hidden: getCookie('Update image')
            }],
            massUpdateActions: {
                update: [],
                rescan: [],
                rename: [],
                subtitle: [],
                delete: [],
                remove: [],
                image: []
            },
            errors: {},
            selectedShows: []
        };
    },
    computed: {
        ...mapState({
            general: state => state.config.general,
            shows: state => state.shows.shows,
            layout: state => state.config.layout,
            showQueue: state => state.config.system.showQueue,
            showQueueItems: state => state.shows.queueitems,
            client: state => state.auth.client
        }),
        filteredShows() {
            const { shows, errors } = this;
            if (Object.keys(errors).length === 0) {
                return shows;
            }
            return shows.map(show => {
                if (errors[show.id.slug]) {
                    show.errors = errors[show.id.slug];
                }
                return show;
            });
        }
    },
    methods: {
        ...mapActions({
            getShowQueue: 'getShowQueue'
        }),
        combinedQualities(quality) {
            const { allowed, preferred } = quality;
            return combineQualities(allowed, preferred);
        },
        /**
         * Keep the Object this.massUpdateActions up2date with the checks.
         * @param {Event} event Click event.
         * @param {string} showSlug Show slug.
         */
        updateActions(event, showSlug) {
            const { action } = event.currentTarget.dataset;
            const { checked } = event.currentTarget;
            if (checked && !this.massUpdateActions[action].includes(showSlug)) {
                this.massUpdateActions[action].push(showSlug);
            }

            if (!checked) {
                this.massUpdateActions[action] = this.massUpdateActions[action].filter(show => show !== showSlug);
            }
        },
        clearActions() {
            this.massUpdateActions = {
                update: [],
                rescan: [],
                rename: [],
                subtitle: [],
                delete: [],
                remove: [],
                image: []
            };
            for (const action of ['update', 'rescan', 'rename', 'subtitle', 'delete', 'remove', 'image']) {
                document.querySelectorAll(`[data-action="${action}"]`).forEach(el => {
                    el.checked = false;
                });
            }
        },
        actionCheckAllRows(event) {
            const { checked } = event.currentTarget;
            const { action } = event.currentTarget.dataset;
            this.massUpdateActions = {
                update: [],
                rescan: [],
                rename: [],
                subtitle: [],
                delete: [],
                remove: [],
                image: []
            };
            document.querySelectorAll(`[data-action="${action}"]`)
                .forEach(el => {
                    if (el.dataset.show) {
                        el.checked = checked;
                        // If checked add this showslug to the massUpdateActions.
                        if (checked && !this.massUpdateActions[action].includes(el.dataset.show)) {
                            this.massUpdateActions[action].push(el.dataset.show);
                        }
                    }
                });

            if (!checked) {
                this.massUpdateActions[action] = [];
            }
        },
        async triggerActions() {
            const { massUpdateActions } = this;

            try {
                const { data } = await this.client.api.post('massupdate', massUpdateActions);
                if (Object.keys(data.shows).length > 0) {
                    this.errors = data.shows;
                }
                // Get new queue.
                this.getShowQueue();
                this.clearActions();
            } catch (error) {
                this.$snotify.warning('error', 'Error trying to queue actions');
            }
        },
        /**
         * Create an object to track the queue/started status for the different actions.
         * @param {string} queueType queue type
         * @param {string} showSlug show slug
         * @returns {boolean} True if the show is in a queue or started
         */
        inQueueOrStarted(queueType, showSlug) {
            const { showQueue, showQueueItems } = this;
            const queueItemNames = new Map([
                ['update', 'UPDATE'],
                ['rescan', 'REFRESH'],
                ['rename', 'RENAME'],
                ['subtitle', 'SUBTITLE'],
                ['delete', 'REMOVE-SHOW'],
                ['remove', 'REMOVE-SHOW']
            ]);

            const showInQueue = showQueue?.find(queue => queue.queueType.toLowerCase() === queueType && queue.showSlug === showSlug);
            const filteredShowQueueItems = showQueueItems?.filter(
                queue => queue.name === queueItemNames.get(queueType) && queue.show.id.slug === showSlug
            );
            if (filteredShowQueueItems.filter(queue => !queue.inProgress).length > 0) {
                return false;
            }

            return Boolean(showInQueue || filteredShowQueueItems.length);
        },
        async toggleConfigOption(show, option) {
            const { config } = show;
            show.config[option] = !show.config[option];
            const data = {
                config: { [option]: config[option] }
            };

            try {
                await this.client.api.patch(`series/${show.id.slug}`, data);
                this.$snotify.success(
                    `${data.config[option] ? 'enabled' : 'disabled'} show option ${option}`,
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to save "${show.title}": ${error.message || 'Unknown'}`,
                    'Error'
                );
            }
        }
    },
    watch: {
        shows(shows) {
            const defaultEpColumn = this.columns.find(column => column.field === 'config.defaultEpisodeStatus');
            const defaultEpSet = new Set(shows.map(show => show.config.defaultEpisodeStatus));
            defaultEpColumn.filterOptions.filterDropdownItems = [...defaultEpSet].map(status => ({ text: status, value: status }));

            const statusColumn = this.columns.find(column => column.field === 'status');
            const statusSet = new Set(shows.map(show => show.status));
            statusColumn.filterOptions.filterDropdownItems = [...statusSet].map(status => ({ text: status, value: status }));
        }
    }
};
</script>
<style scoped>
.header-with-buttons {
    display: inline-block;
    width: 100%;
}

.header-with-buttons > h1 {
    float: left;
}

.header-with-buttons > div {
    float: right;
    height: 69px;
    display: flex;
    vertical-align: bottom;
    align-items: flex-end;
}

.title span.error {
    font-size: 1em;
    color: red;
    font-weight: 800;
}

.title {
    position: relative;
}

.title ul {
    display: none;
    background-color: rgb(95, 95, 95);
    font-size: 14px;
    border: 1px solid rgb(125, 125, 125);
    z-index: 1;
    width: auto;
    white-space: nowrap;
    padding: 2px 5px 2px 5px;
    position: absolute;
    left: 110%;
    top: 0;
}

.title li {
    list-style-type: none;
    text-align: left;
}

.title:hover ul {
    display: block;
}

.buttons button:first-child {
    margin-right: 5px;
}
</style>
