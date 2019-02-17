<template>
    <div class="show-header-container">
        <div class="row">
            <!-- @TODO: Remove data attributes -->
            <!-- @SEE: https://github.com/pymedusa/Medusa/pull/5087#discussion_r214074436 -->
            <div v-if="show" id="showtitle" class="col-lg-12" :data-showname="show.title">
                <div>
                    <!-- @TODO: Remove data attributes -->
                    <!-- @SEE: https://github.com/pymedusa/Medusa/pull/5087#discussion_r214077142 -->
                    <h1 class="title" :data-indexer-name="show.indexer" :data-series-id="show.id[show.indexer]" :id="'scene_exception_' + show.id[show.indexer]">
                        <app-link :href="'home/displayShow?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer]" class="snatchTitle">{{ show.title }}</app-link>
                    </h1>
                </div>

                <div v-if="type === 'snatch-selection'" id="show-specials-and-seasons" class="pull-right">
                    <span class="h2footer display-specials">
                        Manual search for:<br>
                        <app-link
                            :href="'home/displayShow?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer]"
                            class="snatchTitle"
                            >{{ show.title }}</app-link> / Season {{ season }}<template v-if="episode && manualSearchType !== 'season'"> Episode {{ episode }}</template>
                    </span>
                </div>
                <div v-if="type !== 'snatch-selection' && show.seasons && show.seasons.length >= 1" id="show-specials-and-seasons" class="pull-right">
                    <span class="h2footer display-specials" v-if="show.seasons.find(season => ({ season }) => season === 0)">
                        Display Specials: <a @click="toggleSpecials()" class="inner" style="cursor: pointer;">{{ displaySpecials ? 'Hide' : 'Show' }}</a>
                    </span>

                    <div class="h2footer display-seasons clear">
                        <span>
                            <select v-if="show.seasons.length >= 15" v-model="jumpToSeason" id="seasonJump" class="form-control input-sm" style="position: relative">
                                <option value="jump">Jump to Season</option>
                                <option v-for="season in show.seasons" :key="'jumpToSeason-' + season[0].season" :value="'#season-' + season[0].season" :data-season="season[0].season">
                                    {{ season[0].season === 0 ? 'Specials' : 'Season ' + season[0].season }}
                                </option>
                            </select>
                            <template v-else-if="show.seasons.length >= 1">
                                Season:
                                <template v-for="(season, $index) in reverse(show.seasons)">
                                    <app-link :href="'#season-' + season[0].season" :key="`jumpToSeason-${season[0].season}`">{{ season[0].season === 0 ? 'Specials' : season[0].season }}</app-link>
                                    <slot> </slot>
                                    <span v-if="$index !== (show.seasons.length - 1)" :key="`separator-${$index}`" class="separator">| </span>
                                </template>
                            </template>
                        </span>
                    </div>
                </div>
            </div> <!-- end show title -->
        </div> <!-- end row showtitle-->

        <div v-for="queueItem of activeShowQueueStatuses" :key="queueItem.action" class="row">
            <div class="alert alert-info">
                {{ queueItem.message }}
            </div>
        </div>

        <div id="row-show-summary" class="row">
            <div id="col-show-summary" class="col-md-12">
                <div class="show-poster-container">
                    <div class="row">
                        <div class="image-flex-container col-md-12">
                            <asset default="images/poster.png" :show-slug="show.id.slug" type="posterThumb" cls="show-image shadow" :link="true"></asset>
                        </div>
                    </div>
                </div>

                <div class="ver-spacer"></div>

                <div class="show-info-container">
                    <div class="row">
                        <div class="pull-right col-lg-3 col-md-3 hidden-sm hidden-xs">
                            <asset default="images/banner.png" :show-slug="show.id.slug" type="banner" cls="show-banner pull-right shadow" :link="true"></asset>
                        </div>
                        <div id="show-rating" class="pull-left col-lg-9 col-md-9 col-sm-12 col-xs-12">
                            <span v-if="show.rating.imdb && show.rating.imdb.rating"
                                class="imdbstars"
                                :qtip-content="show.rating.imdb.rating + ' / 10 Stars<br> ' + show.rating.imdb.votes + ' Votes'"
                            >
                                <span :style="{ width: (Number(show.rating.imdb.rating) * 12) + '%' }"></span>
                            </span>
                            <template v-if="!show.id.imdb">
                                <span v-if="show.year.start">({{ show.year.start }}) - {{ show.runtime }} minutes - </span>
                            </template>
                            <template v-else>
                                <img v-for="country in show.countryCodes" :key="'flag-' + country" src="images/blank.png" :class="['country-flag', 'flag-' + country]" width="16" height="11" style="margin-left: 3px; vertical-align:middle;" />
                                <span v-if="show.imdbInfo.year">
                                    ({{ show.imdbInfo.year }}) -
                                </span>
                                <span>
                                    {{ show.imdbInfo.runtimes || show.runtime }} minutes
                                </span>
                                <app-link :href="'https://www.imdb.com/title/' + show.id.imdb" :title="'https://www.imdb.com/title/' + show.id.imdb">
                                    <img alt="[imdb]" height="16" width="16" src="images/imdb.png" style="margin-top: -1px; vertical-align:middle;"/>
                                </app-link>
                            </template>
                            <app-link v-if="show.id.trakt" :href="'https://trakt.tv/shows/' + show.id.trakt" :title="'https://trakt.tv/shows/' + show.id.trakt">
                                <img alt="[trakt]" height="16" width="16" src="images/trakt.png" />
                            </app-link>
                            <app-link v-if="showIndexerUrl && indexerConfig[show.indexer].icon" :href="showIndexerUrl" :title="showIndexerUrl">
                                <img :alt="indexerConfig[show.indexer].name" height="16" width="16" :src="'images/' + indexerConfig[show.indexer].icon" style="margin-top: -1px; vertical-align:middle;"/>
                            </app-link>

                            <app-link v-if="show.xemNumbering" :href="'http://thexem.de/search?q=' + show.title" :title="'http://thexem.de/search?q=' + show.title">
                                <img alt="[xem]" height="16" width="16" src="images/xem.png" style="margin-top: -1px; vertical-align:middle;"/>
                            </app-link>

                            <app-link v-if="show.id.tvdb" :href="'https://fanart.tv/series/' + show.id.tvdb" :title="'https://fanart.tv/series/' + show.id[show.indexer]">
                                <img alt="[fanart.tv]" height="16" width="16" src="images/fanart.tv.png" class="fanart"/>
                            </app-link>
                        </div>
                        <div id="tags" class="pull-left col-lg-9 col-md-9 col-sm-12 col-xs-12">
                            <ul class="tags" v-if="show.genres">
                                <app-link v-for="genre in dedupeGenres(show.genres)" :key="genre.toString()" :href="'https://trakt.tv/shows/popular/?genres=' + genre.toLowerCase().replace(' ', '-')" :title="'View other popular ' + genre + ' shows on trakt.tv'"><li>{{ genre }}</li></app-link>
                            </ul>
                            <ul class="tags" v-else>
                                <app-link v-for="genre in showGenres" :key="genre.toString()" :href="'https://www.imdb.com/search/title?count=100&title_type=tv_series&genres=' + genre.toLowerCase().replace(' ', '-')" :title="'View other popular ' + genre + ' shows on IMDB'"><li>{{ genre }}</li></app-link>
                            </ul>
                        </div>
                    </div>

                    <div class="row">
                        <!-- Show Summary -->
                        <div id="summary" class="col-md-12">
                            <div id="show-summary" :class="[{ summaryFanArt: config.fanartBackground }, 'col-lg-9', 'col-md-8', 'col-sm-8', 'col-xs-12']">
                                <table class="summaryTable pull-left">
                                    <tr v-if="show.plot">
                                        <td colspan="2" style="padding-bottom: 15px;">
                                            <truncate @toggle="$emit('reflow')" :length="250" clamp="show more..." less="show less..." :text="show.plot"></truncate>
                                        </td>
                                    </tr>

                                    <!-- Preset -->
                                    <tr v-if="getPreset(combineQualities(show.config.qualities.allowed)).length > 0">
                                    <td class="showLegend">Quality: </td><td>
                                    <quality-pill :quality="combineQualities(show.config.qualities.allowed)"></quality-pill>
                                    </td></tr>

                                    <!-- Custom quality -->
                                    <tr v-if="!getPreset(combineQualities(show.config.qualities.allowed)).length > 0 && show.config.qualities.allowed">
                                    <td class="showLegend">Quality allowed:</td><td>
                                        <template v-for="(curQuality, $index) in show.config.qualities.allowed">
                                            <template v-if="$index > 0">&comma;</template>
                                            <quality-pill :quality="curQuality" :key="'allowed-' + curQuality"></quality-pill>
                                        </template>
                                    </td></tr>

                                    <tr v-if="!getPreset(combineQualities(show.config.qualities.allowed)).length > 0 && combineQualities(show.config.qualities.preferred).length > 0">
                                        <td class="showLegend">Quality preferred:</td><td>
                                            <template v-for="(curQuality, $index) in show.config.qualities.preferred">
                                            <template v-if="$index > 0">&comma;</template>
                                            <quality-pill :quality="curQuality" :key="'preferred-' + curQuality"></quality-pill>
                                        </template>
                                    </td></tr>

                                    <tr v-if="show.network && show.airs"><td class="showLegend">Originally Airs: </td><td>{{ show.airs }} <font v-if="!show.airsFormatValid" color='#FF0000'><b>(invalid Timeformat)</b></font> on {{ show.network }}</td></tr>
                                    <tr v-else-if="show.network"><td class="showLegend">Originally Airs: </td><td>{{ show.network }}</td></tr>
                                    <tr v-else-if="show.airs"><td class="showLegend">Originally Airs: </td><td>{{ show.airs }} <font v-if="!show.airsFormatValid" color='#FF0000'><b>(invalid Timeformat)</b></font></td></tr>
                                    <tr><td class="showLegend">Show Status: </td><td>{{ show.status }}</td></tr>
                                    <tr><td class="showLegend">Default EP Status: </td><td>{{ show.config.defaultEpisodeStatus }}</td></tr>
                                    <tr><td class="showLegend"><span :class="{'location-invalid': !show.config.locationValid}">Location: </span></td><td><span :class="{'location-invalid': !show.config.locationValid}">{{show.config.location}}</span>{{show.config.locationValid ? '' : ' (Missing)'}}</td></tr>

                                    <tr v-if="show.config.aliases.length > 0">
                                        <td class="showLegend" style="vertical-align: top;">Scene Name:</td>
                                        <td>{{show.config.aliases.join(',')}}</td>
                                    </tr>

                                    <tr v-if="show.config.release.requiredWords.length > 0">
                                        <td class="showLegend" style="vertical-align: top;">Required Words: </td>
                                        <td><span class="break-word" :class="{required: type === 'snatch-selection'}">{{show.config.release.requiredWords.join(',')}}</span></td>
                                    </tr>
                                    <tr v-if="show.config.release.ignoredWords.length > 0">
                                        <td class="showLegend" style="vertical-align: top;">Ignored Words: </td>
                                        <td><span class="break-word" :class="{ignored: type === 'snatch-selection'}">{{show.config.release.ignoredWords.join(',')}}</span></td>
                                    </tr>

                                    <tr v-if="preferredWords.length > 0">
                                        <td class="showLegend" style="vertical-align: top;">Preferred Words: </td>
                                        <td><span class="break-word" :class="{preferred: type === 'snatch-selection'}">{{preferredWords.join(',')}}</span></td>
                                    </tr>
                                    <tr v-if="undesiredWords.length > 0">
                                        <td class="showLegend" style="vertical-align: top;">Undesired Words: </td>
                                        <td><span class="break-word" :class="{undesired: type === 'snatch-selection'}">{{undesiredWords.join(',')}}</span></td>
                                    </tr>

                                    <tr v-if="show.config.release.whitelist && show.config.release.whitelist.length > 0">
                                        <td class="showLegend">Wanted Groups:</td>
                                        <td>{{show.config.release.whitelist.join(',')}}</td>
                                    </tr>

                                    <tr v-if="show.config.release.blacklist && show.config.release.blacklist.length > 0">
                                        <td class="showLegend">Unwanted Groups:</td>
                                        <td>{{show.config.release.blacklist.join(',')}}</td>
                                    </tr>

                                    <tr v-if="show.config.airdateOffset !== 0">
                                        <td class="showLegend">Daily search offset:</td>
                                        <td>{{show.config.airdateOffset}} hours</td>
                                    </tr>
                                    <tr v-if="show.config.locationValid && show.size > -1">
                                        <td class="showLegend">Size:</td>
                                        <td>{{humanFileSize(show.size)}}</td>
                                    </tr>
                                </table><!-- Option table right -->
                            </div>

                            <!-- Option table right -->
                            <div id="show-status" class="col-lg-3 col-md-4 col-sm-4 col-xs-12 pull-xs-left">
                                <table class="pull-xs-left pull-md-right pull-sm-right pull-lg-right">
                                    <tr v-if="show.language"><td class="showLegend">Info Language:</td><td><img :src="'images/subtitles/flags/' + getCountryISO2ToISO3(show.language) + '.png'" width="16" height="11" :alt="show.language" :title="show.language" onError="this.onerror=null;this.src='images/flags/unknown.png';"/></td></tr>
                                    <tr v-if="config.subtitles.enabled"><td class="showLegend">Subtitles: </td><td><state-switch :theme="config.themeName" :state="show.config.subtitlesEnabled"></state-switch></td></tr>
                                    <tr><td class="showLegend">Season Folders: </td><td><state-switch :theme="config.themeName" :state="show.config.seasonFolders || config.namingForceFolders"></state-switch></td></tr>
                                    <tr><td class="showLegend">Paused: </td><td><state-switch :theme="config.themeName" :state="show.config.paused"></state-switch></td></tr>
                                    <tr><td class="showLegend">Air-by-Date: </td><td><state-switch :theme="config.themeName" :state="show.config.airByDate"></state-switch></td></tr>
                                    <tr><td class="showLegend">Sports: </td><td><state-switch :theme="config.themeName" :state="show.config.sports"></state-switch></td></tr>
                                    <tr><td class="showLegend">Anime: </td><td><state-switch :theme="config.themeName" :state="show.config.anime"></state-switch></td></tr>
                                    <tr><td class="showLegend">DVD Order: </td><td><state-switch :theme="config.themeName" :state="show.config.dvdOrder"></state-switch></td></tr>
                                    <tr><td class="showLegend">Scene Numbering: </td><td><state-switch :theme="config.themeName" :state="show.config.scene"></state-switch></td></tr>
                                </table>
                            </div> <!-- end of show-status -->
                        </div> <!-- end of summary -->
                    </div> <!-- end of row -->
                </div> <!-- show-info-container -->
            </div> <!-- end of col -->
        </div> <!-- end of row row-show-summary-->

        <div v-if="show" id="row-show-episodes-controls" class="row">
            <div id="col-show-episodes-controls" class="col-md-12">
                <div v-if="type === 'show'" class="row key"> <!-- Checkbox filter controls -->
                    <div class="col-lg-12" id="checkboxControls">
                        <div id="key-padding" class="pull-left top-5">

                            <label v-if="show.seasons" for="wanted"><span class="wanted"><input type="checkbox" id="wanted" checked="checked" @input="showHideRows('wanted')" /> Wanted: <b>{{episodeSummary.Wanted}}</b></span></label>
                            <label v-if="show.seasons" for="qual"><span class="qual"><input type="checkbox" id="qual" checked="checked" @input="showHideRows('qual')" /> Allowed: <b>{{episodeSummary.Allowed}}</b></span></label>
                            <label v-if="show.seasons" for="good"><span class="good"><input type="checkbox" id="good" checked="checked" @input="showHideRows('good')" /> Preferred: <b>{{episodeSummary.Preferred}}</b></span></label>
                            <label v-if="show.seasons" for="skipped"><span class="skipped"><input type="checkbox" id="skipped" checked="checked" @input="showHideRows('skipped')" /> Skipped: <b>{{episodeSummary.Skipped}}</b></span></label>
                            <label v-if="show.seasons" for="snatched"><span class="snatched"><input type="checkbox" id="snatched" checked="checked" @input="showHideRows('snatched')" /> Snatched: <b>{{episodeSummary.Snatched + episodeSummary['Snatched (Proper)'] + episodeSummary['Snatched (Best)']}}</b></span></label>
                            <button class="btn-medusa seriesCheck" @click="selectEpisodesClicked">Select Episodes</button>
                            <button class="btn-medusa clearAll" @click="clearEpisodeSelectionClicked">Clear</button>
                        </div>
                        <div class="pull-lg-right top-5">

                            <select id="statusSelect" class="form-control form-control-inline input-sm-custom input-sm-smallfont">
                                <option v-for="option in changeStatusOptions" :key="option.value" :value="option.value">
                                    {{option.text}}
                                </option>
                            </select>

                            <select id="qualitySelect" class="form-control form-control-inline input-sm-custom input-sm-smallfont">
                                <option v-for="option in changeQualityOptions" :key="option.value" :value="option.value">
                                    {{option.text}}
                                </option>
                            </select>
                            <input type="hidden" id="series-slug" :value="show.id.slug" />
                            <input type="hidden" id="series-id" :value="show.id[show.indexer]" />
                            <input type="hidden" id="indexer" :value="show.indexer" />
                            <input class="btn-medusa" type="button" id="changeStatus" value="Go" @click="changeStatusClicked" />
                        </div>
                    </div> <!-- checkboxControls -->
                </div> <!-- end of row -->
                <div v-else></div>
            </div> <!-- end of col -->
        </div> <!-- end of row -->
    </div>
</template>

<script>
import Truncate from 'vue-truncate-collapsed';
import { getLanguage } from 'country-language';
import { isVisible } from 'is-visible';
import { scrollTo } from 'vue-scrollto';
import { mapState, mapGetters } from 'vuex';
import { api } from '../api';
import { humanFileSize } from '../utils';
import { AppLink, Asset, QualityPill, StateSwitch } from './helpers';

export default {
    name: 'show-header',
    components: {
        AppLink,
        Asset,
        QualityPill,
        StateSwitch,
        Truncate
    },
    props: {
        /**
         * Page type: show or snatch-selection
         */
        type: {
            type: String,
            default: 'show',
            validator: value => [
                'show',
                'snatch-selection'
            ].includes(value)
        },
        /**
         * Show indexer
         */
        showIndexer: {
            type: String
        },
        /**
         * Show id
         */
        showId: {
            type: Number
        },
        /**
         * Season
         */
        showSeason: {
            type: Number
        },
        /**
         * Episode
         */
        showEpisode: {
            type: Number
        },
        /**
         * Manual Search Type (snatch-selection)
         */
        manualSearchType: {
            type: String
        }
    },
    data() {
        return {
            jumpToSeason: 'jump'
        };
    },
    computed: {
        ...mapState({
            shows: state => state.shows.shows,
            indexerConfig: state => state.config.indexers.config.indexers,
            failedDownloads: state => state.config.failedDownloads,
            displaySpecials: state => state.config.layout.show.specials,
            qualities: state => state.qualities,
            search: state => state.search
        }),
        ...mapGetters({
            show: 'getCurrentShow',
            getPreset: 'getPreset',
            combineQualities: 'combineQualities'
        }),
        indexer() {
            return this.showIndexer || this.$route.query.indexername;
        },
        id() {
            return this.showId || Number(this.$route.query.seriesid) || undefined;
        },
        season() {
            return this.showSeason || Number(this.$route.query.season) || undefined;
        },
        episode() {
            return this.showEpisode || Number(this.$route.query.episode) || undefined;
        },
        showIndexerUrl() {
            const { show, indexerConfig } = this;
            if (!show.indexer) {
                return;
            }
            const id = show.id[show.indexer];
            const indexerUrl = indexerConfig[show.indexer].showUrl;

            return `${indexerUrl}${id}`;
        },
        activeShowQueueStatuses() {
            const { showQueueStatus } = this.show;
            if (!showQueueStatus) {
                return [];
            }
            return showQueueStatus.filter(status => status.active === true);
        },
        showGenres() {
            const { show, dedupeGenres } = this;
            const { imdbInfo } = show;
            const { genres } = imdbInfo;
            let result = [];

            if (genres) {
                result = dedupeGenres(genres.split('|'));
            }
            return result;
        },
        preferredWords() {
            const { preferred } = this.search.filters;
            if (preferred.length > 0) {
                return preferred;
            }
            return [];
        },
        undesiredWords() {
            const { undesired } = this.search.filters;
            if (undesired.length > 0) {
                return undesired;
            }
            return [];
        },
        episodeSummary() {
            const { show } = this;
            const { seasons } = show;
            const summary = {
                Skipped: 0,
                Wanted: 0,
                Allowed: 0,
                Preferred: 0,
                Unaired: 0,
                Snatched: 0,
                'Snatched (Proper)': 0,
                'Snatched (Best)': 0,
                Unset: 0,
                Archived: 0
            };
            seasons.forEach(episodes => {
                episodes.forEach(episode => {
                    summary[episode.status] += 1;
                });
            });
            return summary;
        },
        changeStatusOptions() {
            const { failedDownloads } = this;

            const defaultOptions = [
                { text: 'Change status to:', value: null },
                { text: 'Wanted', value: 3 },
                { text: 'Skipped', value: 5 },
                { text: 'Ignored', value: 7 },
                { text: 'Downloaded', value: 4 },
                { text: 'Archived', value: 6 }
            ];

            if (failedDownloads.enabled) {
                defaultOptions.push({ text: 'Failed', value: 11 });
            }

            return defaultOptions;
        },
        changeQualityOptions() {
            const { qualities } = this;

            const defaultOptions = [
                { text: 'Change quality to:', value: null }
            ];

            if (qualities.strings) {
                Object.keys(qualities.strings.values).forEach(key => {
                    defaultOptions.push({
                        text: qualities.strings.values[key],
                        value: key
                    });
                });
            }

            return defaultOptions;
        }
    },
    methods: {
        humanFileSize,
        setQuality(quality, showSlug, episodes) {
            const patchData = {};
            episodes.forEach(episode => {
                patchData[episode] = { quality: parseInt(quality, 10) };
            });

            api.patch('series/' + showSlug + '/episodes', patchData).then(response => {
                console.info(response.data);
                window.location.reload();
            }).catch(error => {
                console.error(error.data);
            });
        },
        changeStatusClicked() {
            const { setQuality } = this;

            const epArr = [];
            const status = $('#statusSelect').val();
            const quality = $('#qualitySelect').val();
            const showSlug = $('#series-slug').val();

            $('.epCheck').each((index, element) => {
                if (element.checked === true) {
                    epArr.push($(element).attr('id'));
                }
            });

            if (epArr.length === 0) {
                return false;
            }

            if (quality) {
                setQuality(quality, showSlug, epArr);
            }

            if (status) {
                window.location.href = $('base').attr('href') + 'home/setStatus?' +
                    'indexername=' + $('#indexer-name').attr('value') +
                    '&seriesid=' + $('#series-id').attr('value') +
                    '&eps=' + epArr.join('|') +
                    '&status=' + status;
            }
        },
        showHideRows(whichClass) {
            const status = $('#checkboxControls > input, #' + whichClass).prop('checked');
            $('tr.' + whichClass).each((index, element) => {
                if (status) {
                    $(element).show();
                } else {
                    $(element).hide();
                }
            });

            // Hide season headers with no episodes under them
            $('tr.seasonheader').each((index, element) => {
                let numRows = 0;
                const seasonNo = $(element).attr('id');
                $('tr.' + seasonNo + ' :visible').each(() => {
                    numRows++;
                });
                if (numRows === 0) {
                    $(element).hide();
                    $('#' + seasonNo + '-cols').hide();
                } else {
                    $(element).show();
                    $('#' + seasonNo + '-cols').show();
                }
            });
        },
        selectEpisodesClicked() {
            // Selects all visible episode checkboxes
            [...document.querySelectorAll('.epCheck, .seasonCheck')].filter(isVisible).forEach(element => {
                element.checked = true;
            });
        },
        clearEpisodeSelectionClicked() {
            // Clears all visible episode checkboxes and the season selectors
            [...document.querySelectorAll('.epCheck, .seasonCheck')].filter(isVisible).forEach(element => {
                element.checked = false;
            });
        },
        toggleSpecials() {
            const config = {
                section: 'main',
                config: {
                    layout: {
                        show: {
                            specials: !this.displaySpecials
                        }
                    }
                }
            };
            this.$store.dispatch('setConfig', config).then(() => {
                window.location.reload();
            });
        },
        reverse(array) {
            return array ? array.slice().reverse() : [];
        },
        dedupeGenres(genres) {
            return genres ? [...new Set(genres.slice(0).map(genre => genre.replace('-', ' ')))] : [];
        },
        getCountryISO2ToISO3(country) {
            return getLanguage(country).iso639_2en;
        }
    },
    watch: {
        jumpToSeason(season) {
            // Don't jump until an option is selected
            if (season !== 'jump') {
                console.debug(`Jumping to ${season}`);

                scrollTo(season, 100, {
                    container: 'body',
                    easing: 'ease-in',
                    offset: -100
                });

                // Update URL hash
                location.hash = season;

                // Reset jump
                this.jumpToSeason = 'jump';
            }
        }
    }
};
</script>

<style scoped>
.summaryTable {
    overflow: hidden;
}

.summaryTable tr td {
    word-break: break-all;
}

.ver-spacer {
    width: 15px;
}

#show-specials-and-seasons {
    margin-bottom: 15px;
}

span.required {
    color: green;
}

span.preferred {
    color: blue;
}

span.undesired {
    color: orange;
}

span.ignored {
    color: red;
}

div#col-show-summary {
    display: table;
}

#col-show-summary img.show-image {
    max-width: 180px;
}

.show-poster-container {
    margin-right: 10px;
    display: table-cell;
    width: 180px;
}

.show-info-container {
    overflow: hidden;
    display: table-cell;
}

@media (min-width: 768px) {
    .display-specials,
    .display-seasons {
        top: -60px;
    }

    #show-specials-and-seasons {
        bottom: 5px;
        right: 15px;
        position: absolute;
    }
}

@media (max-width: 767px) {
    .show-poster-container {
        display: inline-block;
        width: 100%;
        margin: 0 auto;
        border-style: none;
    }

    .show-poster-container img {
        display: block;
        margin: 0 auto;
        max-width: 280px !important;
    }

    .show-info-container {
        display: block;
        padding-top: 5px;
        width: 100%;
    }
}

@media (max-width: 991px) and (min-width: 768px) {
    .show-poster-container {
        float: left;
        display: inline-block;
        width: 100%;
        border-style: none;
    }

    .show-info-container {
        display: block;
        width: 100%;
    }

    #col-show-summary img.show-image {
        max-width: 280px;
    }
}
</style>
