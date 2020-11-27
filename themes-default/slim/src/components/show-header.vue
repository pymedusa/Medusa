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
                        <app-link :href="`home/displayShow?indexername=${show.indexer}&seriesid=${show.id[show.indexer]}`" class="snatchTitle">{{ show.title }}</app-link>
                    </h1>
                </div>

                <!-- Episode specific information for snatch-selection -->
                <div v-if="type === 'snatch-selection'" id="show-specials-and-seasons" class="pull-right episode-info">
                    <span class="h2footer display-specials">
                        Manual search for: Season {{ season }}<template v-if="episode !== undefined && manualSearchType !== 'season'"> Episode {{ episode }}</template>
                    </span>
                    <span v-if="manualSearchType !== 'season' && episodeTitle">
                        {{episodeTitle}}
                    </span>
                </div>

                <!-- Display Specials on/off and season jump -->
                <div v-if="type !== 'snatch-selection' && seasons.length >= 1" id="show-specials-and-seasons" class="pull-right">
                    <span class="h2footer display-specials" v-if="seasons.includes(0)">
                        Display Specials: <a @click.prevent="toggleSpecials()" class="inner" style="cursor: pointer;">{{ displaySpecials ? 'Hide' : 'Show' }}</a>
                    </span>

                    <div class="h2footer display-seasons clear">
                        <span>
                            <select v-if="seasons.length >= 15" v-model="jumpToSeason" id="seasonJump" class="form-control input-sm" style="position: relative">
                                <option value="jump">Jump to Season</option>
                                <option v-for="seasonNumber in seasons" :key="`jumpToSeason-${seasonNumber}`" :value="seasonNumber">
                                    {{ seasonNumber === 0 ? 'Specials' : `Season ${seasonNumber}` }}
                                </option>
                            </select>
                            <template v-else-if="seasons.length >= 1">
                                Season:
                                <template v-for="(seasonNumber, index) in reverse(seasons)">
                                    <app-link :href="`#season-${seasonNumber}`" :key="`jumpToSeason-${seasonNumber}`" @click.native.prevent="jumpToSeason = seasonNumber">
                                        {{ seasonNumber === 0 ? 'Specials' : seasonNumber }}
                                    </app-link>
                                    <span v-if="index !== (seasons.length - 1)" :key="`separator-${index}`" class="separator">| </span>
                                </template>
                            </template>
                        </span>
                    </div>
                </div>
            </div> <!-- end show title -->
        </div> <!-- end row showtitle-->

        <div class="row" v-for="queueItem of activeShowQueueStatuses" :key="queueItem.action">
            <div class="alert alert-info">
                {{ queueItem.message }}
            </div>
        </div>

        <div id="summaryBackground" class="shadow shadow-background">
            <div class="row" id="row-show-summary">
                <div id="col-show-summary" class="col-md-12">
                    <div class="show-poster-container">
                        <div class="row">
                            <div class="image-flex-container col-md-12">
                                <asset default-src="images/poster.png" :show-slug="show.id.slug" type="posterThumb" cls="show-image shadow" :link="true" />
                            </div>
                        </div>
                    </div>

                    <div class="ver-spacer" />

                    <div class="show-info-container">
                        <div class="row">
                            <div class="pull-right col-lg-3 col-md-3 hidden-sm hidden-xs">
                                <asset default-src="images/banner.png" :show-slug="show.id.slug" type="banner" cls="show-banner pull-right shadow" :link="true" />
                            </div>
                            <div id="indexers" class="pull-left col-lg-9 col-md-9 col-sm-12 col-xs-12">
                                <span
                                    v-if="show.rating.imdb && show.rating.imdb.rating"
                                    class="imdbstars"
                                    :qtip-content="`${show.rating.imdb.rating} / 10 Stars<br> ${show.rating.imdb.votes} Votes`"
                                >
                                    <span :style="{ width: (Number(show.rating.imdb.rating) * 10) + '%' }" />
                                </span>
                                <template v-if="!show.id.imdb">
                                    <span v-if="show.year.start">({{ show.year.start }}) - {{ show.runtime }} minutes - </span>
                                </template>
                                <template v-else>
                                    <img v-for="country in show.countryCodes" :key="'flag-' + country" src="images/blank.png" :class="['country-flag', 'flag-' + country]" width="16" height="11" style="margin-left: 3px; vertical-align:middle;">
                                    <span v-if="show.imdbInfo.year">
                                        ({{ show.imdbInfo.year }}) -
                                    </span>
                                    <span>
                                        {{ show.imdbInfo.runtimes || show.runtime }} minutes
                                    </span>
                                    <app-link :href="`https://www.imdb.com/title/${show.id.imdb}`" :title="'https://www.imdb.com/title/' + show.id.imdb">
                                        <img alt="[imdb]" height="16" width="16" src="images/imdb.png" style="margin-top: -1px; vertical-align:middle;">
                                    </app-link>
                                </template>

                                <div id="indexer-wrapper">
                                    <img id="stored-by-indexer" src="images/star.png">
                                    <app-link v-if="showIndexerUrl && indexerConfig[show.indexer].icon" :href="showIndexerUrl" :title="showIndexerUrl">
                                        <img :alt="indexerConfig[show.indexer].name" height="16" width="16" :src="`images/${indexerConfig[show.indexer].icon}`" style="margin-top: -1px; vertical-align:middle;">
                                    </app-link>
                                </div>

                                <app-link v-if="show.id.trakt" :href="`https://trakt.tv/shows/${show.id.trakt}`" :title="`https://trakt.tv/shows/${show.id.trakt}`">
                                    <img alt="[trakt]" height="16" width="16" src="images/trakt.png">
                                </app-link>

                                <app-link v-if="show.xemNumbering && show.xemNumbering.length > 0" :href="`http://thexem.de/search?q=${show.title}`" :title="`http://thexem.de/search?q=${show.title}`">
                                    <img alt="[xem]" height="16" width="16" src="images/xem.png" style="margin-top: -1px; vertical-align:middle;">
                                </app-link>

                                <app-link v-if="show.id.tvdb" :href="`https://fanart.tv/series/${show.id.tvdb}`" :title="`https://fanart.tv/series/${show.id[show.indexer]}`">
                                    <img alt="[fanart.tv]" height="16" width="16" src="images/fanart.tv.png" class="fanart">
                                </app-link>

                            </div>
                            <div id="tags" class="pull-left col-lg-9 col-md-9 col-sm-12 col-xs-12">
                                <ul class="tags" v-if="show.genres">
                                    <app-link v-for="genre in dedupeGenres(show.genres)" :key="genre.toString()" :href="`https://trakt.tv/shows/popular/?genres=${genre.toLowerCase().replace(' ', '-')}`" :title="`View other popular ${genre} shows on trakt.tv`"><li>{{ genre }}</li></app-link>
                                </ul>
                                <ul class="tags" v-else>
                                    <app-link v-for="genre in showGenres" :key="genre.toString()" :href="`https://www.imdb.com/search/title?count=100&title_type=tv_series&genres=${genre.toLowerCase().replace(' ', '-')}`" :title="`View other popular ${genre} shows on IMDB`"><li>{{ genre }}</li></app-link>
                                </ul>
                            </div>
                        </div>

                        <div class="row">
                            <!-- Show Summary -->
                            <div ref="summary" v-if="configLoaded" id="summary" class="col-md-12">
                                <div class="row">
                                    <div id="show-summary" :class="{summaryFanArt: layout.fanartBackground}" class="col-lg-9 col-md-8 col-sm-8 col-xs-12">
                                        <table class="summaryTable pull-left">
                                            <tr v-if="show.plot">
                                                <td colspan="2" style="padding-bottom: 15px;">
                                                    <truncate action-class="btn-medusa" @toggle="$emit('reflow')" :length="250" clamp="show more" less="show less" :text="show.plot" />
                                                </td>
                                            </tr>

                                            <!-- Preset -->
                                            <tr v-if="getQualityPreset({ value: combinedQualities }) !== undefined">
                                                <td class="showLegend">Quality:</td>
                                                <td><quality-pill :quality="combinedQualities" /></td>
                                            </tr>

                                            <!-- Custom quality -->
                                            <template v-else>
                                                <tr v-if="combineQualities(show.config.qualities.allowed) > 0">
                                                    <td class="showLegend">Allowed Qualities:</td>
                                                    <td>
                                                        <template v-for="(curQuality, index) in show.config.qualities.allowed"><!--
                                                            -->{{ index > 0 ? ', ' : '' }}<!--
                                                            --><quality-pill :quality="curQuality" :key="`allowed-${curQuality}`" />
                                                        </template>
                                                    </td>
                                                </tr>

                                                <tr v-if="combineQualities(show.config.qualities.preferred) > 0">
                                                    <td class="showLegend">Preferred Qualities:</td>
                                                    <td>
                                                        <template v-for="(curQuality, index) in show.config.qualities.preferred"><!--
                                                            -->{{ index > 0 ? ', ' : '' }}<!--
                                                            --><quality-pill :quality="curQuality" :key="`preferred-${curQuality}`" />
                                                        </template>
                                                    </td>
                                                </tr>
                                            </template>

                                            <tr v-if="show.network && show.airs"><td class="showLegend">Originally Airs: </td><td>{{ show.airs }}<b v-if="!show.airsFormatValid" class="invalid-value"> (invalid time format)</b> on {{ show.network }}</td></tr>
                                            <tr v-else-if="show.network"><td class="showLegend">Originally Airs: </td><td>{{ show.network }}</td></tr>
                                            <tr v-else-if="show.airs"><td class="showLegend">Originally Airs: </td><td>{{ show.airs }}<b v-if="!show.airsFormatValid" class="invalid-value"> (invalid time format)</b></td></tr>
                                            <tr><td class="showLegend">Show Status: </td><td>{{ show.status }}</td></tr>
                                            <tr><td class="showLegend">Default EP Status: </td><td>{{ show.config.defaultEpisodeStatus }}</td></tr>
                                            <tr><td class="showLegend"><span :class="{'invalid-value': !show.config.locationValid}">Location: </span></td><td><span :class="{'invalid-value': !show.config.locationValid}">{{show.config.location}}</span>{{show.config.locationValid ? '' : ' (Missing)'}}</td></tr>

                                            <tr v-if="show.config.aliases.filter(alias => alias.season === -1).length > 0">
                                                <td class="showLegend" style="vertical-align: top;">Scene Name:</td>
                                                <td>{{show.config.aliases.filter(alias => alias.season === -1).map(alias => alias.title).join(', ')}}</td>
                                            </tr>

                                            <tr v-if="show.config.release.requiredWords.length + search.filters.required.length > 0">
                                                <td class="showLegend" style="vertical-align: top;">
                                                    <span :class="{required: type === 'snatch-selection'}">Required Words: </span>
                                                </td>
                                                <td>
                                                    <span v-if="show.config.release.requiredWords.length" class="break-word">
                                                        {{show.config.release.requiredWords.join(', ')}}
                                                    </span>
                                                    <span v-if="search.filters.required.length > 0" class="break-word global-filter">
                                                        <app-link href="config/search/#searchfilters">
                                                            <template v-if="show.config.release.requiredWords.length > 0">
                                                                <span v-if="show.config.release.requiredWordsExclude"> excluded from: </span>
                                                                <span v-else>+ </span>
                                                            </template>
                                                            {{search.filters.required.join(', ')}}
                                                        </app-link>
                                                    </span>
                                                </td>
                                            </tr>
                                            <tr v-if="show.config.release.ignoredWords.length + search.filters.ignored.length > 0">
                                                <td class="showLegend" style="vertical-align: top;">
                                                    <span :class="{ignored: type === 'snatch-selection'}">Ignored Words: </span>
                                                </td>
                                                <td>
                                                    <span v-if="show.config.release.ignoredWords.length" class="break-word">
                                                        {{show.config.release.ignoredWords.join(', ')}}
                                                    </span>
                                                    <span v-if="search.filters.ignored.length > 0" class="break-word global-filter">
                                                        <app-link href="config/search/#searchfilters">
                                                            <template v-if="show.config.release.ignoredWords.length > 0">
                                                                <span v-if="show.config.release.ignoredWordsExclude"> excluded from: </span>
                                                                <span v-else>+ </span>
                                                            </template>
                                                            {{search.filters.ignored.join(', ')}}
                                                        </app-link>
                                                    </span>
                                                </td>
                                            </tr>

                                            <tr v-if="search.filters.preferred.length > 0">
                                                <td class="showLegend" style="vertical-align: top;">
                                                    <span :class="{preferred: type === 'snatch-selection'}">Preferred Words: </span>
                                                </td>
                                                <td>
                                                    <app-link href="config/search/#searchfilters">
                                                        <span class="break-word">{{search.filters.preferred.join(', ')}}</span>
                                                    </app-link>
                                                </td>
                                            </tr>
                                            <tr v-if="search.filters.undesired.length > 0">
                                                <td class="showLegend" style="vertical-align: top;">
                                                    <span :class="{undesired: type === 'snatch-selection'}">Undesired Words: </span>
                                                </td>
                                                <td>
                                                    <app-link href="config/search/#searchfilters">
                                                        <span class="break-word">{{search.filters.undesired.join(', ')}}</span>
                                                    </app-link>
                                                </td>
                                            </tr>

                                            <tr v-if="show.config.release.whitelist && show.config.release.whitelist.length > 0">
                                                <td class="showLegend">Wanted Groups:</td>
                                                <td>{{show.config.release.whitelist.join(', ')}}</td>
                                            </tr>

                                            <tr v-if="show.config.release.blacklist && show.config.release.blacklist.length > 0">
                                                <td class="showLegend">Unwanted Groups:</td>
                                                <td>{{show.config.release.blacklist.join(', ')}}</td>
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
                                            <tr v-if="show.language"><td class="showLegend">Info Language:</td><td><img :src="'images/subtitles/flags/' + getCountryISO2ToISO3(show.language) + '.png'" width="16" height="11" :alt="show.language" :title="show.language" onError="this.onerror=null;this.src='images/flags/unknown.png';"></td></tr>
                                            <tr v-if="config.subtitles.enabled"><td class="showLegend">Subtitles: </td><td><state-switch :theme="layout.themeName" :state="show.config.subtitlesEnabled" @click="toggleConfigOption('subtitlesEnabled');" /></td></tr>
                                            <tr><td class="showLegend">Season Folders: </td><td><state-switch :theme="layout.themeName" :state="show.config.seasonFolders || config.namingForceFolders" /></td></tr>
                                            <tr><td class="showLegend">Paused: </td><td><state-switch :theme="layout.themeName" :state="show.config.paused" @click="toggleConfigOption('paused')" /></td></tr>
                                            <tr><td class="showLegend">Air-by-Date: </td><td><state-switch :theme="layout.themeName" :state="show.config.airByDate" @click="toggleConfigOption('airByDate')" /></td></tr>
                                            <tr><td class="showLegend">Sports: </td><td><state-switch :theme="layout.themeName" :state="show.config.sports" @click="toggleConfigOption('sports')" /></td></tr>
                                            <tr><td class="showLegend">Anime: </td><td><state-switch :theme="layout.themeName" :state="show.config.anime" @click="toggleConfigOption('anime')" /></td></tr>
                                            <tr><td class="showLegend">DVD Order: </td><td><state-switch :theme="layout.themeName" :state="show.config.dvdOrder" @click="toggleConfigOption('dvdOrder')" /></td></tr>
                                            <tr><td class="showLegend">Scene Numbering: </td><td><state-switch :theme="layout.themeName" :state="show.config.scene" @click="toggleConfigOption('scene')" /></td></tr>
                                        </table>
                                    </div> <!-- end of show-status -->
                                </div> <!-- end of show-satus row -->
                            </div> <!-- end of summary -->
                        </div> <!-- end of row -->
                    </div> <!-- show-info-container -->
                </div> <!-- end of col -->
            </div> <!-- end of row row-show-summary-->
        </div>

        <div id="episodes-controll-background" class="shadow shadow-background">
            <div v-if="show" id="row-show-episodes-controls" class="row">
                <div id="col-show-episodes-controls" class="col-md-12">
                    <div v-if="type === 'show'" class="row key"> <!-- Checkbox filter controls -->
                        <div ref="checkboxControls" class="col-lg-12" id="checkboxControls">
                            <div v-if="show.seasons" id="key-padding" class="pull-left top-5">
                                <label v-for="status of overviewStatus" :key="status.id" :for="status.id">
                                    <span :class="status.id">
                                        <input type="checkbox" :id="status.id" v-model="status.checked" @change="$emit('update-overview-status', overviewStatus)">
                                        {{status.name}}: <b>{{episodeSummary[status.name]}}</b>
                                    </span>
                                </label>
                            </div>
                            <div class="pull-lg-right top-5">

                                <select id="statusSelect" v-model="selectedStatus" class="form-control form-control-inline input-sm-custom input-sm-smallfont">
                                    <option :value="'Change status to:'">Change status to:</option>
                                    <option v-for="status in changeStatusOptions" :key="status.key" :value="status.value">
                                        {{ status.name }}
                                    </option>
                                </select>

                                <select id="qualitySelect" v-model="selectedQuality" class="form-control form-control-inline input-sm-custom input-sm-smallfont">
                                    <option :value="'Change quality to:'">Change quality to:</option>
                                    <option v-for="quality in qualities" :key="quality.key" :value="quality.value">
                                        {{ quality.name }}
                                    </option>
                                </select>
                                <input type="hidden" id="series-slug" :value="show.id.slug">
                                <input type="hidden" id="series-id" :value="show.id[show.indexer]">
                                <input type="hidden" id="indexer" :value="show.indexer">
                                <input class="btn-medusa" type="button" id="changeStatus" value="Go" @click="changeStatusClicked">
                            </div>
                        </div> <!-- checkboxControls -->
                    </div> <!-- end of row -->
                    <div v-else />
                </div> <!-- end of col -->
            </div> <!-- end of row -->
        </div> <!-- end of background -->
    </div>
</template>

<script>
import Truncate from 'vue-truncate-collapsed';
import { getLanguage } from 'country-language';
import { scrollTo } from 'vue-scrollto';
import { mapActions, mapState, mapGetters } from 'vuex';
import { api } from '../api';
import { combineQualities, humanFileSize } from '../utils/core';
import { attachImdbTooltip } from '../utils/jquery';
import { AppLink, Asset, QualityPill, StateSwitch } from './helpers';

/**
 * Return the first item of `values` that is not `null`, `undefined` or `NaN`.
 * @param {...any} values - Values to check.
 * @returns {any} - The first item that fits the criteria, `undefined` otherwise.
 */
const resolveToValue = (...values) => {
    return values.find(value => {
        return !Number.isNaN(value) && value !== null && value !== undefined;
    });
};

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
            jumpToSeason: 'jump',
            selectedStatus: 'Change status to:',
            selectedQuality: 'Change quality to:',
            overviewStatus: [
                {
                    id: 'wanted',
                    checked: true,
                    name: 'Wanted'
                },
                {
                    id: 'allowed',
                    checked: true,
                    name: 'Allowed'
                },
                {
                    id: 'preferred',
                    checked: true,
                    name: 'Preferred'
                },
                {
                    id: 'skipped',
                    checked: true,
                    name: 'Skipped'
                },
                {
                    id: 'snatched',
                    checked: true,
                    name: 'Snatched'
                }
            ]
        };
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            layout: state => state.config.layout,
            shows: state => state.shows.shows,
            indexers: state => state.config.indexers,
            indexerConfig: state => state.config.indexers.indexers,
            displaySpecials: state => state.config.layout.show.specials,
            qualities: state => state.config.consts.qualities.values,
            statuses: state => state.config.consts.statuses,
            search: state => state.config.search,
            configLoaded: state => state.config.layout.fanartBackground !== null
        }),
        ...mapGetters({
            show: 'getCurrentShow',
            getEpisode: 'getEpisode',
            getOverviewStatus: 'getOverviewStatus',
            getQualityPreset: 'getQualityPreset',
            getStatus: 'getStatus'
        }),
        indexer() {
            return this.showIndexer || this.$route.query.indexername;
        },
        id() {
            return this.showId || Number(this.$route.query.seriesid) || undefined;
        },
        season() {
            return resolveToValue(this.showSeason, Number(this.$route.query.season));
        },
        episode() {
            return resolveToValue(this.showEpisode, Number(this.$route.query.episode));
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
        episodeSummary() {
            const { getOverviewStatus, show } = this;
            const { seasons } = show;
            const summary = {
                Unaired: 0,
                Skipped: 0,
                Wanted: 0,
                Snatched: 0,
                Preferred: 0,
                Allowed: 0
            };
            seasons.forEach(season => {
                season.episodes.forEach(episode => {
                    summary[getOverviewStatus(episode.status, episode.quality, show.config.qualities)] += 1;
                });
            });
            return summary;
        },
        changeStatusOptions() {
            const { search, getStatus, statuses } = this;
            const { general } = search;

            if (statuses.length === 0) {
                return [];
            }

            // Get status objects, in this order
            const defaultOptions = ['wanted', 'skipped', 'ignored', 'downloaded', 'archived']
                .map(key => getStatus({ key }));

            if (general.failedDownloads.enabled) {
                defaultOptions.push(getStatus({ key: 'failed' }));
            }

            return defaultOptions;
        },
        combinedQualities() {
            const { allowed, preferred } = this.show.config.qualities;
            return combineQualities(allowed, preferred);
        },
        seasons() {
            const { show } = this;
            const { seasonCount } = show;
            if (!seasonCount) {
                return [];
            }
            // Only return an array with seasons (integers)
            return seasonCount.map(season => season.season);
        },
        episodeTitle() {
            const { getEpisode, show, season, episode } = this;
            if (!(show.id.slug && season && episode)) {
                return '';
            }

            const curEpisode = getEpisode({ showSlug: show.id.slug, season, episode });
            if (curEpisode) {
                return curEpisode.title;
            }

            return '';
        }
    },
    mounted() {
        ['load', 'resize'].map(event => {
            return window.addEventListener(event, () => {
                this.$nextTick(() => this.reflowLayout());
            });
        });
        this.$watch('show', function(slug) { // eslint-disable-line object-shorthand
            // Show has changed. Meaning we should reflow the layout.
            if (slug) {
                const { reflowLayout } = this;
                this.$nextTick(() => reflowLayout());
            }
        }, { deep: true });
    },
    methods: {
        ...mapActions([
            'setSpecials'
        ]),
        combineQualities,
        humanFileSize,
        changeStatusClicked() {
            const { changeStatusOptions, changeQualityOptions, selectedStatus, selectedQuality } = this;
            this.$emit('update', {
                newStatus: selectedStatus,
                newQuality: selectedQuality,
                statusOptions: changeStatusOptions,
                qualityOptions: changeQualityOptions
            });
        },
        toggleSpecials() {
            const { setSpecials } = this;
            setSpecials(!this.displaySpecials);
        },
        reverse(array) {
            return array ? array.slice().reverse() : [];
        },
        dedupeGenres(genres) {
            return genres ? [...new Set(genres.slice(0).map(genre => genre.replace('-', ' ')))] : [];
        },
        getCountryISO2ToISO3(country) {
            return getLanguage(country).iso639_2en;
        },
        toggleConfigOption(option) {
            const { show } = this;
            const { config } = show;
            this.show.config[option] = !this.show.config[option];
            const data = {
                config: { [option]: config[option] }
            };
            api.patch('series/' + show.id.slug, data).then(_ => {
                this.$snotify.success(
                    `${data.config[option] ? 'enabled' : 'disabled'} show option ${option}`,
                    'Saved',
                    { timeout: 5000 }
                );
            }).catch(error => {
                this.$snotify.error(
                    'Error while trying to save "' + show.title + '": ' + error.message || 'Unknown',
                    'Error'
                );
            });
        },
        reflowLayout() {
            attachImdbTooltip(); // eslint-disable-line no-undef
        }
    },
    watch: {
        jumpToSeason(season) {
            // Don't jump until an option is selected
            if (season !== 'jump') {
                // Calculate duration
                let duration = (this.seasons.length - season) * 50;
                duration = Math.max(500, Math.min(duration, 2000)); // Limit to (500ms <= duration <= 2000ms)

                // Calculate offset
                let offset = -50; // Navbar
                // Needs extra offset when the sub menu is "fixed".
                offset -= window.matchMedia('(min-width: 1281px)').matches ? 40 : 0;

                const name = `season-${season}`;
                console.debug(`Jumping to #${name} (${duration}ms)`);

                scrollTo(`[name="${name}"]`, duration, {
                    container: 'body',
                    easing: 'ease-in-out',
                    offset
                });

                // Update URL hash
                window.location.hash = name;

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
    word-break: break-word;
}

.ver-spacer {
    width: 15px;
}

#showtitle {
    float: none;
}

#show-specials-and-seasons {
    bottom: 5px;
    right: 15px;
    position: absolute;
}

.episode-info span {
    display: block;
}

span.required {
    color: green;
}

span.preferred {
    color: rgb(41, 87, 48);
}

span.undesired {
    color: orange;
}

span.ignored {
    color: red;
}

.shadow-background {
    padding: 10px;
}

#col-show-summary {
    display: table;
}

#col-show-summary >>> img.show-image {
    width: 180px;
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

.showLegend {
    padding-right: 6px;
    padding-bottom: 1px;
    width: 150px;
}

.invalid-value {
    color: rgb(255, 0, 0);
}

@media (min-width: 768px) {
    .display-specials,
    .display-seasons {
        top: -60px;
    }
}

@media (max-width: 767px) {
    .show-poster-container {
        display: inline-block;
        width: 100%;
        margin: 0 auto;
        border-style: none;
    }

    .show-poster-container >>> img {
        display: block;
        margin: 0 auto;
        max-width: 280px !important;
    }

    .show-info-container {
        display: block;
        padding-top: 5px;
        width: 100%;
    }

    #showtitle {
        margin-bottom: 40px;
    }

    #show-specials-and-seasons {
        bottom: -40px;
        left: 15px;
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

    #col-show-summary >>> img.show-image {
        width: 280px;
    }
}

.unaired {
    background-color: rgb(245, 241, 228);
}

.skipped {
    background-color: rgb(190, 222, 237);
}

.preferred {
    background-color: rgb(195, 227, 200);
}

.archived {
    background-color: rgb(195, 227, 200);
}

.allowed {
    background-color: rgb(255, 218, 138);
}

.wanted {
    background-color: rgb(255, 176, 176);
}

.snatched {
    background-color: rgb(235, 193, 234);
}

.downloaded {
    background-color: rgb(195, 227, 200);
}

.failed {
    background-color: rgb(255, 153, 153);
}

span.unaired {
    color: rgb(88, 75, 32);
}

span.skipped {
    color: rgb(29, 80, 104);
}

span.preffered {
    color: rgb(41, 87, 48);
}

span.allowed {
    color: rgb(118, 81, 0);
}

span.wanted {
    color: rgb(137, 0, 0);
}

span.snatched {
    color: rgb(101, 33, 100);
}

span.unaired b,
span.skipped b,
span.preferred b,
span.allowed b,
span.wanted b,
span.snatched b {
    color: rgb(0, 0, 0);
    font-weight: 800;
}

span.global-filter {
    font-style: italic;
}

.show-status {
    font-size: 11px;
    text-align: left;
    display: block;
}

#stored-by-indexer {
    position: absolute;
    bottom: -3px;
    right: -3px;
}

#indexer-wrapper {
    display: inline;
    position: relative;
}

</style>
