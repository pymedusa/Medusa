<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import statusStrings
    from medusa.helpers import remove_article
%>
<%block name="scripts">
<script>
const { mapState } = window.Vuex;

window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    // TODO: Replace with Object spread (`...mapState`)
    computed: mapState(['config']),
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

            $('.editCheck').each((index, element) => {
                if (element.checked === true) {
                    <%text>
                    editArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
                    </%text>
                }
            });

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

            $('.updateCheck').each((index, element) => {
                if (element.checked === true) {
                    <%text>
                    updateArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
                    </%text>
                }
            });

            $('.refreshCheck').each((index, element) => {
                if (element.checked === true) {
                    <%text>
                    refreshArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
                    </%text>
                }
            });

            $('.renameCheck').each((index, element) => {
                if (element.checked === true) {
                    <%text>
                    renameArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
                    </%text>
                }
            });

            $('.subtitleCheck').each((index, element) => {
                if (element.checked === true) {
                    <%text>
                    subtitleArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
                    </%text>
                }
            });

            $('.removeCheck').each((index, element) => {
                if (element.checked === true) {
                    <%text>
                    removeArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
                    </%text>
                }
            });

            $('.imageCheck').each((index, element) => {
                if (element.checked === true) {
                    <%text>
                    imageUpdateArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
                    </%text>
                }
            });

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
                        $('.deleteCheck').each((index, element) => {
                            if (element.checked === true) {
                                <%text>
                                deleteArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
                                </%text>
                            }
                        });
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
});
</script>
</%block>
<%block name="content">
<form name="massUpdateForm" method="post" action="manage/massUpdate">
    <div class="row">
        <div class="col-md-12">
            <table style="width: 100%;" class="home-header">
                <tr>
                    <td nowrap>
                        <h1 class="header" style="margin: 0;">{{ $route.meta.header }}</h1>
                    </td>
                    <td align="right">
                        <div>
                            <input class="btn-medusa btn-inline submitMassEdit" type="button" value="Edit Selected" />
                            <input class="btn-medusa btn-inline submitMassUpdate" type="button" value="Submit" />
                            <span class="show-option">
                                <button id="popover" type="button" class="btn-medusa btn-inline">Select Columns <b class="caret"></b></button>
                            </span>
                            <span class="show-option">
                                <button type="button" class="resetsorting btn-medusa btn-inline">Clear Filter(s)</button>
                            </span>
                        </div>
                    </td>
                </tr>
            </table>
        </div>
    </div>

    <div class="row">
        <div class="col-md-12 horizontal-scroll">
            <table id="massUpdateTable" class="tablesorter" cellspacing="1" border="0" cellpadding="0">
                <thead>
                    <tr>
                        <th class="col-checkbox">Edit<br><input type="checkbox" class="bulkCheck" id="editCheck" /></th>
                        <th class="nowrap" style="text-align: left;">Show Name</th>
                        <th class="col-quality">Quality</th>
                        <th class="col-legend">Sports</th>
                        <th class="col-legend">Scene</th>
                        <th class="col-legend">Anime</th>
                        <th class="col-legend">Season folders</th>
                        <th class="col-legend">DVD Order</th>
                        <th class="col-legend">Paused</th>
                        <th class="col-legend">Subtitle</th>
                        <th class="col-legend">Default Ep Status</th>
                        <th class="col-legend">Status</th>
                        <th width="1%">Update<br><input type="checkbox" class="bulkCheck" id="updateCheck" /></th>
                        <th width="1%">Rescan<br><input type="checkbox" class="bulkCheck" id="refreshCheck" /></th>
                        <th width="1%">Rename<br><input type="checkbox" class="bulkCheck" id="renameCheck" /></th>
                        <th width="1%" v-if="config.general.subtitles.enabled">Search Subtitle<br><input type="checkbox" class="bulkCheck" id="subtitleCheck" /></th>
                        <!-- <th>Force Metadata Regen <input type="checkbox" class="bulkCheck" id="metadataCheck" /></th>//-->
                        <th width="1%">Delete<br><input type="checkbox" class="bulkCheck" id="deleteCheck" /></th>
                        <th width="1%">Remove<br><input type="checkbox" class="bulkCheck" id="removeCheck" /></th>
                        <th width="1%">Update image<br><input type="checkbox" class="bulkCheck" id="imageCheck" /></th>
                    </tr>
                </thead>
                <tfoot>
                    <tr>
                        <td rowspan="1" colspan="2" class="align-center alt"><input class="btn-medusa pull-left submitMassEdit" type="button" value="Edit Selected" /></td>
                        <td rowspan="1" :colspan="config.general.subtitles.enabled ? 17 : 16" class="align-right alt"><input class="btn-medusa pull-right submitMassUpdate" type="button" value="Submit" /></td>
                    </tr>
                </tfoot>
                <tbody>
            <%
                def titler(x):
                    return (remove_article(x), x)[not x or app.SORT_ARTICLE]

                my_show_list = app.showList
                my_show_list.sort(key=lambda x: titler(x.name).lower())
            %>
                % for cur_show in my_show_list:
                <%
                    cur_ep = cur_show.next_aired
                    disabled = app.show_queue_scheduler.action.isBeingUpdated(cur_show) or app.show_queue_scheduler.action.isInUpdateQueue(cur_show)
                    curUpdate = '<input type="checkbox" class="updateCheck" data-indexer-name=' + cur_show.indexer_name + ' data-series-id="' + str(cur_show.series_id) + '" id="update-' + str(cur_show.indexerid) + '" ' + ('', 'disabled="disabled" ')[disabled] + '/>'
                    disabled = app.show_queue_scheduler.action.isBeingRefreshed(cur_show) or app.show_queue_scheduler.action.isInRefreshQueue(cur_show)
                    curRefresh = '<input type="checkbox" class="refreshCheck" data-indexer-name=' + cur_show.indexer_name + ' data-series-id="' + str(cur_show.series_id) + '" id="refresh-' + str(cur_show.indexerid) + '" ' + ('', 'disabled="disabled" ')[disabled] + '/>'
                    disabled = app.show_queue_scheduler.action.isBeingRenamed(cur_show) or app.show_queue_scheduler.action.isInRenameQueue(cur_show)
                    curRename = '<input type="checkbox" class="renameCheck" data-indexer-name=' + cur_show.indexer_name + ' data-series-id="' + str(cur_show.series_id) + '" id="rename-' + str(cur_show.indexerid) + '" ' + ('', 'disabled="disabled" ')[disabled] + '/>'
                    disabled = not cur_show.subtitles or app.show_queue_scheduler.action.isBeingSubtitled(cur_show) or app.show_queue_scheduler.action.isInSubtitleQueue(cur_show)
                    curSubtitle = '<input type="checkbox" class="subtitleCheck" data-indexer-name=' + cur_show.indexer_name + ' data-series-id="' + str(cur_show.series_id) + '" id="subtitle-' + str(cur_show.indexerid) + '" ' + ('', 'disabled="disabled" ')[disabled] + '/>'
                    disabled = app.show_queue_scheduler.action.isBeingRenamed(cur_show) or app.show_queue_scheduler.action.isInRenameQueue(cur_show) or app.show_queue_scheduler.action.isInRefreshQueue(cur_show)
                    curDelete = '<input type="checkbox" class="confirm deleteCheck" data-indexer-name=' + cur_show.indexer_name + ' data-series-id="' + str(cur_show.series_id) + '" id="delete-' + str(cur_show.indexerid) + '" ' + ('', 'disabled="disabled" ')[disabled] + '/>'
                    disabled = app.show_queue_scheduler.action.isBeingRenamed(cur_show) or app.show_queue_scheduler.action.isInRenameQueue(cur_show) or app.show_queue_scheduler.action.isInRefreshQueue(cur_show)
                    curRemove = '<input type="checkbox" class="removeCheck" data-indexer-name=' + cur_show.indexer_name + ' data-series-id="' + str(cur_show.series_id) + '" id="remove-' + str(cur_show.indexerid) + '" ' + ('', 'disabled="disabled" ')[disabled] + '/>'
                    curImage = '<input type="checkbox" class="imageCheck" data-indexer-name=' + cur_show.indexer_name + ' data-series-id="' + str(cur_show.series_id) + '" id="image-' + str(cur_show.indexerid) + '" ' + '/>'
                %>
                <tr>
                    <td class="triggerhighlight" align="center" title="Edit"><input type="checkbox" class="editCheck" data-indexer-name="${cur_show.indexer_name}" data-series-id="${cur_show.series_id}" id="edit-${cur_show.series_id}" /></td>
                    <td class="tvShow triggerhighlight"><app-link href="home/displayShow?indexername=${cur_show.indexer_name}&seriesid=${cur_show.indexerid}">${cur_show.name}</app-link></td>
                    <td class="triggerhighlight" align="center"><quality-pill :quality="${cur_show.quality}" show-title></quality-pill></td>
                    <td class="triggerhighlight" align="center" title="Sports"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[int(cur_show.is_sports) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center" title="Scene"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[int(cur_show.is_scene) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center" title="Anime"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[int(cur_show.is_anime) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center" title="Season folders"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[cur_show.season_folders]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center" title="DVD Order"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[int(cur_show.dvd_order) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center" title="Paused"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[int(cur_show.paused) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center" title="Subtitle"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[int(cur_show.subtitles) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center" title="Default Ep Status">${statusStrings[cur_show.default_ep_status]}</td>
                    <td class="triggerhighlight" align="center" title="Status">${cur_show.status}</td>
                    <td class="triggerhighlight" align="center" title="Update">${curUpdate}</td>
                    <td class="triggerhighlight" align="center" title="Refresh">${curRefresh}</td>
                    <td class="triggerhighlight" align="center" title="Rename">${curRename}</td>
                    <td v-if="config.general.subtitles.enabled" class="triggerhighlight" align="center" title="Search Subtitle">${curSubtitle}</td>
                    <td class="triggerhighlight" align="center" title="Delete">${curDelete}</td>
                    <td class="triggerhighlight" align="center" title="Remove">${curRemove}</td>
                    <td class="triggerhighlight" align="center" title="Update image">${curImage}</td>
                </tr>
            % endfor
            </tbody>
            </table>
        </div>
    </div>
</form>
</%block>
