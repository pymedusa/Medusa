<template>
<!-- < inherit file="/layouts/main.mako"/>
< !
    from medusa import app
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import statusStrings
    from medusa.helpers import remove_article
 >
< block name="scripts"> -->
    <div class="vgt-table-styling">
        <div class="header-with-buttons">
            <h1 class="header">
                Mass Update
            </h1>
            <div class="buttons">
                <button class="btn-medusa btn-inline">Edit Selected</button>
                <button class="btn-medusa btn-inline" @click="triggerActions">Trigger Actions</button>
            </div>
        </div>

        <vue-good-table
            v-if="shows.length > 0"
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
        >
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
                    <state-switch :theme="layout.themeName" :state="props.row.config.sports" />
                </span>

                <span v-else-if="props.column.label === 'Scene'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.scene" />
                </span>

                <span v-else-if="props.column.label === 'Anime'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.anime" />
                </span>

                <span v-else-if="props.column.label === 'Season folders'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.seasonFolders" />
                </span>

                <span v-else-if="props.column.label === 'DVD order'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.dvdOrder" />
                </span>

                <span v-else-if="props.column.label === 'Paused'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.paused" />
                </span>

                <span v-else-if="props.column.label === 'Subtitle'" class="align-center">
                    <state-switch :theme="layout.themeName" :state="props.row.config.subtitlesEnabled" />
                </span>

                <span v-else-if="props.column.label === 'Update'" class="align-center">
                    <input :disabled="inQueueOrStarted('update', props.row.id.slug)" type="checkbox" class="bulkCheck" id="updateCheck" data-action="update" @input="updateActions($event, props.row.id.slug)"/>
                </span>

                <span v-else-if="props.column.label === 'Refresh'" class="align-center">
                    <input :disabled="inQueueOrStarted('refresh', props.row.id.slug)" type="checkbox" class="bulkCheck" id="updateRefresh" data-action="refresh" @input="updateActions($event, props.row.id.slug)"/>
                </span>

                <span v-else-if="props.column.label === 'Rename'" class="align-center">
                    <input :disabled="inQueueOrStarted('rename', props.row.id.slug)" type="checkbox" class="bulkCheck" id="updateRename" data-action="rename" @input="updateActions($event, props.row.id.slug)"/>
                </span>

                <span v-else-if="props.column.label === 'Search subtitle'" class="align-center">
                    <input :disabled="inQueueOrStarted('subtitle', props.row.id.slug)" type="checkbox" class="bulkCheck" id="updateSubtitle" data-action="subtitle" @input="updateActions($event, props.row.id.slug)"/>
                </span>

                <span v-else-if="props.column.label === 'Delete'" class="align-center">
                    <input :disabled="inQueueOrStarted('delete', props.row.id.slug)" type="checkbox" class="bulkCheck" id="updateDelete" data-action="delete" @input="updateActions($event, props.row.id.slug)"/>
                </span>

                <span v-else-if="props.column.label === 'Remove'" class="align-center">
                    <input :disabled="inQueueOrStarted('remove', props.row.id.slug)" type="checkbox" class="bulkCheck" id="updateRemove" data-action="remove" @input="updateActions($event, props.row.id.slug)"/>
                </span>

                <span v-else-if="props.column.label === 'Update image'" class="align-center">
                    <input type="checkbox" class="bulkCheck" id="updateImage" data-action="image" @input="updateActions($event, props.row.id.slug)"/>
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
import { api } from '../api';

export default {
    name: 'manage-mass-update',
    components: {
        VueGoodTable
    },
    mixins: [
        showlistTableMixin,
        manageCookieMixin('mass-update')
    ],
    data() {
        const { getCookie } = this;
        const columns = [{
            label: 'Show name',
            field: 'title',
            filterOptions: {
                enabled: true
            },
            sortFn: this.sortTitle,
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
                filterDropdownItems: [
                    { value: true, text: 'yes' },
                    { value: false, text: 'no' }
                ]
            },
        }, {
            label: 'Scene',
            field: 'config.scene',
            type: 'boolean',
            filterOptions: {
                enabled: true,
                filterDropdownItems: [
                    { value: true, text: 'yes' },
                    { value: false, text: 'no' }
                ]
            },
        }, {
            label: 'Anime',
            field: 'config.anime',
            type: 'boolean',
            filterOptions: {
                enabled: true,
                filterDropdownItems: [
                    { value: true, text: 'yes' },
                    { value: false, text: 'no' }
                ]
            },
        }, {
            label: 'Season folders',
            field: 'config.seasonFolders',
            type: 'boolean',
            filterOptions: {
                enabled: true,
                filterDropdownItems: [
                    { value: true, text: 'yes' },
                    { value: false, text: 'no' }
                ]
            },
        }, {
            label: 'DVD order',
            field: 'config.dvdOrder',
            type: 'boolean',
            filterOptions: {
                enabled: true,
                filterDropdownItems: [
                    { value: true, text: 'yes' },
                    { value: false, text: 'no' }
                ]
            },
        }, {
            label: 'Paused',
            field: 'config.paused',
            type: 'boolean',
            filterOptions: {
                enabled: true,
                filterDropdownItems: [
                    { value: true, text: 'yes' },
                    { value: false, text: 'no' }
                ]
            },
        }, {
            label: 'Subtitle',
            field: 'config.subtitlesEnabled',
            type: 'boolean',
            filterOptions: {
                enabled: true,
                filterDropdownItems: [
                    { value: true, text: 'yes' },
                    { value: false, text: 'no' }
                ]
            }
        }, {
            label: 'Default Ep Status',
            field: 'config.defaultEpisodeStatus'
        }, {
            label: 'Status',
            field: 'status'
        }, {
            label: 'Update',
            field: 'update',
            sortable: false
        }, {
            label: 'Refresh',
            field: 'rescan',
            sortable: false
        }, {
            label: 'Rename',
            field: 'rename',
            sortable: false
        }, {
            label: 'Search subtitle',
            field: 'searchsubtitle',
            sortable: false
        }, {
            label: 'Delete',
            field: 'delete',
            sortable: false
        }, {
            label: 'Remove',
            field: 'remove',
            sortable: false
        }, {
            label: 'Update image',
            field: 'updateimage',
            sortable: false
        }]

        return {
            columns,
            massUpdateActions: {
                update: [],
                refresh: [],
                rename: [],
                subtitle: [],
                delete: [],
                remove: [],
                image: []
            },
            errors: {}
        }
    },
    // TODO: Replace with Object spread (`...mapState`)
    computed: {
        ...mapState({
            general: state => state.config.general,
            shows: state => state.shows.shows,
            layout: state => state.config.layout,
            showQueue: state => state.config.system.showQueue,
            showQueueItems: state => state.shows.queueitems
        }),
        filteredShows() {
            const { shows, errors } = this;
            if (!Object.keys(errors).length) {
                return shows;
            }
            return shows.map(show => {
                if (errors[show.id.slug]) {
                    show.errors = errors[show.id.slug];
                }
                return show;
            })
        }
    },
    mounted() {
        this.getShowQueue();
        $('.resetsorting').on('click', () => {
            $('table').trigger('filterReset');
        });

        $('#massUpdateTable:has(tbody tr)').tablesorter({
            sortList: [[1, 0]],
            textExtraction: {
                2(node) { return $(node).find('span').text().toLowerCase(); }, // eslint-disable-line brace-style
                3(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                4(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                5(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                6(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                7(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                8(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                9(node) { return $(node).find('img').attr('alt'); } // eslint-disable-line brace-style
            },
            widgets: ['zebra', 'filter', 'columnSelector'],
            headers: {
                0: { sorter: false, filter: false },
                1: { sorter: 'showNames' },
                2: { sorter: 'quality' },
                3: { sorter: 'sports' },
                4: { sorter: 'scene' },
                5: { sorter: 'anime' },
                6: { sorter: 'flatfold' },
                7: { sorter: 'paused' },
                8: { sorter: 'subtitle' },
                9: { sorter: 'default_ep_status' },
                10: { sorter: 'status' },
                11: { sorter: false },
                12: { sorter: false },
                13: { sorter: false },
                14: { sorter: false },
                15: { sorter: false },
                16: { sorter: false }
            },
            widgetOptions: {
                columnSelector_mediaquery: false // eslint-disable-line camelcase
            }
        });

        $('#popover').popover({
            placement: 'bottom',
            html: true, // Required if content has HTML
            content: '<div id="popover-target"></div>'
        }).on('shown.bs.popover', () => { // Bootstrap popover event triggered when the popover opens
            // call this function to copy the column selection code into the popover
            $.tablesorter.columnSelector.attachTo($('#massUpdateTable'), '#popover-target');
        });

        $(document.body).on('click', '.submitMassEdit', () => {
            const editArr = [];

            // $('.editCheck').each((index, element) => {
            //     if (element.checked === true) {
            //         < text>
            //         editArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            //         </ text>
            //     }
            // });

            if (editArr.length === 0) {
                return;
            }

            const submitForm = $('<form method=\'post\' action=\'' + $('base').attr('href') + 'manage/massEdit\'>' +
                '<input type=\'hidden\' name=\'toEdit\' value=\'' + editArr.join('|') + '\'/>' +
                '</form>');
            submitForm.appendTo('body');

            submitForm.submit();
        });

        $(document.body).on('click', '.submitMassUpdate', () => {
            const updateArr = [];
            const refreshArr = [];
            const renameArr = [];
            const subtitleArr = [];
            const deleteArr = [];
            const removeArr = [];
            const metadataArr = [];
            const imageUpdateArr = [];

            // $('.updateCheck').each((index, element) => {
            //     if (element.checked === true) {
            //         < text>
            //         updateArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            //         </ text>
            //     }
            // });

            // $('.refreshCheck').each((index, element) => {
            //     if (element.checked === true) {
            //         < text>
            //         refreshArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            //         </ text>
            //     }
            // });

            // $('.renameCheck').each((index, element) => {
            //     if (element.checked === true) {
            //         < text>
            //         renameArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            //         </ text>
            //     }
            // });

            // $('.subtitleCheck').each((index, element) => {
            //     if (element.checked === true) {
            //         < text>
            //         subtitleArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            //         </ text>
            //     }
            // });

            // $('.removeCheck').each((index, element) => {
            //     if (element.checked === true) {
            //         < text>
            //         removeArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            //         </ text>
            //     }
            // });

            // $('.imageCheck').each((index, element) => {
            //     if (element.checked === true) {
            //         < text>
            //         imageUpdateArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            //         </ text>
            //     }
            // });

            let deleteCount = 0;

            $('.deleteCheck').each((index, element) => {
                if (element.checked === true) {
                    deleteCount++;
                }
            });

            const totalCount = [].concat.apply([], [updateArr, refreshArr, renameArr, subtitleArr, deleteArr, removeArr, metadataArr, imageUpdateArr]).length; // eslint-disable-line no-useless-call

            if (deleteCount >= 1) {
                $.confirm({
                    title: 'Delete Shows',
                    text: 'You have selected to delete ' + deleteCount + ' show(s).  Are you sure you wish to continue? All files will be removed from your system.',
                    confirmButton: 'Yes',
                    cancelButton: 'Cancel',
                    dialogClass: 'modal-dialog',
                    post: false,
                    confirm() {
                        // $('.deleteCheck').each((index, element) => {
                        //     if (element.checked === true) {
                        //         <%text>
                        //         deleteArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
                        //         </%text>
                        //     }
                        // });
                        if (totalCount === 0) {
                            return false;
                        }
                        const params = $.param({
                            toUpdate: updateArr.join('|'),
                            toRefresh: refreshArr.join('|'),
                            toRename: renameArr.join('|'),
                            toSubtitle: subtitleArr.join('|'),
                            toDelete: deleteArr.join('|'),
                            toRemove: removeArr.join('|'),
                            toMetadata: metadataArr.join('|'),
                            toImageUpdate: imageUpdateArr.join('|')
                        });

                        window.location.href = $('base').attr('href') + 'manage/massUpdate?' + params;
                    }
                });
            }

            if (totalCount === 0) {
                return false;
            }
            if (updateArr.length + refreshArr.length + renameArr.length + subtitleArr.length + deleteArr.length + removeArr.length + metadataArr.length + imageUpdateArr.length === 0) {
                return false;
            }
            const url = $('base').attr('href') + 'manage/massUpdate';
            const params = 'toUpdate=' + updateArr.join('|') + '&toRefresh=' + refreshArr.join('|') + '&toRename=' + renameArr.join('|') + '&toSubtitle=' + subtitleArr.join('|') + '&toDelete=' + deleteArr.join('|') + '&toRemove=' + removeArr.join('|') + '&toMetadata=' + metadataArr.join('|') + '&toImageUpdate=' + imageUpdateArr.join('|');
            $.post(url, params, () => {
                location.reload(true);
            });
        });

        ['.editCheck', '.updateCheck', '.refreshCheck', '.renameCheck', '.deleteCheck', '.removeCheck', '.imageCheck'].forEach(name => {
            let lastCheck = null;

            $(document.body).on('click', name, event => {
                if (!lastCheck || !event.shiftKey) {
                    lastCheck = event.currentTarget;
                    return;
                }

                const check = event.currentTarget;
                let found = 0;

                $(name).each((index, element) => {
                    if (found === 1) {
                        if (!element.disabled) {
                            element.checked = lastCheck.checked;
                        }
                    }
                    if (found === 2) {
                        return false;
                    }
                    if (element === check || element === lastCheck) {
                        found++;
                    }
                });
            });
        });
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
            const action = event.currentTarget.dataset.action;
            const checked = event.currentTarget.checked;
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
                refresh: [],
                rename: [],
                subtitle: [],
                delete: [],
                remove: [],
                image: []
            }
            for (const action of ['update', 'refresh', 'rename', 'subtitle', 'delete', 'remove', 'image']) {
                document.querySelectorAll(`[data-action="${action}"]`).forEach(el => el.checked = false);
            }
        },
        async triggerActions() {
            const { massUpdateActions } = this;
            
            try {
                const { data } = await api.post('massupdate', massUpdateActions);
                if (Object.keys(data.shows).length) {
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
         */
        inQueueOrStarted(queueType, showSlug) {
            const { showQueue, showQueueItems } = this;
            const queueItemNames = new Map([
                ['update', 'UPDATE'],
                ['refresh', 'REFRESH'],
                ['rename', 'RENAME'],
                ['subtitle', 'SUBTITLE'],
                ['delete', 'REMOVE-SHOW'],
                ['remove', 'REMOVE-SHOW']
            ])

            const showInQueue = showQueue?.find(queue => queue.queueType.toLowerCase() === queueType && queue.showSlug === showSlug);
            const filteredShowQueueItems = showQueueItems?.filter(
                queue => queue.name === queueItemNames.get(queueType) && queue.show.id.slug === showSlug
            )
            if (filteredShowQueueItems.filter(queue => !queue.inProgress).length) {
                return false;
            }

            return Boolean(showInQueue || filteredShowQueueItems.length);
        }
        // async getShowQueue() {
        //     try {
        //         const { data } = await api.get('config/system/showQueue');
        //         this.showQueue = data;
        //     } catch (error) {
        //         this.$snotify.warning('error', 'Error trying to get showqueue');                
        //     }
        // }
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
    float: right;
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
</style>
