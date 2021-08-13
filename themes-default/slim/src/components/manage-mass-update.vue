<template>
<!-- < inherit file="/layouts/main.mako"/>
< !
    from medusa import app
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import statusStrings
    from medusa.helpers import remove_article
 >
< block name="scripts"> -->



    <div>
        <vue-good-table v-if="shows.length > 0"
                :columns="columns"
                :rows="shows"
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
                @on-sort-change="saveSorting"
        >
        </vue-good-table>
    </div>
</template>

<script>
import { mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';

export default {
    name: 'manage-mass-update',
    mixins: [
        showlistTableMixin
    ],
    data() {
        return {
            columns: [{
                label: 'Show Name',
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
                field: 'config.subtitle',
                type: 'boolean',
                filterOptions: {
                    enabled: true,
                    filterDropdownItems: [
                        { value: true, text: 'yes' },
                        { value: false, text: 'no' }
                    ]
                },
            }
            ]
        }
    },
    // TODO: Replace with Object spread (`...mapState`)
    computed: {
        ...mapState({
            general: state => state.config.general,
            shows: state => state.shows.shows
        })
    },
    mounted() {
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
    }
};
</script>
<style scoped>
</style>
