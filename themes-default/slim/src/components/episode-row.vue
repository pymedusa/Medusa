<template>
    <tr v-if="show && config" :class="episode.status.toLowerCase() + ' season-' + episode.season + ' seasonstyle'" :id="'S' + episode.season + 'E' + episode.episode">
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
            <plot-info :has-plot="Boolean(episode.description)" :show-slug="show.id.slug" :season="String(episode.season)" episode="String(episode.episode)"></plot-info>
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
            <div v-if="['Archived', 'Downloaded', 'Ignored', 'Skipped'].includes(episode.status)">
                <div class="subtitles" v-for="flag in episode.subtitles" :key="flag">
                    <app-link v-if="flag !== 'und'" class="epRedownloadSubtitle" href="home/searchEpisodeSubtitles?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + episode.season + '&episode='episode.episode' + '&lang=' + flag">
                        <img :src="'images/subtitles/flags/' + flag + '.png'" width="16" height="11" alt="{flag}" onError="this.onerror=null;this.src='images/flags/unknown.png';"/>
                    </app-link>
                    <img v-if="flag === 'und'" :src="'images/subtitles/flags/' + flag + '.png'" width="16" height="11" alt="flag" onError="this.onerror=null;this.src='images/flags/unknown.png';" />
                </div>
            </div>
        </td>
        <td class="col-status triggerhighlight">{{episode.status}} 
            <quality-pill v-if="episode.quality !== 0" :quality="episode.quality"></quality-pill>
        </td>
        <td class="col-search triggerhighlight">
            <div >
                <app-link v-if="episode.season !== 0" :class="retryDownload(episode) ? 'epRetry' : 'epSearch'" :id="show.indexer + 'x' + show.id[show.indexer] + 'x' + episode.season + 'x' + episode.episode" :name="show.indexer + 'x' + show.id[show.indexer] + 'x' + episode.season + 'x' + episode.episode" :href="'home/' + (retryDownload(episode) ? 'retryEpisode' : 'searchEpisode') + '?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + episode.season + '&episode=' + episode.episode"><img data-ep-search src="images/search16.png" height="16" alt="retryDownload(episode) ? 'retry' : 'search'" title="retryDownload(episode) ? 'Retry Download' : 'Forced Seach'"/></app-link>
                <app-link class="epManualSearch" :id="show.indexer + 'x' + show.id[show.indexer] + 'x' + episode.season + 'x' + episode.episode" :name="show.indexer + 'x' + show.id[show.indexer] + 'x' + episode.season + 'x' + episode.episode" :href="'home/snatchSelection?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + episode.season + '&episode=' + episode.episode"><img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" /></app-link>
                <app-link v-if="showSubtitleButton(episode)" class="epSubtitlesSearch" :href="'home/searchEpisodeSubtitles?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + episode.season + '&episode=' + episode.episode"><img src="images/closed_captioning.png" height="16" alt="search subtitles" title="Search Subtitles" /></app-link>
            </div>
        </td>
    </tr>
</template>
<script>

import { mapState } from 'vuex';
import { humanFileSize } from '../utils';

export default {
    name: 'episode-row',
    props: {
        show: {
            type: Object
        },
        episode: {
            type: Object
        }
    },
    computed: {
        ...mapState({
            configLoaded: state => state.config.fanartBackground !== null,
            config: state => state.config            
        }),
    },
    methods: {
        humanFileSize,
        /**
         * Check if the season/episode combination exists in the scene numbering.
         */
        getSceneNumbering(episode) {
            const { show } = this;
            const { xemNumbering } = show;

            if (xemNumbering.length !== 0) {
                const mapped = xemNumbering.filter(x => {
                    return x.source.season === episode.season && x.source.episode === episode.episode;
                });
                if (mapped.length !== 0) {
                    return mapped[0].destination;
                }
            }
            return { season: 0, episode: 0 };
        },
        getSceneAbsoluteNumbering(episode) {
            const { show } = this;
            const { sceneAbsoluteNumbering, xemAbsoluteNumbering } = show;  
            const xemAbsolute = xemAbsoluteNumbering[episode.absoluteNumber];

            if (Object.keys(sceneAbsoluteNumbering).length > 0) {
                return sceneAbsoluteNumbering[episode.absoluteNumber];
            } else if (xemAbsolute) {
                return xemAbsolute;
            }
            return 0;
        },
        retryDownload(episode) {
            const { config } = this;
            return (config.failedDownloads.enabled && ['Snatched', 'Snatched (Proper)', 'Snatched (Best)', 'Downloaded'].includes(episode.status));
        },
        showSubtitleButton(episode) {
            const { config, show } = this;
            return (episode.season !== 0 && config.subtitles.enabled && show.config.subtitlesEnabled && !['Snatched', 'Snatched (Proper)', 'Snatched (Best)', 'Downloaded'].includes(episode.status));
        },
        totalSeasonEpisodeSize(season) {
            return season.episodes.filter(x => x.file && x.file.size > 0).reduce((a, b) => a + b.file.size, 0);
        },
        getSeasonExceptions(season) {
            const { show } = this;
            const { allSceneExceptions } = show;
            let bindData = { class: 'display: none' };

            // Map the indexer season to a xem mapped season.
            // check if the season exception also exists in the xem numbering table

            let xemSeasons = [];
            let foundInXem = false;
            if (show.xemNumbering.length > 0) {
                const xemResult = show.xemNumbering.filter(x => x.source.season === season);
                // Create an array with unique seasons
                xemSeasons = [...new Set(xemResult.map(item => item.destination.season))];
                foundInXem = Boolean(xemSeasons.length);
            }

            // Check if there is a season exception for this season
            if (allSceneExceptions[season]) {
                // if there is not a match on the xem table, display it as a medusa scene exception
                bindData = {
                    id: `xem-exception-season-${foundInXem ? xemSeasons[0] : season}`,
                    alt: foundInXem ? '[xem]' : '[medusa]',
                    src: foundInXem ? 'images/xem.png' : 'images/ico/favicon-16.png',
                    title: xemSeasons.reduce(function (a, b) {
                        return a = a.concat(allSceneExceptions[b]);
                    }, []).join(', '),
                }
            }

            return bindData;
        }
    }
};
</script>
<style>
</style>
