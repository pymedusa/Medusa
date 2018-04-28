<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import statusStrings
    from medusa.helpers import remove_article
%>
<%block name="scripts">
<script type="text/javascript" src="js/mass-update.js?${sbPID}"></script>
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Mass Update'
        },
        data() {
            return {
                header: 'Mass Update'
            };
        }
    });
};
</script>
</%block>
<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>

<form name="massUpdateForm" method="post" action="manage/massUpdate">
    <div class="row">
        <div class="col-md-12">
            <table style="width: 100%;" class="home-header">
                <tr>
                    <td nowrap>
                        <h1 class="header" style="margin: 0;">{{header}}</h1>
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
                    % if app.USE_SUBTITLES:
                        <th width="1%">Search Subtitle<br><input type="checkbox" class="bulkCheck" id="subtitleCheck" /></th>
                    % endif
                        <!-- <th>Force Metadata Regen <input type="checkbox" class="bulkCheck" id="metadataCheck" /></th>//-->
                        <th width="1%">Delete<br><input type="checkbox" class="bulkCheck" id="deleteCheck" /></th>
                        <th width="1%">Remove<br><input type="checkbox" class="bulkCheck" id="removeCheck" /></th>
                        <th width="1%">Update image<br><input type="checkbox" class="bulkCheck" id="imageCheck" /></th>
                    </tr>
                </thead>
                <tfoot>
                    <tr>
                        <td rowspan="1" colspan="2" class="align-center alt"><input class="btn-medusa pull-left submitMassEdit" type="button" value="Edit Selected" /></td>
                        <td rowspan="1" colspan="${(16, 17)[bool(app.USE_SUBTITLES)]}" class="align-right alt"><input class="btn-medusa pull-right submitMassUpdate" type="button" value="Submit" /></td>
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
                    curUpdate = "<input type=\"checkbox\" class=\"updateCheck\" data-indexer-name=" + cur_show.indexer_name + " data-series-id=\"" + str(cur_show.series_id) + "\" id=\"update-" + str(cur_show.indexerid) + "\" " + ("", "disabled=\"disabled\" ")[disabled] + "/>"
                    disabled = app.show_queue_scheduler.action.isBeingRefreshed(cur_show) or app.show_queue_scheduler.action.isInRefreshQueue(cur_show)
                    curRefresh = "<input type=\"checkbox\" class=\"refreshCheck\" data-indexer-name=" + cur_show.indexer_name + " data-series-id=\"" + str(cur_show.series_id) + "\"id=\"refresh-" + str(cur_show.indexerid) + "\" " + ("", "disabled=\"disabled\" ")[disabled] + "/>"
                    disabled = app.show_queue_scheduler.action.isBeingRenamed(cur_show) or app.show_queue_scheduler.action.isInRenameQueue(cur_show)
                    curRename = "<input type=\"checkbox\" class=\"renameCheck\" data-indexer-name=" + cur_show.indexer_name + " data-series-id=\"" + str(cur_show.series_id) + "\"id=\"rename-" + str(cur_show.indexerid) + "\" " + ("", "disabled=\"disabled\" ")[disabled] + "/>"
                    disabled = not cur_show.subtitles or app.show_queue_scheduler.action.isBeingSubtitled(cur_show) or app.show_queue_scheduler.action.isInSubtitleQueue(cur_show)
                    curSubtitle = "<input type=\"checkbox\" class=\"subtitleCheck\" data-indexer-name=" + cur_show.indexer_name + " data-series-id=\"" + str(cur_show.series_id) + "\"id=\"subtitle-" + str(cur_show.indexerid) + "\" " + ("", "disabled=\"disabled\" ")[disabled] + "/>"
                    disabled = app.show_queue_scheduler.action.isBeingRenamed(cur_show) or app.show_queue_scheduler.action.isInRenameQueue(cur_show) or app.show_queue_scheduler.action.isInRefreshQueue(cur_show)
                    curDelete = "<input type=\"checkbox\" class=\"confirm deleteCheck\" data-indexer-name=" + cur_show.indexer_name + " data-series-id=\"" + str(cur_show.series_id) + "\"id=\"delete-" + str(cur_show.indexerid) + "\" " + ("", "disabled=\"disabled\" ")[disabled] + "/>"
                    disabled = app.show_queue_scheduler.action.isBeingRenamed(cur_show) or app.show_queue_scheduler.action.isInRenameQueue(cur_show) or app.show_queue_scheduler.action.isInRefreshQueue(cur_show)
                    curRemove = "<input type=\"checkbox\" class=\"removeCheck\" data-indexer-name=" + cur_show.indexer_name + " data-series-id=\"" + str(cur_show.series_id) + "\"id=\"remove-" + str(cur_show.indexerid) + "\" " + ("", "disabled=\"disabled\" ")[disabled] + "/>"
                    curImage = "<input type=\"checkbox\" class=\"imageCheck\" data-indexer-name=" + cur_show.indexer_name + " data-series-id=\"" + str(cur_show.series_id) + "\"id=\"image-" + str(cur_show.indexerid) + "\" " + "/>"
                %>
                <tr>
                    <td class="triggerhighlight" align="center"><input type="checkbox" class="editCheck" data-indexer-name="${cur_show.indexer_name}" data-series-id="${cur_show.series_id}" id="edit-${cur_show.series_id}" /></td>
                    <td class="tvShow triggerhighlight"><app-link href="home/displayShow?indexername=${cur_show.indexer_name}&seriesid=${cur_show.indexerid}">${cur_show.name}</app-link></td>
                    <td class="triggerhighlight" align="center">${renderQualityPill(cur_show.quality, showTitle=True)}</td>
                    <td class="triggerhighlight" align="center"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[int(cur_show.is_sports) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[int(cur_show.is_scene) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[int(cur_show.is_anime) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[not int(cur_show.flatten_folders) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[int(cur_show.dvd_order) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[int(cur_show.paused) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center"><img src="images/${('no16.png" alt="N', 'yes16.png" alt="Y')[int(cur_show.subtitles) == 1]}" width="16" height="16" /></td>
                    <td class="triggerhighlight" align="center">${statusStrings[cur_show.default_ep_status]}</td>
                    <td class="triggerhighlight" align="center">${cur_show.status}</td>
                    <td class="triggerhighlight" align="center">${curUpdate}</td>
                    <td class="triggerhighlight" align="center">${curRefresh}</td>
                    <td class="triggerhighlight" align="center">${curRename}</td>
                    % if app.USE_SUBTITLES:
                    <td class="triggerhighlight" align="center">${curSubtitle}</td>
                    % endif
                    <td class="triggerhighlight" align="center">${curDelete}</td>
                    <td class="triggerhighlight" align="center">${curRemove}</td>
                    <td class="triggerhighlight" align="center">${curImage}</td>
                </tr>
            % endfor
            </tbody>
            </table>
        </div>
    </div>
</form>
</%block>
