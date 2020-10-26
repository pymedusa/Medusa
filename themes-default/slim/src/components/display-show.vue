<template>
    <div class="display-show-template" :class="theme">
        <vue-snotify />
        <backstretch v-if="show.id.slug" :slug="show.id.slug" />
        <input type="hidden" id="series-id" value="">
        <input type="hidden" id="indexer-name" value="">
        <input type="hidden" id="series-slug" value="">

        <show-header type="show"
                     ref="show-header"
                     @reflow="reflowLayout"
                     :show-id="id"
                     :show-indexer="indexer"
                     @update="statusQualityUpdate"
                     @update-overview-status="filterByOverviewStatus = $event"
        />

        <div class="row" :class="{ fanartBackground: layout.fanartBackground }">
            <div class="col-md-12 top-15 displayShow horizontal-scroll">
                <!-- Display non-special episodes, paginate if enabled -->
                <vue-good-table v-if="show.seasons"
                                :columns="columns"
                                :rows="orderSeasons"
                                :groupOptions="{
                                    enabled: true,
                                    mode: 'span',
                                    customChildObject: 'episodes'
                                }"
                                :pagination-options="{
                                    enabled: layout.show.pagination.enable,
                                    perPage: paginationPerPage,
                                    perPageDropdown
                                }"
                                :search-options="{
                                    enabled: true,
                                    trigger: 'enter',
                                    skipDiacritics: false,
                                    placeholder: 'Search episodes',
                                }"
                                :sort-options="{
                                    enabled: true,
                                    initialSortBy: getSortBy('episode', 'desc')
                                }"
                                :selectOptions="{
                                    enabled: true,
                                    selectOnCheckboxOnly: true, // only select when checkbox is clicked instead of the row
                                    selectionInfoClass: 'select-info',
                                    selectionText: 'episodes selected',
                                    clearSelectionText: 'clear',
                                    selectAllByGroup: true
                                }"
                                :row-style-class="rowStyleClassFn"
                                :column-filter-options="{
                                    enabled: true
                                }"
                                ref="table-seasons"
                                @on-selected-rows-change="selectedEpisodes=$event.selectedRows"
                                @on-per-page-change="updatePaginationPerPage($event.currentPerPage)"
                                @on-page-change="onPageChange">

                    <template slot="table-header-row" slot-scope="props">
                        <h3 class="season-header toggle collapse"><app-link :name="'season-'+ props.row.season" />
                            {{ props.row.season > 0 ? 'Season ' + props.row.season : 'Specials' }}
                            <!-- Only show the search manual season search, when any of the episodes in it is not unaired -->
                            <app-link v-if="anyEpisodeNotUnaired(props.row)" class="epManualSearch" :href="`home/snatchSelection?indexername=${show.indexer}&seriesid=${show.id[show.indexer]}&amp;season=${props.row.season}&amp;episode=1&amp;manual_search_type=season`">
                                <img v-if="config" data-ep-manual-search src="images/manualsearch-white.png" width="16" height="16" alt="search" title="Manual Search">
                            </app-link>
                            <div class="season-scene-exception" :data-season="props.row.season > 0 ? props.row.season : 'Specials'" />
                            <img v-bind="getSeasonExceptions(props.row.season)">
                        </h3>
                    </template>

                    <template slot="table-footer-row" slot-scope="{headerRow}">
                        <tr colspan="9999" :id="`season-${headerRow.season}-footer`" class="seasoncols border-bottom shadow">
                            <th class="col-footer" colspan="15" align="left">Season contains {{headerRow.episodes.length}} episodes with total filesize: {{addFileSize(headerRow)}}</th>
                        </tr>
                        <tr class="spacer" />
                    </template>

                    <template slot="table-row" slot-scope="props">
                        <span v-if="props.column.field == 'content.hasNfo'">
                            <img :src="'images/' + (props.row.content.hasNfo ? 'nfo.gif' : 'nfo-no.gif')" :alt="(props.row.content.hasNfo ? 'Y' : 'N')" width="23" height="11">
                        </span>
                        <span v-else-if="props.column.field == 'content.hasTbn'">
                            <img :src="'images/' + (props.row.content.hasTbn ? 'tbn.gif' : 'tbn-no.gif')" :alt="(props.row.content.hasTbn ? 'Y' : 'N')" width="23" height="11">
                        </span>

                        <span v-else-if="props.column.label == 'Episode'">
                            <span :title="props.row.file.location !== '' ? props.row.file.location : ''" :class="{addQTip: props.row.file.location !== ''}">{{props.row.episode}}</span>
                        </span>

                        <span v-else-if="props.column.label == 'Scene'" class="align-center">
                            <input type="text" :placeholder="`${props.formattedRow[props.column.field].season}x${props.formattedRow[props.column.field].episode}`" size="6" maxlength="8"
                                   class="sceneSeasonXEpisode form-control input-scene addQTip" :data-for-season="props.row.season" :data-for-episode="props.row.episode"
                                   :id="`sceneSeasonXEpisode_${show.id[show.indexer]}_${props.row.season}_${props.row.episode}`"
                                   title="Change this value if scene numbering differs from the indexer episode numbering. Generally used for non-anime shows."
                                   :value="props.formattedRow[props.column.field].season + 'x' + props.formattedRow[props.column.field].episode"
                                   style="padding: 0; text-align: center; max-width: 60px;">
                        </span>

                        <span v-else-if="props.column.label == 'Scene Abs. #'" class="align-center">
                            <input type="text" :placeholder="props.formattedRow[props.column.field]" size="6" maxlength="8"
                                   class="sceneAbsolute form-control input-scene addQTip" :data-for-absolute="props.formattedRow[props.column.field] || 0"
                                   :id="`sceneSeasonXEpisode_${show.id[show.indexer]}${props.formattedRow[props.column.field]}`"
                                   title="Change this value if scene absolute numbering differs from the indexer absolute numbering. Generally used for anime shows."
                                   :value="props.formattedRow[props.column.field] ? props.formattedRow[props.column.field] : ''"
                                   style="padding: 0; text-align: center; max-width: 60px;">
                        </span>

                        <span v-else-if="props.column.label == 'Title'">
                            <plot-info v-if="props.row.description !== ''" :description="props.row.description" :show-slug="show.id.slug" :season="props.row.season" :episode="props.row.episode" />
                            {{props.row.title}}
                        </span>

                        <span v-else-if="props.column.label == 'File'">
                            <span :title="props.row.file.location" class="addQTip">{{props.row.file.name}}</span>
                        </span>

                        <span v-else-if="props.column.label == 'Download'">
                            <app-link v-if="config.downloadUrl && props.row.file.location && ['Downloaded', 'Archived'].includes(props.row.status)" :href="config.downloadUrl + props.row.file.location">Download</app-link>
                        </span>

                        <span v-else-if="props.column.label == 'Subtitles'" class="align-center">
                            <div class="subtitles" v-if="['Archived', 'Downloaded', 'Ignored', 'Skipped'].includes(props.row.status)">
                                <div v-for="flag in props.row.subtitles" :key="flag">
                                    <img v-if="flag !== 'und'" :src="`images/subtitles/flags/${flag}.png`" width="16" height="11" :alt="flag" onError="this.onerror=null;this.src='images/flags/unknown.png';" @click="searchSubtitle($event, props.row, flag)">
                                    <img v-else :src="`images/subtitles/flags/${flag}.png`" class="subtitle-flag" width="16" height="11" :alt="flag" onError="this.onerror=null;this.src='images/flags/unknown.png';">
                                </div>
                            </div>
                        </span>

                        <span v-else-if="props.column.label == 'Status'">
                            <div class="pull-left">
                                {{props.row.status}}
                                <quality-pill v-if="props.row.quality !== 0" :quality="props.row.quality" />
                                <img v-if="props.row.status !== 'Unaired'"
                                     :title="props.row.watched ? 'This episode has been flagged as watched' : ''"
                                     class="addQTip" :src="`images/${props.row.watched ? '' : 'not'}watched.png`"
                                     width="16" height="16" style="margin-left: 5px" @click="updateEpisodeWatched(props.row, !props.row.watched);"
                                >
                            </div>
                        </span>

                        <span v-else-if="props.column.field == 'search'">
                            <div class="full-width">
                                <img class="epForcedSearch" :id="`${show.indexer}x${show.id[show.indexer]}x${props.row.season}x${props.row.episode}`"
                                     :name="`${show.indexer}x${show.id[show.indexer]}x${props.row.season}x${props.row.episode}`"
                                     :ref="`search-${props.row.slug}`" src="images/search16.png" height="16"
                                     :alt="retryDownload(props.row) ? 'retry' : 'search'"
                                     :title="retryDownload(props.row) ? 'Retry Download' : 'Forced Seach'"
                                     @click="queueSearch(props.row)"
                                >
                                <app-link class="epManualSearch" :id="`${show.indexer}x${show.id[show.indexer]}x${props.row.season}x${props.row.episode}`"
                                          :name="`${show.indexer}x${show.id[show.indexer]}x${props.row.season}x${props.row.episode}`"
                                          :href="`home/snatchSelection?indexername=${show.indexer}&seriesid=${show.id[show.indexer]}&season=${props.row.season}&episode=${props.row.episode}`"
                                >
                                    <img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search">
                                </app-link>
                                <img src="images/closed_captioning.png" height="16" alt="search subtitles" title="Search Subtitles" @click="searchSubtitle($event, props.row)">
                            </div>
                            <div class="mobile">
                                <select name="search-select" class="form-control input-sm mobile-select" @change="mobileSelectSearch($event, props.row)">
                                    <option disabled selected value="search action">search action</option>
                                    <option value="forced">{{retryDownload(props.row) ? 'retry' : 'search'}}</option>
                                    <option value="manual">manual</option>
                                    <option value="subtitle">subtitle</option>
                                </select>
                            </div>
                        </span>

                        <span v-else>
                            {{props.formattedRow[props.column.field]}}
                        </span>
                    </template>

                    <template slot="table-column" slot-scope="props">
                        <span v-if="props.column.label =='Abs. #'">
                            <span title="Absolute episode number" class="addQTip">{{props.column.label}}</span>
                        </span>
                        <span v-else-if="props.column.label =='Scene Abs. #'">
                            <span title="Scene Absolute episode number" class="addQTip">{{props.column.label}}</span>
                        </span>
                        <span v-else>
                            {{props.column.label}}
                        </span>
                    </template>

                </vue-good-table>

                <!-- Display special episodes -->
                <vue-good-table v-if="layout.show.specials && specials && specials.length > 0"
                                :columns="columns"
                                :rows="specials"
                                :groupOptions="{
                                    enabled: true,
                                    mode: 'span',
                                    customChildObject: 'episodes'
                                }"
                                :pagination-options="{
                                    enabled: false
                                }"
                                :search-options="{
                                    enabled: true,
                                    trigger: 'enter',
                                    skipDiacritics: false,
                                    placeholder: 'Search specials',
                                }"
                                :sort-options="{
                                    enabled: true,
                                    initialSortBy: getSortBy('episode', 'desc')
                                }"
                                :selectOptions="{
                                    enabled: true,
                                    selectOnCheckboxOnly: true, // only select when checkbox is clicked instead of the row
                                    selectionInfoClass: 'select-info',
                                    selectionText: 'episodes selected',
                                    clearSelectionText: 'clear',
                                    selectAllByGroup: true
                                }"
                                :row-style-class="rowStyleClassFn"
                                :column-filter-options="{
                                    enabled: false
                                }"
                                ref="table-specials"
                                @on-selected-rows-change="selectedEpisodes=$event.selectedRows">

                    <template slot="table-header-row" slot-scope="props">
                        <h3 class="season-header toggle collapse"><app-link :name="'season-'+ props.row.season" />
                            {{ props.row.season > 0 ? 'Season ' + props.row.season : 'Specials' }}
                            <!-- Only show the search manual season search, when any of the episodes in it is not unaired -->
                            <app-link v-if="anyEpisodeNotUnaired(props.row)" class="epManualSearch" :href="`home/snatchSelection?indexername=${show.indexer}&seriesid=${show.id[show.indexer]}&amp;season=${props.row.season}&amp;episode=1&amp;manual_search_type=season`">
                                <img v-if="config" data-ep-manual-search src="images/manualsearch-white.png" width="16" height="16" alt="search" title="Manual Search">
                            </app-link>
                            <div class="season-scene-exception" :data-season="props.row.season > 0 ? props.row.season : 'Specials'" />
                            <img v-bind="getSeasonExceptions(props.row.season)">
                        </h3>
                    </template>

                    <template slot="table-footer-row" slot-scope="{headerRow}">
                        <tr colspan="9999" :id="`season-${headerRow.season}-footer`" class="seasoncols border-bottom shadow">
                            <th class="col-footer" colspan="15" align="left">Season contains {{headerRow.episodes.length}} episodes with total filesize: {{addFileSize(headerRow)}}</th>
                        </tr>
                        <tr class="spacer" />
                    </template>

                    <template slot="table-row" slot-scope="props">
                        <span v-if="props.column.field == 'content.hasNfo'">
                            <img :src="'images/' + (props.row.content.hasNfo ? 'nfo.gif' : 'nfo-no.gif')" :alt="(props.row.content.hasNfo ? 'Y' : 'N')" width="23" height="11">
                        </span>
                        <span v-else-if="props.column.field == 'content.hasTbn'">
                            <img :src="'images/' + (props.row.content.hasTbn ? 'tbn.gif' : 'tbn-no.gif')" :alt="(props.row.content.hasTbn ? 'Y' : 'N')" width="23" height="11">
                        </span>

                        <span v-else-if="props.column.label == 'Episode'">
                            <span :title="props.row.file.location !== '' ? props.row.file.location : ''" :class="{addQTip: props.row.file.location !== ''}">{{props.row.episode}}</span>
                        </span>

                        <span v-else-if="props.column.label == 'Scene'" class="align-center">
                            <input type="text" :placeholder="`${props.formattedRow[props.column.field].season}x${props.formattedRow[props.column.field].episode}`" size="6" maxlength="8"
                                   class="sceneSeasonXEpisode form-control input-scene addQTip" :data-for-season="props.row.season" :data-for-episode="props.row.episode"
                                   :id="`sceneSeasonXEpisode_${show.id[show.indexer]}_${props.row.season}_${props.row.episode}`"
                                   title="Change this value if scene numbering differs from the indexer episode numbering. Generally used for non-anime shows."
                                   :value="props.formattedRow[props.column.field].season + 'x' + props.formattedRow[props.column.field].episode"
                                   style="padding: 0; text-align: center; max-width: 60px;">
                        </span>

                        <span v-else-if="props.column.label == 'Scene Abs. #'" class="align-center">
                            <input type="text" :placeholder="props.formattedRow[props.column.field]" size="6" maxlength="8"
                                   class="sceneAbsolute form-control input-scene addQTip" :data-for-absolute="props.formattedRow[props.column.field] || 0"
                                   :id="`sceneSeasonXEpisode_${show.id[show.indexer]}${props.formattedRow[props.column.field]}`"
                                   title="Change this value if scene absolute numbering differs from the indexer absolute numbering. Generally used for anime shows."
                                   :value="props.formattedRow[props.column.field] ? props.formattedRow[props.column.field] : ''"
                                   style="padding: 0; text-align: center; max-width: 60px;">
                        </span>

                        <span v-else-if="props.column.label == 'Title'">
                            <plot-info v-if="props.row.description !== ''" :description="props.row.description" :show-slug="show.id.slug" :season="props.row.season" :episode="props.row.episode" />
                            {{props.row.title}}
                        </span>

                        <span v-else-if="props.column.label == 'File'">
                            <span :title="props.row.file.location" class="addQTip">{{props.row.file.name}}</span>
                        </span>

                        <span v-else-if="props.column.label == 'Download'">
                            <app-link v-if="config.downloadUrl && props.row.file.location && ['Downloaded', 'Archived'].includes(props.row.status)" :href="config.downloadUrl + props.row.file.location">Download</app-link>
                        </span>

                        <span v-else-if="props.column.label == 'Subtitles'" class="align-center">
                            <div class="subtitles" v-if="['Archived', 'Downloaded', 'Ignored', 'Skipped'].includes(props.row.status)">
                                <div v-for="flag in props.row.subtitles" :key="flag">
                                    <img v-if="flag !== 'und'" :src="`images/subtitles/flags/${flag}.png`" width="16" height="11" alt="{flag}" onError="this.onerror=null;this.src='images/flags/unknown.png';" @click="searchSubtitle($event, props.row, flag)">
                                    <img v-else :src="`images/subtitles/flags/${flag}.png`" class="subtitle-flag" width="16" height="11" alt="flag" onError="this.onerror=null;this.src='images/flags/unknown.png';">
                                </div>
                            </div>
                        </span>

                        <span v-else-if="props.column.label == 'Status'" class="align-center">
                            <div class="pull-left">
                                {{props.row.status}}
                                <quality-pill v-if="props.row.quality !== 0" :quality="props.row.quality" class="quality-margins" />
                                <img :title="props.row.watched ? 'This episode has been flagged as watched' : ''" class="addQTip" v-if="props.row.status !== 'Unaired'" :src="`images/${props.row.watched ? '' : 'not'}watched.png`" width="16" @click="updateEpisodeWatched(props.row, !props.row.watched);">
                            </div>
                        </span>

                        <span v-else-if="props.column.field == 'search'">
                            <div class="full-width">
                                <img class="epForcedSearch" :id="`${show.indexer}x${show.id[show.indexer]}x${props.row.season}x${props.row.episode}`"
                                     :name="`${show.indexer}x${show.id[show.indexer]}x${props.row.season}x${props.row.episode}`"
                                     :ref="`search-${props.row.slug}`" src="images/search16.png" height="16"
                                     :alt="retryDownload(props.row) ? 'retry' : 'search'"
                                     :title="retryDownload(props.row) ? 'Retry Download' : 'Forced Seach'"
                                     @click="queueSearch(props.row)"
                                >
                                <app-link class="epManualSearch" :id="`${show.indexer}x${show.id[show.indexer]}x${props.row.season}x${props.row.episode}`"
                                          :name="`${show.indexer}x${show.id[show.indexer]}x${props.row.season}x${props.row.episode}`"
                                          :href="`home/snatchSelection?indexername=${show.indexer}&seriesid=${show.id[show.indexer]}&season=${props.row.season}&episode=${props.row.episode}`"
                                >
                                    <img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search">
                                </app-link>
                                <img src="images/closed_captioning.png" height="16" alt="search subtitles" title="Search Subtitles" @click="searchSubtitle($event, props.row)">
                            </div>
                            <div class="mobile">
                                <select name="search-select" class="form-control input-sm mobile-select" @change="mobileSelectSearch($event, props.row)">
                                    <option disabled selected value="search action">search action</option>
                                    <option value="forced">{{retryDownload(props.row) ? 'retry' : 'search'}}</option>
                                    <option value="manual">manual</option>
                                    <option value="subtitle">subtitle</option>
                                </select>
                            </div>
                        </span>

                        <span v-else>
                            {{props.formattedRow[props.column.field]}}
                        </span>
                    </template>

                    <template slot="table-column" slot-scope="props">
                        <span v-if="props.column.label =='Abs. #'">
                            <span title="Absolute episode number" class="addQTip">{{props.column.label}}</span>
                        </span>
                        <span v-else-if="props.column.label =='Scene Abs. #'">
                            <span title="Scene Absolute episode number" class="addQTip">{{props.column.label}}</span>
                        </span>
                        <span v-else>
                            {{props.column.label}}
                        </span>
                    </template>

                </vue-good-table>
            </div>
        </div>

        <!-- eslint-disable @sharkykh/vue-extra/component-not-registered -->
        <modal name="query-start-backlog-search" @before-open="beforeBacklogSearchModalClose" :height="'auto'" :width="'80%'">
            <transition name="modal">
                <div class="modal-mask">
                    <div class="modal-wrapper">
                        <div class="modal-content">
                            <div class="modal-header">
                                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                                <h4 class="modal-title">Start search?</h4>
                            </div>
                            <div class="modal-body">
                                <p>Some episodes have been changed to 'Wanted'. Do you want to trigger a backlog search for these {{backlogSearchEpisodes.length}} episode(s)</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn-medusa btn-danger" data-dismiss="modal" @click="$modal.hide('query-start-backlog-search')">No</button>
                                <button type="button" class="btn-medusa btn-success" data-dismiss="modal" @click="search(backlogSearchEpisodes, 'backlog'); $modal.hide('query-start-backlog-search')">Yes</button>
                            </div>
                        </div>
                    </div>
                </div>
            </transition>
        </modal>

        <modal name="query-mark-failed-and-search" @before-open="beforeFailedSearchModalClose" :height="'auto'" :width="'80%'">
            <transition name="modal">
                <div class="modal-mask">
                    <div class="modal-wrapper">
                        <div class="modal-content">
                            <div class="modal-header">
                                Mark episode as failed and search?
                            </div>

                            <div class="modal-body">
                                <p>Starting to search for the episode</p>
                                <p v-if="failedSearchEpisode">Would you also like to mark episode {{failedSearchEpisode.slug}} as "failed"? This will make sure the episode cannot be downloaded again</p>
                            </div>

                            <div class="modal-footer">
                                <button type="button" class="btn-medusa btn-danger" data-dismiss="modal" @click="search([failedSearchEpisode], 'backlog'); $modal.hide('query-mark-failed-and-search')">No</button>
                                <button type="button" class="btn-medusa btn-success" data-dismiss="modal" @click="search([failedSearchEpisode], 'failed'); $modal.hide('query-mark-failed-and-search')">Yes</button>
                                <button type="button" class="btn-medusa btn-danger" data-dismiss="modal" @click="$modal.hide('query-mark-failed-and-search')">Cancel</button>
                            </div>
                        </div>
                    </div>
                </div>
            </transition>
        </modal>
        <!-- eslint-enable -->
    </div>
</template>

<script>
import debounce from 'lodash/debounce';
import { mapState, mapGetters, mapActions } from 'vuex';
import { AppLink, PlotInfo } from './helpers';
import { humanFileSize } from '../utils/core';
import { manageCookieMixin } from '../mixins/manage-cookie';
import { addQTip, updateSearchIcons } from '../utils/jquery';
import { VueGoodTable } from 'vue-good-table';
import Backstretch from './backstretch.vue';
import ShowHeader from './show-header.vue';
import SubtitleSearch from './subtitle-search.vue';
import QualityPill from './helpers/quality-pill.vue';

export default {
    name: 'show',
    components: {
        AppLink,
        Backstretch,
        PlotInfo,
        QualityPill,
        ShowHeader,
        VueGoodTable
    },
    mixins: [
        manageCookieMixin('displayShow')
    ],
    metaInfo() {
        if (!this.show || !this.show.title) {
            return {
                title: 'Medusa'
            };
        }

        const { title } = this.show;
        return {
            title,
            titleTemplate: '%s | Medusa'
        };
    },
    props: {
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
        }
    },
    data() {
        const { getCookie } = this;
        const perPageDropdown = [25, 50, 100, 250, 500];
        const getPaginationPerPage = () => {
            const rows = getCookie('pagination-perPage');
            if (!rows) {
                return 50;
            }

            if (!perPageDropdown.includes(rows)) {
                return 500;
            }
            return rows;
        };
        return {
            invertTable: true,
            isMobile: false,
            subtitleSearchComponents: [],
            columns: [{
                label: 'NFO',
                field: 'content.hasNfo',
                type: 'boolean',
                sortable: false,
                hidden: getCookie('NFO')
            }, {
                label: 'TBN',
                field: 'content.hasTbn',
                type: 'boolean',
                sortable: false,
                hidden: getCookie('TBN')
            }, {
                label: 'Episode',
                field: 'episode',
                type: 'number',
                hidden: getCookie('Episode')
            }, {
                label: 'Abs. #',
                field: 'absoluteNumber',
                type: 'number',
                hidden: getCookie('Abs. #')
            }, {
                label: 'Scene',
                field: row => {
                    const { getSceneNumbering } = this;
                    return getSceneNumbering(row);
                },
                sortable: false,
                hidden: getCookie('Scene')
            }, {
                label: 'Scene Abs. #',
                field: row => {
                    const { getSceneAbsoluteNumbering } = this;
                    return getSceneAbsoluteNumbering(row);
                },
                type: 'number',
                /**
                 * Vue-good-table sort overwrite function.
                 * @param {Object} x - row1 value for column.
                 * @param {object} y - row2 value for column.
                 * @returns {Boolean} - if we want to display this row before the next
                 */
                sortFn(x, y) {
                    return (x < y ? -1 : (x > y ? 1 : 0));
                },
                hidden: getCookie('Scene Abs. #')
            }, {
                label: 'Title',
                field: 'title',
                hidden: getCookie('Title')
            }, {
                label: 'File',
                field: 'file.location',
                hidden: getCookie('File')
            }, {
                label: 'Size',
                field: 'file.size',
                type: 'number',
                formatFn: humanFileSize,
                hidden: getCookie('Size')
            }, {
                // For now i'm using a custom function the parse it. As the type: date, isn't working for us.
                // But the goal is to have this user formatted (as configured in backend)
                label: 'Air date',
                field: this.parseDateFn,
                tdClass: 'align-center',
                sortable: false,
                hidden: getCookie('Air date')
            }, {
                label: 'Download',
                field: 'download',
                sortable: false,
                hidden: getCookie('Download')
            }, {
                label: 'Subtitles',
                field: 'subtitles',
                sortable: false,
                hidden: getCookie('Subtitles')
            }, {
                label: 'Status',
                field: 'status',
                hidden: getCookie('Status')
            }, {
                label: 'Search',
                field: 'search',
                sortable: false,
                hidden: getCookie('Search')
            }],
            perPageDropdown,
            paginationPerPage: getPaginationPerPage(),
            selectedEpisodes: [],
            // We need to keep track of which episode where trying to search, for the vue-modal
            failedSearchEpisode: null,
            backlogSearchEpisodes: [],
            filterByOverviewStatus: false,
            selectedSearch: 'search action'
        };
    },
    computed: {
        ...mapState({
            shows: state => state.shows.shows,
            config: state => state.config.general,
            configLoaded: state => state.config.layout.fanartBackground !== null,
            layout: state => state.config.layout,
            stateSearch: state => state.config.search
        }),
        ...mapGetters({
            show: 'getCurrentShow',
            getOverviewStatus: 'getOverviewStatus',
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        indexer() {
            return this.showIndexer || this.$route.query.indexername;
        },
        id() {
            return this.showId || Number(this.$route.query.seriesid) || undefined;
        },
        theme() {
            const { layout } = this;
            const { themeName } = layout;
            return themeName || 'light';
        },
        orderSeasons() {
            const { filterByOverviewStatus, invertTable, show } = this;

            if (!show.seasons) {
                return [];
            }

            let sortedSeasons = show.seasons.sort((a, b) => a.season - b.season).filter(season => season.season !== 0);

            // Use the filterOverviewStatus to filter the data based on what's checked in the show-header.
            if (filterByOverviewStatus && filterByOverviewStatus.filter(status => status.checked).length < filterByOverviewStatus.length) {
                const filteredSortedSeasons = [];
                for (const season of sortedSeasons) {
                    const { episodes, ...res } = season;
                    const filteredEpisodes = episodes.filter(episode => {
                        const episodeOverviewStatus = this.getOverviewStatus(episode.status, episode.quality, show.config.qualities);
                        const filteredStatus = filterByOverviewStatus.find(overviewStatus => overviewStatus.name === episodeOverviewStatus);
                        return !filteredStatus || filteredStatus.checked;
                    });
                    filteredSortedSeasons.push(Object.assign({
                        episodes: filteredEpisodes
                    }, res));
                }
                sortedSeasons = filteredSortedSeasons;
            }

            if (invertTable) {
                return sortedSeasons.reverse();
            }

            return sortedSeasons;
        },
        specials() {
            const { show } = this;
            if (!show.seasons) {
                return [];
            }
            return show.seasons.filter(season => season.season === 0);
        }
    },

    mounted() {
        const {
            setEpisodeSceneNumbering,
            setAbsoluteSceneNumbering,
            setInputValidInvalid
        } = this;

        this.loadShow();

        ['load', 'resize'].map(event => {
            return window.addEventListener(event, () => {
                this.reflowLayout();
            });
        });

        $(document.body).on('click', '.seasonCheck', event => {
            const seasCheck = event.currentTarget;
            const seasNo = $(seasCheck).attr('id');

            $('#collapseSeason-' + seasNo).collapse('show');
            const seasonIdentifier = 's' + seasNo;
            $('.epCheck:visible').each((index, element) => {
                const epParts = $(element).attr('id').split('e');
                if (epParts[0] === seasonIdentifier) {
                    element.checked = seasCheck.checked;
                }
            });
        });

        $(document.body).on('change', '.sceneSeasonXEpisode', event => {
            const target = event.currentTarget;
            // Strip non-numeric characters
            const value = $(target).val();
            $(target).val(value.replace(/[^\dXx]*/g, ''));
            const forSeason = $(target).attr('data-for-season');
            const forEpisode = $(target).attr('data-for-episode');

            // If empty reset the field
            if (value === '') {
                setEpisodeSceneNumbering(forSeason, forEpisode, null, null);
                return;
            }

            const m = $(target).val().match(/^(\d+)x(\d+)$/i);
            const onlyEpisode = $(target).val().match(/^(\d+)$/i);
            let sceneSeason = null;
            let sceneEpisode = null;
            let isValid = false;
            if (m) {
                sceneSeason = m[1];
                sceneEpisode = m[2];
                isValid = setInputValidInvalid(true, $(target));
            } else if (onlyEpisode) {
                // For example when '5' is filled in instead of '1x5', asume it's the first season
                sceneSeason = forSeason;
                sceneEpisode = onlyEpisode[1];
                isValid = setInputValidInvalid(true, $(target));
            } else {
                isValid = setInputValidInvalid(false, $(target));
            }

            if (isValid) {
                setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode);
            }
        });

        $(document.body).on('change', '.sceneAbsolute', event => {
            const target = event.currentTarget;
            // Strip non-numeric characters
            $(target).val($(target).val().replace(/[^\dXx]*/g, ''));
            const forAbsolute = $(target).attr('data-for-absolute');

            const m = $(target).val().match(/^(\d{1,3})$/i);
            let sceneAbsolute = null;
            if (m) {
                sceneAbsolute = m[1];
            }

            setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute);
        });
    },
    methods: {
        humanFileSize,
        ...mapActions({
            getShow: 'getShow', // Map `this.getShow()` to `this.$store.dispatch('getShow')`
            getEpisodes: 'getEpisodes',
            setCurrentShow: 'setCurrentShow',
            setRecentShow: 'setRecentShow'
        }),
        async loadShow() {
            const { setCurrentShow, id, indexer, initializeEpisodes, getShow } = this;
            // We need detailed info for the xem / scene exceptions, so let's get it.
            await getShow({ id, indexer, detailed: true });

            // Let's tell the store which show we currently want as current.
            // Run this after getShow(), as it will trigger the initializeEpisodes() method.
            setCurrentShow({
                indexer,
                id
            });

            // Load all episodes
            initializeEpisodes();
        },
        statusQualityUpdate(event) {
            const { selectedEpisodes, setStatus, setQuality } = this;

            if (event.newQuality !== null && event.newQuality !== 'Change quality to:') {
                setQuality(event.newQuality, selectedEpisodes);
            }

            if (event.newStatus !== null && event.newStatus !== 'Change status to:') {
                setStatus(event.newStatus, selectedEpisodes);
            }
        },
        setQuality(quality, episodes) {
            const { id, indexer, getEpisodes, show } = this;
            const patchData = {};

            episodes.forEach(episode => {
                patchData[episode.slug] = { quality: Number.parseInt(quality, 10) };
            });

            api.patch('series/' + show.id.slug + '/episodes', patchData) // eslint-disable-line no-undef
                .then(_ => {
                    console.info(`patched show ${show.id.slug} with quality ${quality}`);
                    [...new Set(episodes.map(episode => episode.season))].forEach(season => {
                        getEpisodes({ id, indexer, season });
                    });
                }).catch(error => {
                    console.error(String(error));
                });
        },
        setStatus(status, episodes) {
            const { id, indexer, getEpisodes, show } = this;
            const patchData = {};

            episodes.forEach(episode => {
                patchData[episode.slug] = { status };
            });

            api.patch('series/' + show.id.slug + '/episodes', patchData) // eslint-disable-line no-undef
                .then(_ => {
                    console.info(`patched show ${show.id.slug} with status ${status}`);
                    [...new Set(episodes.map(episode => episode.season))].forEach(season => {
                        getEpisodes({ id, indexer, season });
                    });
                }).catch(error => {
                    console.error(String(error));
                });

            if (status === 3) {
                this.$modal.show('query-start-backlog-search', { episodes });
            }
        },
        parseDateFn(row) {
            const { fuzzyParseDateTime } = this;
            return fuzzyParseDateTime(row.airDate);
        },
        rowStyleClassFn(row) {
            const { getOverviewStatus, show } = this;
            if (Object.keys(row).includes('vgt_header_id')) {
                return;
            }
            const overview = getOverviewStatus(row.status, row.quality, show.config.qualities).toLowerCase().trim();
            return overview;
        },
        /**
         * Add (reduce) the total episodes filesize.
         * @param {object} headerRow header row object.
         * @returns {string} - Human readable file size.
         */
        addFileSize(headerRow) {
            return humanFileSize(headerRow.episodes.reduce((a, b) => a + (b.file.size || 0), 0));
        },
        searchSubtitle(event, episode, lang) {
            const { id, indexer, getEpisodes, show, subtitleSearchComponents } = this;
            const SubtitleSearchClass = Vue.extend(SubtitleSearch); // eslint-disable-line no-undef
            const instance = new SubtitleSearchClass({
                propsData: { show, episode, key: episode.originalIndex, lang },
                parent: this
            });

            // Update the show, as we downloaded new subtitle(s)
            instance.$on('update', event => {
                // This could be replaced by the generic websocket updates in future.
                if (event.reason === 'new subtitles found') {
                    getEpisodes({ id, indexer, season: episode.season });
                }
            });

            const node = document.createElement('div');
            const tableRef = episode.season === 0 ? 'table-specials' : 'table-seasons';
            this.$refs[tableRef].$refs[`row-${episode.originalIndex}`][0].after(node);
            instance.$mount(node);
            subtitleSearchComponents.push(instance);
        },

        /**
         * Attaches IMDB tooltip
         */
        reflowLayout: debounce(() => {
            console.debug('Reflowing layout');
            addQTip(); // eslint-disable-line no-undef
        }, 1000),

        setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode) {
            const { $snotify, id, indexer, show } = this;

            if (!show.config.scene) {
                $snotify.warning(
                    'To change episode scene numbering you need to enable the show option `scene` first',
                    'Warning',
                    { timeout: 0 }
                );
            }

            if (sceneSeason === '') {
                sceneSeason = null;
            }

            if (sceneEpisode === '') {
                sceneEpisode = null;
            }

            $.getJSON('home/setSceneNumbering', {
                indexername: indexer,
                seriesid: id,
                forSeason,
                forEpisode,
                sceneSeason,
                sceneEpisode
            }, data => {
                // Set the values we get back
                if (data.sceneSeason === null || data.sceneEpisode === null) {
                    $('#sceneSeasonXEpisode_' + id + '_' + forSeason + '_' + forEpisode).val('');
                } else {
                    $('#sceneSeasonXEpisode_' + id + '_' + forSeason + '_' + forEpisode).val(data.sceneSeason + 'x' + data.sceneEpisode);
                }

                if (!data.success) {
                    if (data.errorMessage) {
                        alert(data.errorMessage); // eslint-disable-line no-alert
                    } else {
                        alert('Update failed.'); // eslint-disable-line no-alert
                    }
                }
            });
        },
        setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute) {
            const { $snotify, id, indexer, show } = this;

            if (!show.config.scene) {
                $snotify.warning(
                    'To change an anime episode scene numbering you need to enable the show option `scene` first',
                    'Warning',
                    { timeout: 0 }
                );
            }

            if (sceneAbsolute === '') {
                sceneAbsolute = null;
            }

            $.getJSON('home/setSceneNumbering', {
                indexername: indexer,
                seriesid: id,
                forAbsolute,
                sceneAbsolute
            }, data => {
                // Set the values we get back
                if (data.sceneAbsolute === null) {
                    $('#sceneAbsolute_' + id + '_' + forAbsolute).val('');
                } else {
                    $('#sceneAbsolute_' + id + '_' + forAbsolute).val(data.sceneAbsolute);
                }

                if (!data.success) {
                    if (data.errorMessage) {
                        alert(data.errorMessage); // eslint-disable-line no-alert
                    } else {
                        alert('Update failed.'); // eslint-disable-line no-alert
                    }
                }
            });
        },
        setInputValidInvalid(valid, el) {
            if (valid) {
                $(el).css({
                    'background-color': '#90EE90', // Green
                    'color': '#FFF', // eslint-disable-line quote-props
                    'font-weight': 'bold'
                });
                return true;
            }

            $(el).css({
                'background-color': '#FF0000', // Red
                'color': '#FFF !important', // eslint-disable-line quote-props
                'font-weight': 'bold'
            });
            return false;
        },
        /**
         * Check if any of the episodes in this season does not have the status "unaired".
         * If that's the case we want to manual season search icon.
         * @param {object} season - A season object.
         * @returns {Boolean} - true if one of the seasons episodes has a status 'unaired'.
         */
        anyEpisodeNotUnaired(season) {
            return season.episodes.filter(ep => ep.status !== 'Unaired').length > 0;
        },
        episodesInverse(season) {
            const { invertTable } = this;
            if (!season.episodes) {
                return [];
            }

            if (invertTable) {
                return season.episodes.slice().reverse();
            }

            return season.episodes;
        },
        /**
         * Check if the season/episode combination exists in the scene numbering.
         * @param {Object} episode - object.
         * @returns {Object} with scene season and episodes mapped numbering.
         */
        getSceneNumbering(episode) {
            const { show } = this;
            const { sceneNumbering, xemNumbering } = show;

            if (!show.config.scene) {
                return { season: 0, episode: 0 };
            }

            // Manually configured scene numbering
            if (sceneNumbering.length !== 0) {
                const mapped = sceneNumbering.filter(x => {
                    return x.source.season === episode.season && x.source.episode === episode.episode;
                });
                if (mapped.length !== 0) {
                    return mapped[0].destination;
                }
            }

            // Scene numbering downloaded from thexem.de.
            if (xemNumbering.length !== 0) {
                const mapped = xemNumbering.filter(x => {
                    return x.source.season === episode.season && x.source.episode === episode.episode;
                });
                if (mapped.length !== 0) {
                    return mapped[0].destination;
                }
            }

            return { season: episode.scene.season || 0, episode: episode.scene.episode || 0 };
        },
        getSceneAbsoluteNumbering(episode) {
            const { show } = this;
            const { sceneAbsoluteNumbering, xemAbsoluteNumbering } = show;

            if (!show.config.anime || !show.config.scene) {
                return episode.scene.absoluteNumber;
            }

            if (Object.keys(sceneAbsoluteNumbering).length > 0 && sceneAbsoluteNumbering[episode.absoluteNumber]) {
                return sceneAbsoluteNumbering[episode.absoluteNumber].sceneAbsolute;
            }

            if (Object.keys(xemAbsoluteNumbering).length > 0 && xemAbsoluteNumbering[episode.absoluteNumber]) {
                return xemAbsoluteNumbering[episode.absoluteNumber].sceneAbsolute;
            }

            return episode.scene.absoluteNumber;
        },
        /**
         * Vue-js-modal requires a method, to pass an event to.
         * The event then can be used to assign the value of the episode.
         * @param {Object} event - vue js modal event
         */
        beforeBacklogSearchModalClose(event) {
            this.backlogSearchEpisodes = event.params.episodes;
        },
        /**
         * Vue-js-modal requires a method, to pass an event to.
         * The event then can be used to assign the value of the episode.
         * @param {Object} event - vue js modal event
         */
        beforeFailedSearchModalClose(event) {
            this.failedSearchEpisode = event.params.episode;
        },
        retryDownload(episode) {
            const { stateSearch } = this;
            return (stateSearch.general.failedDownloads.enabled && ['Snatched', 'Snatched (Proper)', 'Snatched (Best)', 'Downloaded'].includes(episode.status));
        },
        search(episodes, searchType) {
            const { show } = this;
            let data = {};

            if (episodes) {
                data = {
                    showSlug: show.id.slug,
                    episodes: [],
                    options: {}
                };
                episodes.forEach(episode => {
                    data.episodes.push(episode.slug);
                    this.$refs[`search-${episode.slug}`].src = 'images/loading16-dark.gif';
                });
            }

            api.put(`search/${searchType}`, data) // eslint-disable-line no-undef
                .then(_ => {
                    if (episodes.length === 1) {
                        console.info(`started search for show: ${show.id.slug} episode: ${episodes[0].slug}`);
                        this.$refs[`search-${episodes[0].slug}`].src = 'images/queued.png';
                        this.$refs[`search-${episodes[0].slug}`].disabled = true;
                    } else {
                        console.info('started a full backlog search');
                    }
                }).catch(error => {
                    console.error(String(error));

                    episodes.forEach(episode => {
                        data.episodes.push(episode.slug);
                        this.$refs[`search-${episodes[0].slug}`].src = 'images/no16.png';
                    });
                }).finally(() => {
                    this.failedSearchEpisode = null;
                    this.backlogSearchEpisodes = [];
                });
        },
        /**
         * Start a backlog search or failed search for the specific episode.
         * A failed search is started depending on the current episodes status.
         * @param {Object} episode - Episode object. If no episode object is passed, a backlog search is started.
         */
        queueSearch(episode) {
            const { $modal, search, retryDownload } = this;
            const episodeIdentifier = episode.slug;
            if (episode) {
                if (this.$refs[`search-${episodeIdentifier}`].disabled === true) {
                    return;
                }

                if (retryDownload(episode)) {
                    $modal.show('query-mark-failed-and-search', { episode });
                } else {
                    search([episode], 'backlog');
                }
            }
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
            const { config } = show;
            const { aliases } = config;
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
            if (aliases.find(x => x.season === season)) {
                // If there is not a match on the xem table, display it as a medusa scene exception
                bindData = {
                    id: `xem-exception-season-${foundInXem ? xemSeasons[0] : season}`,
                    alt: foundInXem ? '[xem]' : '[medusa]',
                    src: foundInXem ? 'images/xem.png' : 'images/ico/favicon-16.png',
                    title: foundInXem ? xemSeasons.reduce((a, b) => {
                        return a.concat(aliases.filter(alias => alias.season === b).map(alias => alias.title));
                    }, []).join(', ') : aliases.filter(alias => alias.season === season).map(alias => alias.title).join(', ')
                };
            }

            return bindData;
        },
        updateEpisodeWatched(episode, watched) {
            const { id, indexer, getEpisodes, show } = this;
            const patchData = {};

            patchData[episode.slug] = { watched };

            api.patch(`series/${show.id.slug}/episodes`, patchData) // eslint-disable-line no-undef
                .then(_ => {
                    console.info(`patched episode ${episode.slug} with watched set to ${watched}`);
                    getEpisodes({ id, indexer, season: episode.season });
                }).catch(error => {
                    console.error(String(error));
                });

            episode.watched = watched;
        },
        updatePaginationPerPage(rows) {
            const { setCookie } = this;
            this.paginationPerPage = rows;
            setCookie('pagination-perPage', rows);
        },
        onPageChange(params) {
            this.loadEpisodes(params.currentPage);
        },
        neededSeasons(page) {
            const { layout, paginationPerPage, show } = this;
            const { seasonCount } = show;
            if (!seasonCount || seasonCount.length === 0) {
                return [];
            }

            if (!layout.show.pagination.enable) {
                return seasonCount.filter(season => season.season !== 0).map(season => season.season).reverse();
            }

            const seasons = show.seasonCount.length - 1;

            let pagesCount = 1;
            let episodeCount = 0;
            const pages = {};
            for (let i = seasons; i >= 0; i--) {
                const { season } = show.seasonCount[i];
                // Exclude specials
                if (season === 0) {
                    break;
                }

                if (pagesCount in pages) {
                    pages[pagesCount].push(season);
                } else {
                    pages[pagesCount] = [season];
                }

                episodeCount += show.seasonCount[i].episodeCount;
                if (episodeCount / paginationPerPage > pagesCount) {
                    pagesCount++;
                    pages[pagesCount] = [season];
                }

                if (pagesCount > page) {
                    break;
                }
            }
            return pages[page] || [];
        },
        loadEpisodes(page) {
            const { id, indexer, getEpisodes } = this;
            // Wrap getEpisodes into an async/await function, so we can wait for the season to have been committed
            // before going on to the next one.
            const _getEpisodes = async (id, indexer) => {
                for (const season of this.neededSeasons(page)) {
                    // We're waiting for the results by design, to give vue the chance to update the dom.
                    // If we fire all the promises at once for, for example 25 seasons. We'll overload medusa's app
                    // and chance is high a number of requests will timeout.
                    await getEpisodes({ id, indexer, season }); // eslint-disable-line no-await-in-loop
                }
            };

            _getEpisodes(id, indexer);
        },
        initializeEpisodes() {
            const { getEpisodes, id, indexer, setRecentShow, show } = this;
            if (!show.seasons && show.seasonCount) {
                // Load episodes for the first page.
                this.loadEpisodes(1);
                // Always get special episodes if available.
                if (show.seasonCount.length > 0 && show.seasonCount[0].season === 0) {
                    getEpisodes({ id, indexer, season: 0 });
                }
            }

            if (show.id.slug) {
                // For now i'm dumping this here
                setRecentShow({
                    indexerName: show.indexer,
                    showId: show.id[show.indexer],
                    name: show.title
                });
            }
        },
        mobileSelectSearch(event, episode) {
            const { $snotify, $router, queueSearch, searchSubtitle, show } = this;
            if (event.target.value === 'forced') {
                queueSearch(episode);
                $snotify.success(
                    `Search started for S${episode.season} E${episode.episode}`
                );
            }

            if (event.target.value === 'manual') {
                // Use the router to navigate to snatchSelection.
                $router.push({ name: 'snatchSelection', query: {
                    indexername: show.indexer,
                    seriesid: show.id[show.indexer],
                    season: episode.season,
                    episode: episode.episode
                } });
            }

            if (event.target.value === 'subtitle') {
                searchSubtitle(event, episode);
            }

            setTimeout(() => {
                event.target.value = 'search action';
            }, 2000);
        }
    },
    watch: {
        'show.id.slug': function(slug) { // eslint-disable-line object-shorthand
            // Show's slug has changed, meaning the show's page has finished loading.
            if (slug) {
                // This is still technically jQuery. Meaning whe're still letting jQuery do its thing on the entire dom.
                updateSearchIcons(slug, this);
            }
        }
    }
};
</script>

<style scoped>
@import '../style/modal.css';

.defaultTable.displayShow {
    clear: both;
}

.displayShowTable.displayShow {
    clear: both;
}

.fanartBackground.displayShow {
    clear: both;
    opacity: 0.9;
}

.fanartBackground table {
    table-layout: auto;
    width: 100%;
    border-collapse: collapse;
    border-spacing: 0;
    text-align: center;
    border: none;
    empty-cells: show;
    color: rgb(0, 0, 0) !important;
}

.summaryFanArt {
    opacity: 0.9;
}

.fanartBackground > table th.vgt-row-header {
    border: none !important;
    background-color: transparent !important;
    color: rgb(255, 255, 255) !important;
    padding-top: 15px !important;
    text-align: left !important;
}

.fanartBackground td.col-search {
    text-align: center;
}

/* Trying to migrate this from tablesorter */

/* =======================================================================
tablesorter.css
========================================================================== */

.displayShow >>> .vgt-global-search__input.vgt-pull-left {
    float: left;
    height: 40px;
}

.displayShow >>> .vgt-input {
    border: 1px solid #ccc;
    transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out, -webkit-box-shadow 0.15s ease-in-out;
    height: 30px;
    padding: 5px 10px;
    font-size: 12px;
    line-height: 1.5;
    border-radius: 3px;
}

.displayShow >>> div.vgt-responsive > table tbody > tr > th.vgt-row-header > span {
    font-size: 24px;
    margin-top: 20px;
    margin-bottom: 10px;
}

.displayShow >>> .vgt-table {
    width: 100%;
    margin-right: auto;
    margin-left: auto;
    color: rgb(0, 0, 0);
    text-align: left;
    border-spacing: 0;
}

.displayShow >>> .vgt-table th,
.displayShow >>> .vgt-table td {
    padding: 4px;
    border-top: rgb(34, 34, 34) 1px solid;
    border-left: rgb(34, 34, 34) 1px solid;
    vertical-align: middle;
}

/* remove extra border from left edge */
.displayShow >>> .vgt-table th:first-child,
.displayShow >>> .vgt-table td:first-child {
    border-left: none;
}

.displayShow >>> .vgt-table th {
    /* color: rgb(255, 255, 255); */
    text-align: center;
    text-shadow: -1px -1px 0 rgba(0, 0, 0, 0.3);
    background-color: rgb(51, 51, 51);
    border-collapse: collapse;
    font-weight: normal;
    white-space: nowrap;
    color: rgb(255, 255, 255);
}

.displayShow >>> .vgt-table span.break-word {
    word-wrap: break-word;
}

.displayShow >>> .vgt-table thead th.sorting.sorting-desc {
    background-color: rgb(85, 85, 85);
    background-image: url(data:image/gif;base64,R0lGODlhFQAEAIAAAP///////yH5BAEAAAEALAAAAAAVAAQAAAINjB+gC+jP2ptn0WskLQA7);
}

.displayShow >>> .vgt-table thead th.sorting.sorting-asc {
    background-color: rgb(85, 85, 85);
    background-image: url(data:image/gif;base64,R0lGODlhFQAEAIAAAP///////yH5BAEAAAEALAAAAAAVAAQAAAINjI8Bya2wnINUMopZAQA7);
    background-position-x: right;
    background-position-y: bottom;
}

.displayShow >>> .vgt-table thead th.sorting {
    background-repeat: no-repeat;
}

.displayShow >>> .vgt-table thead th {
    background-image: none;
    padding: 4px;
    cursor: default;
}

.displayShow >>> .vgt-table input.tablesorter-filter {
    width: 98%;
    height: auto;
    -webkit-box-sizing: border-box;
    -moz-box-sizing: border-box;
    box-sizing: border-box;
}

.displayShow >>> .vgt-table tr.tablesorter-filter-row,
.displayShow >>> .vgt-table tr.tablesorter-filter-row td {
    text-align: center;
}

/* optional disabled input styling */
.displayShow >>> .vgt-table input.tablesorter-filter-row .disabled {
    display: none;
}

.tablesorter-header-inner {
    padding: 0 2px;
    text-align: center;
}

.displayShow >>> .vgt-table tfoot tr {
    color: rgb(255, 255, 255);
    text-align: center;
    text-shadow: -1px -1px 0 rgba(0, 0, 0, 0.3);
    background-color: rgb(51, 51, 51);
    border-collapse: collapse;
}

.displayShow >>> .vgt-table tfoot a {
    color: rgb(255, 255, 255);
    text-decoration: none;
}

.displayShow >>> .vgt-table th.vgt-row-header {
    text-align: left;
}

.displayShow >>> .vgt-table .season-header {
    display: inline;
    margin-left: 5px;
}

.displayShow >>> .vgt-table tr.spacer {
    height: 25px;
}

.displayShow >>> .unaired {
    background-color: rgb(245, 241, 228);
}

.displayShow >>> .skipped {
    background-color: rgb(190, 222, 237);
}

.displayShow >>> .preferred {
    background-color: rgb(195, 227, 200);
}

.displayShow >>> .archived {
    background-color: rgb(195, 227, 200);
}

.displayShow >>> .allowed {
    background-color: rgb(255, 218, 138);
}

.displayShow >>> .wanted {
    background-color: rgb(255, 176, 176);
}

.displayShow >>> .snatched {
    background-color: rgb(235, 193, 234);
}

.displayShow >>> .downloaded {
    background-color: rgb(255, 218, 138);
}

.displayShow >>> .failed {
    background-color: rgb(255, 153, 153);
}

.displayShow >>> span.unaired {
    color: rgb(88, 75, 32);
}

.displayShow >>> span.skipped {
    color: rgb(29, 80, 104);
}

.displayShow >>> span.preffered {
    color: rgb(41, 87, 48);
}

.displayShow >>> span.allowed {
    color: rgb(118, 81, 0);
}

.displayShow >>> span.wanted {
    color: rgb(137, 0, 0);
}

.displayShow >>> span.snatched {
    color: rgb(101, 33, 100);
}

.displayShow >>> span.unaired b,
.displayShow >>> span.skipped b,
.displayShow >>> span.preferred b,
.displayShow >>> span.allowed b,
.displayShow >>> span.wanted b,
.displayShow >>> span.snatched b {
    color: rgb(0, 0, 0);
    font-weight: 800;
}

.mobile-select {
    width: 110px;
    font-size: x-small;
}

td.col-footer {
    text-align: left !important;
}

.displayShow >>> .vgt-wrap__footer {
    color: rgb(255, 255, 255);
    padding: 1em;
    background-color: rgb(51, 51, 51);
    margin-bottom: 1em;
    display: flex;
    justify-content: space-between;
}

.displayShow >>> .footer__row-count,
.displayShow >>> .footer__navigation__page-info {
    display: inline;
}

.displayShow >>> .footer__row-count__label {
    margin-right: 1em;
}

.displayShow >>> .vgt-wrap__footer .footer__navigation {
    font-size: 14px;
}

.displayShow >>> .vgt-pull-right {
    float: right !important;
}

.displayShow >>> .vgt-wrap__footer .footer__navigation__page-btn .chevron {
    width: 24px;
    height: 24px;
    border-radius: 15%;
    position: relative;
    margin: 0 8px;
}

.displayShow >>> .vgt-wrap__footer .footer__navigation__info,
.displayShow >>> .vgt-wrap__footer .footer__navigation__page-info {
    display: inline-flex;
    color: #909399;
    margin: 0 16px;
    margin-top: 0;
    margin-right: 16px;
    margin-bottom: 0;
    margin-left: 16px;
}

.select-info span {
    margin-left: 5px;
    line-height: 40px;
}

.subtitles > div {
    float: left;
}

.subtitles > div:not(:last-child) {
    margin-right: 2px;
}

.displayShow >>> .vgt-dropdown-menu {
    position: absolute;
    z-index: 1000;
    float: left;
    min-width: 160px;
    padding: 5px 0;
    margin: 2px 0 0;
    font-size: 14px;
    text-align: left;
    list-style: none;
    background-clip: padding-box;
    border-radius: 4px;
}

.displayShow >>> .vgt-dropdown-menu > li > span {
    display: block;
    padding: 3px 20px;
    clear: both;
    font-weight: 400;
    line-height: 1.42857143;
    white-space: nowrap;
}

</style>
