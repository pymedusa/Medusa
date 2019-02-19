<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script type="text/x-template" id="show-template">
<div>
    <input type="hidden" id="series-id" value="" />
    <input type="hidden" id="indexer-name" value="" />
    <input type="hidden" id="series-slug" value="" />

    <show-header @reflow="reflowLayout" type="show"
        :show-id="id" :show-indexer="indexer"
    ></show-header>

    <div class="row">
        <div class="col-md-12 horizontal-scroll" style="top: 12px" :class="[{ displayShowTableFanArt: config.fanartBackground }, { tablesorterFanArt: config.fanartBackground }, { displayShowTable: !config.fanartBackground }]">

                <table :id='show.config.anime ? "animeTable" : "showTable"' cellspacing="0" border="0" cellpadding="0" class="display_show">
                    <thead>
                        <tr class="seasoncols" style="display:none;">
                            <th data-sorter="false" data-priority="critical" class="col-checkbox"><input type="checkbox" class="seasonCheck"/></th>
                            <th data-sorter="false" class="col-metadata">NFO</th>
                            <th data-sorter="false" class="col-metadata">TBN</th>
                            <th data-sorter="false" class="col-ep">Episode</th>
                            <th data-sorter="false" :class="['col-ep', { 'columnSelector-false': !show.config.anime }]">Absolute</th>
                            <th data-sorter="false" :class="['col-ep', { 'columnSelector-false': (show.config.airByDate || show.config.sports || show.config.anime) && !show.config.scene }]">Scene</th>
                            <th data-sorter="false" :class="['col-ep', { 'columnSelector-false': (show.config.airByDate || show.config.sports || !show.config.anime) && !show.config.scene }]">Scene Absolute</th>
                            <th data-sorter="false" class="col-name">Name</th>
                            <th data-sorter="false" class="col-name columnSelector-false">File Name</th>
                            <th data-sorter="false" class="col-ep columnSelector-false">Size</th>
                            <th data-sorter="false" class="col-airdate">Airdate</th>
                            <th data-sorter="false" :class="['col-ep', { 'columnSelector-false': !config.downloadUrl }]">Download</th>
                            <th data-sorter="false" :class="['col-ep', { 'columnSelector-false': !show.config.subtitlesEnabled }]">Subtitles</th>
                            <th data-sorter="false" class="col-status">Status</th>
                            <th data-sorter="false" class="col-search">Search</th>
                        </tr>
                    </thead>

                    <div class="row" v-for="(season, $index) in seasonsInverse" :key="season.season">
                        <div class="col-lg-12">
                                <tbody class="tablesorter-no-sort">
                                    <tr>
                                        <th class="row-seasonheader" colspan="15" style="vertical-align: bottom; width: auto;">
                                            <h3 style="display: inline;"><app-link :name="'season-'+ season.season"></app-link>
                                                <!-- {'Season ' + str(epResult['season']) if int(epResult['season']) > 0 else 'Specials'} -->
                                                {{ season.season > 0 ? 'Season ' + season.season : 'Specials' }}
                                                <!-- Only show the search manual season search, when any of the episodes in it is not unaired -->
                                                <app-link v-if="anyEpisodeNotUnaired(season)" class="epManualSearch" :href="'home/snatchSelection?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&amp;season=' + season.season + '&amp;episode=1&amp;manual_search_type=season'">
                                                    <img v-if="config" data-ep-manual-search :src="'images/manualsearch' + (config.themeName === 'dark' ? '-white' : '') + '.png'" width="16" height="16" alt="search" title="Manual Search" />
                                                </app-link>
                                            </h3>
                                            <div class="season-scene-exception" :data-season="season.season > 0 ? season.season : 'Specials'">
                                                <img v-bind="getSeasonExceptions(season.season)" height="16" />
                                            </div>
                                            <div class="pull-right"> <!-- column select and hide/show episodes -->
                                                    <!-- if not app.DISPLAY_ALL_SEASONS: -->
                                                    <button v-if="!config.layout.show.allSeasons" :id="'showseason-' + season.season" type="button" class="btn-medusa pull-right" data-toggle="collapse" :data-target="'#collapseSeason-' + season.season">Hide Episodes</button>
                                                    <!-- endif -->
                                                <button id="popover" type="button" class="btn-medusa pull-right selectColumns">Select Columns <b class="caret"></b></button>
                                            </div> <!-- end column select and hide/show episodes -->
                                        </th>
                                    </tr>
                                </tbody>
                                <tbody class="tablesorter-no-sort">
                                    <tr :id="'season-' + season.season + '-cols'" class="seasoncols">
                                        <th data-column="0" class="col-checkbox"><input type="checkbox" class="seasonCheck" :id="season.season" /></th>
                                        <th data-column="1" class="col-metadata">NFO</th>
                                        <th data-column="2" class="col-metadata">TBN</th>
                                        <th data-column="3" class="col-ep">Episode</th>
                                        <th data-column="4" class="col-ep">Absolute</th>
                                        <th data-column="5" class="col-ep">Scene</th>
                                        <th data-column="6" class="col-ep">Scene Absolute</th>
                                        <th data-column="7" class="col-name hidden-xs">Name</th>
                                        <th data-column="8" class="col-name hidden-xs">File Name</th>
                                        <th data-column="9" class="col-ep">Size</th>
                                        <th data-column="10" class="col-airdate">Airdate</th>
                                        <th data-column="11" class="col-ep">Download</th>
                                        <th data-column="12" class="col-ep">Subtitles</th>
                                        <th data-column="13" class="col-status">Status</th>
                                        <th data-column="14" class="col-search">Search</th>
                                    </tr>
                                </tbody>

                                <tbody :class="[{toggle: !config.layout.show.allSeasons}, {collapse: !config.layout.show.allSeasons}, {'in': !config.layout.show.allSeasons && $index === 0}]" :id="'collapseSeason-'+ season.season">
                                    <tr v-for="episode in episodesInverse(season)" :key="episode.episode" :value="episode.episode" :class="episode.status.toLowerCase() + ' season-' + episode.season + ' seasonstyle'" :id="'S' + episode.season + 'E' + episode.episode">
                                        <td class="col-checkbox triggerhighlight">
                                            <input v-if="episode.status !== 'Unaired'" type="checkbox" class="epCheck" :id="'s' + episode.season + 'e' + episode.episode" :name="'s' + episode.season + 'e' + episode.episode"/>
                                        </td>
                                        <td align="center" class="triggerhighlight"><img :src="'images/' + (episode.content.hasNfo ? 'nfo.gif' : 'nfo-no.gif')" :alt="(episode.content.hasNfo ? 'Y' : 'N')" width="23" height="11" /></td>
                                        <td align="center" class="triggerhighlight"><img :src="'images/' + (episode.content.hasTbn ? 'tbn.gif' : 'tbn-no.gif')" :alt="(episode.content.hasTbn ? 'Y' : 'N')" width="23" height="11" /></td>
                                        <td align="center" class="triggerhighlight">
                                        <!-- <
                                            text = str(epResult['episode'])
                                            if epLoc != '' and epLoc is not None:
                                                text = '<span title="' + epLoc + '" class="addQTip">' + text + '</span>'
                                                epCount += 1
                                                if not epLoc in epList:
                                                    epSize += epResult['file_size']
                                                    epList.append(epLoc)
                                        -->
                                            <span :title="episode.location !== '' ? episode.location : ''" :class="{addQTip: episode.location !== ''}">{{episode.episode}}</span>
                                        </td>
                                        <td align="center" class="triggerhighlight">{{episode.scene.absoluteNumber || 0}}</td>
                                        <td align="center" class="triggerhighlight">
                                            <input type="text" :placeholder="getSceneNumbering(episode).season + 'x' + getSceneNumbering(episode).episode" size="6" maxlength="8"
                                                class="sceneSeasonXEpisode form-control input-scene" :data-for-season="episode.season" :data-for-episode="episode.episode"
                                                :id="'sceneSeasonXEpisode_' + show.id[show.indexer] + '_' + episode.season + '_' + episode.episode"
                                                title="Change this value if scene numbering differs from the indexer episode numbering. Generally used for non-anime shows."
                                                :value="getSceneNumbering(episode).season + 'x' + getSceneNumbering(episode).episode"
                                                style="padding: 0; text-align: center; max-width: 60px;"/>
                                        </td>
                                        <td align="center" class="triggerhighlight">
                                            <input type="text" :placeholder="getSceneAbsoluteNumbering(episode)" size="6" maxlength="8"
                                                class="sceneAbsolute form-control input-scene" :data-for-absolute="episode.absoluteNumber || 0"
                                                :id="'sceneSeasonXEpisode_' + show.id[show.indexer] + episode.absoluteNumber"
                                                title="Change this value if scene absolute numbering differs from the indexer absolute numbering. Generally used for anime shows."
                                                :value="getSceneAbsoluteNumbering(episode) ? getSceneAbsoluteNumbering(episode) : ''"
                                                style="padding: 0; text-align: center; max-width: 60px;"/>
                                        </td>
                                        <td class="col-name hidden-xs triggerhighlight">
                                            <!-- < has_plot = 'has-plot' if epResult['description'] else '' > -->
                                            <plot-info :has-plot="episode.description ? true : false" :show-slug="indexer + id" :season="String(episode.season)" episode="String(episode.episode)"></plot-info>
                                            <!-- {epResult['name']} --> {{episode.title}}
                                        </td>
                                        <td class="col-name hidden-xs triggerhighlight">{{episode.file.location}}</td>
                                        <td class="col-ep triggerhighlight">
                                            <span v-if="episode.file">{{humanFileSize(episode.file.size)}}</span> 
                                        </td>
                                        <td class="col-airdate triggerhighlight">
                                                <!-- if int(epResult['airdate']) != 1:
                                                ## Lets do this exactly like ComingEpisodes and History
                                                ## Avoid issues with dateutil's _isdst on Windows but still provide air dates
                                                < airDate = datetime.datetime.fromordinal(epResult['airdate']) >
                                                    if airDate.year >= 1970 or show.network:
                                                     airDate = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(epResult['airdate'], show.airs, show.network)) >
                                                    endif
                                                <time datetime="{airDate.isoformat('T')}" class="date">{sbdatetime.sbdatetime.sbfdatetime(airDate)}</time>
                                                else:
                                                Never
                                                endif -->
                                                {{episode.airDate}}
                                        </td>
                                        <td class="triggerhighlight">
                                                <!-- if app.DOWNLOAD_URL and epResult['location'] and int(epResult['status']) in [DOWNLOADED, ARCHIVED]:
                                                <
                                                    filename = epResult['location']
                                                    for rootDir in app.ROOT_DIRS:
                                                        if rootDir.startswith('/'):
                                                            filename = filename.replace(rootDir, '')
                                                    filename = app.DOWNLOAD_URL + urllib.quote(filename.encode('utf8'))
                                                > -->
                                                <app-link v-if="config.downloadUrl && episode.file.location && ['Downloaded', 'Archived'].includes(episode.status)" :href="config.downloadUrl + episode.file.location">Download</app-link>
                                                <!-- endif -->
                                        </td>
                                        <td class="col-subtitles triggerhighlight" align="center">
                                            <div class="subtitles" v-if="['Archived', 'Downloaded', 'Ignored', 'Skipped'].includes(episode.status)" v-for="flag in episode.subtitles">
                                                <app-link v-if="flag !== 'und'" class="epRedownloadSubtitle" href="home/searchEpisodeSubtitles?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + episode.season + '&episode='episode.episode' + '&lang=' + flag">
                                                    <img :src="'images/subtitles/flags/' + flag + '.png'" width="16" height="11" alt="{flag}" onError="this.onerror=null;this.src='images/flags/unknown.png';"/>
                                                </app-link>
                                                <img v-if="flag === 'und'" :src="'images/subtitles/flags/' + flag + '.png'" width="16" height="11" alt="flag" onError="this.onerror=null;this.src='images/flags/unknown.png';" />
                                            </div>
                                        </td>
                                        <td v-if="episode.quality !== 'N/A'" class="col-status triggerhighlight">{{episode.status}} 
                                            <quality-pill v-if="episode.quality !== 'N/A'" :quality="episode.quality"></quality-pill>
                                        </td>
                                        <td class="col-search triggerhighlight">
                                                <!-- if int(epResult['season']) != 0: -->
                                            <div >
                                                <app-link v-if="episode.season !== 0" :class="retryDownload(episode) ? 'epRetry' : 'epSearch'" :id="show.indexer + 'x' + show.id[show.indexer] + 'x' + episode.season + 'x' + episode.episode" :name="show.indexer + 'x' + show.id[show.indexer] + 'x' + episode.season + 'x' + episode.episode" :href="'home/' + (retryDownload(episode) ? 'retryEpisode' : 'searchEpisode') + '?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + episode.season + '&episode=' + episode.episode"><img data-ep-search src="images/search16.png" height="16" alt="retryDownload(episode) ? 'retry' : 'search'" title="retryDownload(episode) ? 'Retry Download' : 'Forced Seach'"/></app-link>
                                                <app-link class="epManualSearch" :id="show.indexer + 'x' + show.id[show.indexer] + 'x' + episode.season + 'x' + episode.episode" :name="show.indexer + 'x' + show.id[show.indexer] + 'x' + episode.season + 'x' + episode.episode" href="home/snatchSelection?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + episode.season + '&episode='episode.episode"><img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" /></app-link>
                                                <app-link v-if="showSubtitleButton(episode)" class="epSubtitlesSearch" :href="'home/searchEpisodeSubtitles?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + episode.season + '&episode=' + episode.episode"><img src="images/closed_captioning.png" height="16" alt="search subtitles" title="Search Subtitles" /></app-link>
                                            </div>
                                        </td>
                                    </tr>
                                    <!-- end of the season episodes -->
                                    <!-- if sql_results: -->
                                <tr v-if="season.episodes.length > 0" :id="'season-' + season.season + '-footer'" class="seasoncols border-bottom shadow">
                                    <th class="col-footer" colspan=15 align=left>Season contains {{season.episodes.length}} episodes with total filesize: {{humanFileSize(totalSeasonEpisodeSize(season))}}</th>
                                </tr>
                                <!-- endif -->
                                </tbody>
                                    
                        </div>                    
                    </div>
                    <tbody class="tablesorter-no-sort"><tr><th class="row-seasonheader" colspan=15></th></tr></tbody>
            </table>
        </div>
    </div>

    <!--Begin - Bootstrap Modals-->
    <div id="forcedSearchModalFailed" class="modal fade">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h4 class="modal-title">Forced Search</h4>
                </div>
                <div class="modal-body">
                    <p>Do you want to mark this episode as failed?</p>
                    <p class="text-warning"><small>The episode release name will be added to the failed history, preventing it to be downloaded again.</small></p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn-medusa btn-danger" data-dismiss="modal">No</button>
                    <button type="button" class="btn-medusa btn-success" data-dismiss="modal">Yes</button>
                </div>
            </div>
        </div>
    </div>
    <div id="forcedSearchModalQuality" class="modal fade">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h4 class="modal-title">Forced Search</h4>
                </div>
                <div class="modal-body">
                    <p>Do you want to include the current episode quality in the search?</p>
                    <p class="text-warning"><small>Choosing No will ignore any releases with the same episode quality as the one currently downloaded/snatched.</small></p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn-medusa btn-danger" data-dismiss="modal">No</button>
                    <button type="button" class="btn-medusa btn-success" data-dismiss="modal">Yes</button>
                </div>
            </div>
        </div>
    </div>
    <div id="confirmSubtitleReDownloadModal" class="modal fade">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h4 class="modal-title">Re-download subtitle</h4>
                </div>
                <div class="modal-body">
                    <p>Do you want to re-download the subtitle for this language?</p>
                    <p class="text-warning"><small>It will overwrite your current subtitle</small></p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn-medusa btn-danger" data-dismiss="modal">No</button>
                    <button type="button" class="btn-medusa btn-success" data-dismiss="modal">Yes</button>
                </div>
            </div>
        </div>
    </div>
    <div id="askmanualSubtitleSearchModal" class="modal fade">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h4 class="modal-title">Subtitle search</h4>
                </div>
                <div class="modal-body">
                    <p>Do you want to manually pick subtitles or let us choose it for you?</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn-medusa btn-info" data-dismiss="modal">Auto</button>
                    <button type="button" class="btn-medusa btn-success" data-dismiss="modal">Manual</button>
                </div>
            </div>
        </div>
    </div>

    <%include file="subtitle_modal.mako"/>
    <!--End - Bootstrap Modal-->
</div>
</script>
<script type="text/javascript" src="js/rating-tooltip.js?${sbPID}"></script>
<script type="text/javascript" src="js/ajax-episode-search.js?${sbPID}"></script>
<script type="text/javascript" src="js/ajax-episode-subtitles.js?${sbPID}"></script>
<script>
const { store, router } = window;

window.app = {};
window.app = new Vue({
    el: '#vue-wrap',
    store,
    router,
    data() {
        return {
            // This loads show.vue
            pageComponent: 'show'
        }
    },
    created() {
        const { $store } = this;
        // Needed for the show-selector component
        $store.dispatch('getShows');
    }
});
</script>
</%block>
