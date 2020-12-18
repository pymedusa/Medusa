<%inherit file="/layouts/main.mako"/>
<%!
    from datetime import datetime
    from medusa import app
    from medusa.sbdatetime import sbdatetime
%>
<%block name="scripts">
<script type="text/javascript" src="js/rating-tooltip.js?${sbPID}"></script>
<script type="text/x-template" id="snatch-selection-template">
<div>
    <input type="hidden" id="series-id" value="${show.indexerid}" />
    <input type="hidden" id="series-slug" value="${show.slug}" />

    <backstretch slug="${show.slug}"></backstretch>

    <div class="clearfix"></div><!-- div.clearfix //-->

    <show-header @reflow="reflowLayout" type="snatch-selection"
        :show-id="id" :show-indexer="indexer"
        :show-season="season" :show-episode="episode"
        manual-search-type="${manual_search_type}"
    ></show-header>

    <div class="row">
        <div class="col-md-12 horizontal-scroll">
            <div class="clearfix"></div><!-- .clearfix //-->
            <div id="wrapper" data-history-toggle="hide">
                <div id="container">

                % if episode_history:
                    <table id="snatchhistory" class="${"displayShowTableFanArt tablesorterFanArt" if app.FANART_BACKGROUND else "displayShowTable"} display_show tablesorter tablesorter-default" cellspacing="1" border="0" cellpadding="0">
                        <tbody class="tablesorter-no-sort" aria-live="polite" aria-relevant="all">
                            <tr role="row">
                                <th colspan="5" class="row-seasonheader">
                                    <h3>
                                        History
                                    </h3>
                                    <button id="showhistory" type="button" class="btn-medusa top-5 bottom-5 pull-right" data-toggle="collapse" data-target="#historydata">
                                        Show History
                                    </button>
                                </th>
                            </tr>
                        </tbody>
                        <tbody class="tablesorter-no-sort" aria-live="polite" aria-relevant="all">
                            <tr>
                                <th>Date</th>
                                <th>Status</th>
                                <th>Provider/Group</th>
                                <th>Release</th>
                                <th>Size</th>
                            </tr>
                        </tbody>
                        <tbody class="toggle collapse" aria-live="polite" aria-relevant="all" id="historydata">
                            % for item in episode_history:
                                <tr class="${item['status_color_style']}">
                                    <td>
                                        ${item['action_date']}
                                    </td>
                                    <td>
                                    ${item['status_name']} <quality-pill :quality="${item['quality']}"></quality-pill>
                                    </td>
                                    <td>
                                            % if item['provider_img_link']:
                                                <img src="${item['provider_img_link']}" width="16" height="16" alt="${item['provider_name']}" title="${item['provider_name']}"/> ${item["provider_name"]}
                                            % else:
                                                ${item['provider_name']}
                                            % endif
                                    </td>
                                    <td>
                                    ${item['resource_file']}
                                    </td>
                                    <td class="col-size">
                                    ${item['pretty_size']}
                                    </td>
                                </tr>
                            % endfor
                            <tr id="history-footer" class="tablesorter-no-sort border-bottom shadow">
                                <th class="tablesorter-no-sort" colspan="5"></th>
                            </tr>
                        </tbody>
                        <tbody class="tablesorter-no-sort"><tr><th class="row-seasonheader" colspan="5"></th></tr></tbody>
                    </table>
                % endif
                <!-- add provider meta data -->
                    <div id='manualSearchMeta'>
                        <meta data-last-prov-updates='${provider_results["last_prov_updates"]}' data-indexer-name="${show.indexer_name}" data-series-id="${show.indexerid}" data-season="${season}" data-episode="${episode}" data-manual-search-type="${manual_search_type}">
                    </div>
                    <div class="col-md-12 bottom-15">
                        <div class="col-md-8 left-30">
                        <input class="btn-medusa manualSearchButton" type="button" id="reloadResults" value="Reload Results" data-force-search="0" />
                        <input class="btn-medusa manualSearchButton" type="button" id="reloadResultsForceSearch" value="Force Search" data-force-search="1" />
                        <div id="searchNotification"></div><!-- #searchNotification //-->
                        </div>
                        <div class="pull-right clearfix col-md-4 right-30" id="filterControls">
                            <div class="pull-right">
                                <button id="popover" type="button" class="btn-medusa">Select Columns <b class="caret"></b></button>
                                <button id="btnReset" type="button" class="btn-medusa">Reset Sort</button>
                            </div>
                        </div><!-- #filterControls //-->
                    </div>
                    <table id="srchresults" class="${"displayShowTableFanArt tablesorterFanArt" if app.FANART_BACKGROUND else "displayShowTable"} display_show tablesorter tablesorter-default hasSaveSort hasStickyHeaders" cellspacing="1" border="0" cellpadding="0">
                        <thead>
                            <tr>
                                <th data-priority="critical" class="col-name">Release</th>
                                <th>Group</th>
                                <th>Provider</th>
                                <th>Quality</th>
                                <th>Seeds</th>
                                <th>Peers</th>
                                <th>Size</th>
                                <th>Type</th>
                                <th>Updated</th>
                                <th>Published</th>
                                <th>Added</th>
                                <th data-priority="critical" class="col-search">Snatch</th>
                            </tr>
                        </thead>
                        <tbody id="manualSearchTbody" aria-live="polite" aria-relevant="all">
                        % for hItem in provider_results['found_items']:
                            <tr id="${hItem['name'] | h}" class="skipped season-${season} seasonstyle ${hItem['status_highlight']}" role="row">
                                <td class="release-name-ellipses triggerhighlight">
                                    <span v-pre data-qtip-my="top left" data-qtip-at="bottom left" :class="getReleaseNameClasses(`${hItem['name']}`)" title="${hItem['name'] | h}" class="break-word ${hItem['name_highlight']} addQTip">${hItem['name'] | h}</span>
                                </td>
                                <td class="col-group break-word triggerhighlight">
                                    <span class="break-word ${hItem['rg_highlight']}">${hItem['release_group']}</span>
                                </td>
                                <td class="col-provider triggerhighlight">
                                    <span title="${hItem["provider"]}" class="addQTip">
                                        <img src="${hItem["provider_img_link"]}" width="16" height="16" class="vMiddle curHelp" alt="${hItem["provider"]}" title="${hItem["provider"]}"/>
                                    </span>
                                </td>
                                <td class="triggerhighlight"><quality-pill :quality="${int(hItem['quality'])}"></quality-pill>
                                % if hItem["proper_tags"]:
                                    <img src="images/info32.png" width="16" height="16" class="vMmiddle" title="${hItem["proper_tags"]}"/>
                                % endif
                                </td>
                                <td class="triggerhighlight">
                                    <span class="${hItem['seed_highlight']}">${hItem["seeders"]}</span>
                                </td>
                                <td class="triggerhighlight">
                                    <span class="${hItem['leech_highlight']}">${hItem["leechers"]}</span>
                                </td>
                                <td class="col-size triggerhighlight" data-size="${hItem["size"]}">${hItem["pretty_size"]}</td>
                                <td class="triggerhighlight">${hItem["provider_type"]}</td>
                                <td class="col-date triggerhighlight">
                                    <span data-qtip-my="top middle" data-qtip-at="bottom middle" title='${hItem["time"]}' class="addQTip"><time datetime="${hItem['time'].isoformat('T')}" class="date">${hItem["time"]}</time></span>
                                </td>
                                <td class="col-date triggerhighlight" data-datetime="${hItem['pubdate'].isoformat('T') if hItem['pubdate'] else datetime.min}">
                                    ${sbdatetime.sbfdatetime(dt=hItem['pubdate'], d_preset=app.DATE_PRESET, t_preset=app.TIME_PRESET) if hItem['pubdate'] else 'N/A'}
                                </td>
                                <td class="col-date triggerhighlight" data-datetime="${hItem['date_added'].isoformat('T') if hItem['date_added'] else datetime.min}">
                                    ${sbdatetime.sbfdatetime(dt=hItem['date_added'], d_preset=app.DATE_PRESET, t_preset=app.TIME_PRESET) if hItem['date_added'] else 'N/A'}
                                </td>
                                <td class="col-search triggerhighlight"><app-link class="epManualSearch" id="${str(show.indexerid)}x${season}x${episode}" name="${str(show.indexerid)}x${season}x${episode}" href='home/pickManualSearch?provider=${hItem["provider_id"]}&amp;rowid=${hItem["rowid"]}'><img src="images/download.png" width="16" height="16" alt="search" title="Download selected episode" /></app-link></td>
                            </tr>
                        % endfor
                        </tbody>
                        <tbody class="tablesorter-no-sort">
                        <tr id="search-footer" class="tablesorter-no-sort border-bottom shadow">
                            <th class="tablesorter-no-sort" colspan="12"></th>
                        </tr>
                        <tr><th class="row-seasonheader" colspan="12"></th></tr></tbody>
                    </table>
                </div><!-- #container //-->
            </div><!-- #wrapper //-->
        </div><!-- col -->
    </div><!-- row -->
</div>
</script>
<script>
const { store, router } = window;

window.app = {};
window.app = new Vue({
    el: '#vue-wrap',
    store,
    router,
    data() {
        return {
            // This loads snatch-selection.vue
            pageComponent: 'snatch-selection'
        }
    }
});
</script>
</%block>
