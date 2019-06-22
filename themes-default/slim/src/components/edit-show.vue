<template>
    <div id="config-content">
    <vue-snotify></vue-snotify>
    <backstretch slug="${show.slug}"></backstretch>

    <h1 class="header">
        Edit Show
        <span v-show="show.title"> - <app-link :href="showUrl">{{show.title}}</app-link></span>
    </h1>

        <div id="config" :class="{ summaryFanArt: config.fanartBackground }">
            <form @submit.prevent="saveShow('all')" class="form-horizontal">
            <div id="config-components">
                <ul>
                    <li><app-link href="#core-component-group1">Main</app-link></li>
                    <li><app-link href="#core-component-group2">Format</app-link></li>
                    <li><app-link href="#core-component-group3">Advanced</app-link></li>
                </ul>
                <div id="core-component-group1">
                    <div class="component-group">
                        <h3>Main Settings</h3>
                        <fieldset class="component-group-list">
                            <config-template label-for="location" label="Show Location">
                                <file-browser name="location" title="Select Show Location" :initial-dir="show.config.location" @update="show.config.location = $event"></file-browser>
                            </config-template>

                            <config-template label-for="qualityPreset" label="Quality">
                                <quality-chooser
                                    :overall-quality="combinedQualities"
                                    :show-slug="show.id.slug"
                                    @update:quality:allowed="show.config.qualities.allowed = $event"
                                    @update:quality:preferred="show.config.qualities.preferred = $event"
                                ></quality-chooser>
                            </config-template>

                            <config-template label-for="defaultEpStatusSelect" label="Default Episode Status">
                                <select name="defaultEpStatus" id="defaultEpStatusSelect" class="form-control form-control-inline input-sm"
                                    v-model="show.config.defaultEpisodeStatus">
                                    <option v-for="option in defaultEpisodeStatusOptions" :value="option.value" :key="option.value">{{ option.text }}</option>
                                    <p>This will set the status for future episodes.</p>
                                </select>
                            </config-template>

                            <config-template label-for="indexerLangSelect" label="Info Language">
                                    <language-select id="indexerLangSelect" @update-language="updateLanguage" :language="show.language" :available="availableLanguages" name="indexer_lang" class="form-control form-control-inline input-sm"></language-select>
                                    <div class="clear-left"><p>This only applies to episode filenames and the contents of metadata files.</p></div>
                            </config-template>

                            <config-toggle-slider v-model="show.config.subtitlesEnabled" label="Subtitles" id="subtitles">
                                <span>search for subtitles</span>
                            </config-toggle-slider>

                            <config-toggle-slider v-model="show.config.paused" label="Paused" id="paused">
                                    <span>pause this show (Medusa will not download episodes)</span>
                            </config-toggle-slider>
                        </fieldset>
                    </div>
                </div>
                <div id="core-component-group2">
                    <div class="component-group">
                        <h3>Format Settings</h3>
                        <fieldset class="component-group-list">

                            <config-toggle-slider v-model="show.config.airByDate" label="Air by date" id="air_by_date">
                                    <span>check if the show is released as Show.03.02.2010 rather than Show.S02E03</span>
                                    <p style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</p>
                            </config-toggle-slider>

                            <config-toggle-slider v-model="show.config.anime" label="Anime" id="anime">
                                    <span>enable if the show is Anime and episodes are released as Show.265 rather than Show.S02E03</span>
                            </config-toggle-slider>

                            <config-template v-if="show.config.anime" label-for="anidbReleaseGroup" label="Release Groups">
                                <anidb-release-group-ui class="max-width" :blacklist="show.config.release.blacklist" :whitelist="show.config.release.whitelist" :all-groups="show.config.release.allgroups" @change="onChangeReleaseGroupsAnime"></anidb-release-group-ui>
                                    <anidb-release-group-ui class="max-width" :blacklist="show.config.release.blacklist" :whitelist="show.config.release.whitelist" :all-groups="show.config.release.allgroups" @change="onChangeReleaseGroupsAnime"></anidb-release-group-ui>
                            </config-template>

                            <config-toggle-slider v-model="show.config.sports" label="Sports" id="sports">
                                    <span>enable if the show is a sporting or MMA event released as Show.03.02.2010 rather than Show.S02E03</span>
                                    <p style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</p>
                            </config-toggle-slider>

                            <config-toggle-slider v-model="show.config.seasonFolders" label="Season" id="season_folders">
                                    <span>group episodes by season folder (disable to store in a single folder)</span>
                            </config-toggle-slider>

                            <config-toggle-slider v-model="show.config.scene" label="Scene Numbering" id="scene_numbering">
                                    <span>search by scene numbering (disable to search by indexer numbering)</span>
                            </config-toggle-slider>

                            <config-toggle-slider v-model="show.config.dvdOrder" label="DVD Order" id="dvd_order">
                                    <span>use the DVD order instead of the air order</span>
                                    <div class="clear-left"><p>A "Force Full Update" is necessary, and if you have existing episodes you need to sort them manually.</p></div>
                            </config-toggle-slider>
                        </fieldset>
                    </div>
                </div>
                <div id="core-component-group3">
                    <div class="component-group">
                        <h3>Advanced Settings</h3>
                        <fieldset class="component-group-list">

                            <config-template label-for="rls_ignore_words" label="Ignored words">
                                    <select-list :list-items="show.config.release.ignoredWords" @change="onChangeIgnoredWords"></select-list>
                                    <div class="clear-left">
                                        <p>Search results with one or more words from this list will be ignored.</p>
                                    </div>
                            </config-template>

                            <config-toggle-slider v-model="show.config.release.ignoredWordsExclude" label="Exclude ignored words" id="ignored_words_exclude">
                                <div>Use the Ignored Words list to exclude these from the global ignored list</div>
                                <p>Currently the effective list is: {{ effectiveIgnored }}</p>
                            </config-toggle-slider>

                            <config-template label-for="rls_require_words" label="Required words">
                                    <select-list :list-items="show.config.release.requiredWords" @change="onChangeRequiredWords"></select-list>
                                        <p>Search results with no words from this list will be ignored.</p>
                            </config-template>

                            <config-toggle-slider v-model="show.config.release.requiredWordsExclude" label="Exclude required words" id="required_words_exclude">
                                <p>Use the Required Words list to exclude these from the global required words list</p>
                                <p>Currently the effective list is: {{ effectiveRequired }}</p>
                            </config-toggle-slider>

                            <config-template label-for="SceneName" label="Scene Exception">
                                    <select-list :list-items="show.config.aliases" @change="onChangeAliases"></select-list>
                                        <p>This will affect episode search on NZB and torrent providers. This list appends to the original show name.</p>
                            </config-template>

                            <config-textbox-number :min="-168" :max="168" :step="1" v-model="show.config.airdateOffset"
                                label="Airdate offset" id="airdate_offset" :explanations="['Amount of hours we want to start searching early (-1) or late (1) for new episodes.',
                                'This only applies to daily searches.']">
                            </config-textbox-number>

                        </fieldset>
                    </div>
                </div>
            </div>
            <br>
            <input id="submit" type="submit" :value="saveButton" class="btn-medusa pull-left button" :disabled="saving || !show">
            </form>
        </div>
    </div>
</template>

<script>
import { mapState, mapGetters, mapActions } from 'vuex';
import { arrayUnique, arrayExclude, combineQualities } from '../utils/core';

export default {
    name: 'editShow',
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
        return {
            defaultEpisodeStatusOptions: [
                { text: 'Wanted', value: 'Wanted' },
                { text: 'Skipped', value: 'Skipped' },
                { text: 'Ignored', value: 'Ignored' }
            ],
            saving: false
        };
    },
    created() {
        const { getShows } = this;
        // Without getting any specific show data, we pick the show needed from the shows array.
        getShows();
    },

    methods: {
        ...mapActions({
            getShows: 'getShows'
        }),
        saveShow(subject) {
            // We want to wait until the page has been fully loaded, before starting to save stuff.
            if (!this.show) {
                return;
            }

            if (!['show', 'all'].includes(subject)) {
                return;
            }

            // Disable the save button until we're done.
            this.saving = true;

            const data = {
                config: {
                    aliases: this.show.config.aliases,
                    defaultEpisodeStatus: this.show.config.defaultEpisodeStatus,
                    dvdOrder: this.show.config.dvdOrder,
                    seasonFolders: this.show.config.seasonFolders,
                    anime: this.show.config.anime,
                    scene: this.show.config.scene,
                    sports: this.show.config.sports,
                    paused: this.show.config.paused,
                    location: this.show.config.location,
                    airByDate: this.show.config.airByDate,
                    subtitlesEnabled: this.show.config.subtitlesEnabled,
                    release: {
                        requiredWords: this.show.config.release.requiredWords,
                        ignoredWords: this.show.config.release.ignoredWords,
                        requiredWordsExclude: this.show.config.release.requiredWordsExclude,
                        ignoredWordsExclude: this.show.config.release.ignoredWordsExclude
                    },
                    qualities: {
                        preferred: this.show.config.qualities.preferred,
                        allowed: this.show.config.qualities.allowed
                    },
                    airdateOffset: this.show.config.airdateOffset
                },
                language: this.show.language
            };

            if (data.config.anime) {
                data.config.release.blacklist = this.show.config.release.blacklist;
                data.config.release.whitelist = this.show.config.release.whitelist;
            }

            const { indexer, id, $store } = this;
            $store.dispatch('setShow', { indexer, id, data, save: true }).then(() => {
                this.$snotify.success(
                    'You may need to "Re-scan files" or "Force Full Update".',
                    'Saved',
                    { timeout: 5000 }
                );
            }).catch(error => {
                this.$snotify.error(
                    'Error while trying to save "' + this.show.title + '": ' + error.message || 'Unknown',
                    'Error'
                );
            }).finally(() => {
                // Re-enable the save button.
                this.saving = false;
            });
        },
        onChangeIgnoredWords(items) {
            this.show.config.release.ignoredWords = items.map(item => item.value);
        },
        onChangeRequiredWords(items) {
            this.show.config.release.requiredWords = items.map(item => item.value);
        },
        onChangeAliases(items) {
            this.show.config.aliases = items.map(item => item.value);
        },
        onChangeReleaseGroupsAnime(items) {
            this.show.config.release.whitelist = items.filter(item => item.memberOf === 'whitelist');
            this.show.config.release.blacklist = items.filter(item => item.memberOf === 'blacklist');
            this.show.config.release.allgroups = items.filter(item => item.memberOf === 'releasegroups');
        },
        updateLanguage(value) {
            this.show.language = value;
        }
    },
    // @TODO: Replace with Object spread (`...mapState`)
    computed: {
        ...mapState({
            shows: state => state.shows.shows,
            configLoaded: state => state.config.fanartBackground !== null,
            config: state => state.config,
            defaultShow: state => state.defaults.show
        }),
        ...mapGetters({
            getShowByIdFromShows: 'getShowByIdFromShows'
        }),
        indexer() {
            return this.showIndexer || this.$route.query.indexername;
        },
        id() {
            return this.showId || Number(this.$route.query.seriesid) || undefined;
        },
        // @TODO: Enable this once we remove this.series
        // show() {
        //     const { $store } = this;
        //     return this.shows.length === 0 ? $store.defaults.show : this.shows.find(show => show.indexer === this.indexer && Number(show.id[show.indexer]) === Number(this.id));
        // },
        availableLanguages() {
            if (this.config.indexers.config.main.validLanguages) {
                return this.config.indexers.config.main.validLanguages.join(',');
            }

            return '';
        },
        combinedQualities() {
            const { allowed, preferred } = this.show.config.qualities;
            return combineQualities(allowed, preferred);
        },
        saveButton() {
            return this.saving === false ? 'Save Changes' : 'Saving...';
        },
        showUrl() {
            // @TODO: Change the URL generation to use `this.series`. Currently not possible because
            // the values are not available at the time of app-link component creation.
            return window.location.pathname.replace('editShow', 'displayShow') + window.location.search;
        },
        globalIgnored() {
            return this.$store.state.search.filters.ignored.map(x => x.toLowerCase());
        },
        globalRequired() {
            return this.$store.state.search.filters.required.map(x => x.toLowerCase());
        },
        effectiveIgnored() {
            const { globalIgnored } = this;
            const showIgnored = this.show.config.release.ignoredWords.map(x => x.toLowerCase());

            if (this.show.config.release.ignoredWordsExclude) {
                return arrayExclude(globalIgnored, showIgnored);
            }

            return arrayUnique(globalIgnored.concat(showIgnored));
        },
        effectiveRequired() {
            const { globalRequired } = this;
            const showRequired = this.show.config.release.requiredWords.map(x => x.toLowerCase());

            if (this.show.config.release.requiredWordsExclude) {
                return arrayExclude(globalRequired, showRequired);
            }

            return arrayUnique(globalRequired.concat(showRequired));
        },
        show() {
            const { defaultShow, id, indexer, getShowByIdFromShows, shows } = this;
            return getShowByIdFromShows({ shows, id, indexer }) || defaultShow;
        }
    }
};
</script>
<style scoped>
</style>
