<template>
    <div id="config-content">
        <!-- Remove v-if when backstretch is reactive to prop changes -->
        <backstretch v-if="showLoaded" :slug="show.id.slug" />

        <h1 v-if="showLoaded" class="header">
            Edit Show - <app-link :href="`home/displayShow?indexername=${indexer}&seriesid=${id}`">{{ show.title }}</app-link>
        </h1>
        <h1 v-else class="header">
            Edit Show<template v-if="!loadError"> (Loading...)</template>
        </h1>

        <h3 v-if="loadError">Error loading show: {{ loadError }}</h3>

        <div v-if="showLoaded" id="config" :class="{ summaryFanArt: layout.fanartBackground }">
            <form @submit.prevent="saveShow('all')" class="form-horizontal">
                <vue-tabs>
                    <v-tab title="Main">
                        <div class="component-group">
                            <h3>Main Settings</h3>
                            <fieldset class="component-group-list">
                                <config-template label-for="location" label="Show Location">
                                    <file-browser
                                        name="location"
                                        title="Select Show Location"
                                        :key="show.id.slug"
                                        :initial-dir="show.config.location"
                                        @update="show.config.location = $event"
                                    />
                                </config-template>

                                <config-template label-for="qualityPreset" label="Quality">
                                    <quality-chooser
                                        :overall-quality="combinedQualities"
                                        :show-slug="show.id.slug"
                                        @update:quality:allowed="show.config.qualities.allowed = $event"
                                        @update:quality:preferred="show.config.qualities.preferred = $event"
                                    />
                                </config-template>

                                <config-template label-for="defaultEpStatusSelect" label="Default Episode Status">
                                    <select
                                        name="defaultEpStatus"
                                        id="defaultEpStatusSelect"
                                        class="form-control form-control-inline input-sm"
                                        v-model="show.config.defaultEpisodeStatus"
                                    >
                                        <option v-for="option in defaultEpisodeStatusOptions" :value="option.name" :key="option.value">
                                            {{ option.name }}
                                        </option>
                                    </select>
                                    <p>This will set the status for future episodes.</p>
                                </config-template>

                                <config-template label-for="indexerLangSelect" label="Info Language">
                                    <language-select
                                        id="indexerLangSelect"
                                        @update-language="updateLanguage"
                                        :language="show.language"
                                        :available="availableLanguages"
                                        name="indexer_lang"
                                        class="form-control form-control-inline input-sm"
                                    />
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
                    </v-tab>

                    <v-tab title="Format">
                        <div class="component-group">
                            <h3>Format Settings</h3>
                            <fieldset class="component-group-list">

                                <config-toggle-slider :value="show.config.airByDate" @input="changeFormat($event, 'airByDate')" label="Air by date" id="airByDate">
                                    <span>check if the show is released as Show.03.02.2010 rather than Show.S02E03</span>
                                    <p style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</p>
                                </config-toggle-slider>

                                <config-toggle-slider :value="show.config.anime" @input="changeFormat($event, 'anime')" label="Anime" id="anime">
                                    <span>enable if the show is Anime and episodes are released as Show.265 rather than Show.S02E03</span>
                                </config-toggle-slider>

                                <config-template v-if="show.config.anime" label-for="anidbReleaseGroup" label="Release Groups">
                                    <anidb-release-group-ui
                                        v-if="show.title"
                                        class="max-width"
                                        :show-name="show.title"
                                        :blacklist="show.config.release.blacklist"
                                        :whitelist="show.config.release.whitelist"
                                        @change="onChangeReleaseGroupsAnime"
                                    />
                                </config-template>

                                <config-toggle-slider :value="show.config.sports" @input="changeFormat($event, 'sports')" label="Sports" id="sports">
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

                                <config-template label-for="show_lists" label="Display in show lists">
                                    <multiselect
                                        v-model="showLists"
                                        :multiple="true"
                                        :options="layout.show.showListOrder.map(list => list.toLowerCase())"
                                    />
                                </config-template>

                            </fieldset>
                        </div>
                    </v-tab>

                    <v-tab title="Advanced">
                        <div class="component-group">
                            <h3>Advanced Settings</h3>
                            <fieldset class="component-group-list">

                                <config-template label-for="rls_ignore_words" label="Ignored words">
                                    <select-list
                                        :list-items="show.config.release.ignoredWords"
                                        @change="onChangeIgnoredWords"
                                    />
                                    <div class="clear-left">
                                        <p>Search results with one or more words from this list will be ignored.</p>
                                    </div>
                                </config-template>

                                <config-toggle-slider
                                    v-model="show.config.release.ignoredWordsExclude"
                                    label="Exclude ignored words"
                                    id="ignored_words_exclude"
                                >
                                    <div>Use the Ignored Words list to exclude these from the global ignored list</div>
                                    <p>Currently the effective list is: {{ effectiveIgnored }}</p>
                                </config-toggle-slider>

                                <config-template label-for="rls_require_words" label="Required words">
                                    <select-list
                                        :list-items="show.config.release.requiredWords"
                                        @change="onChangeRequiredWords"
                                    />
                                    <p>Search results with no words from this list will be ignored.</p>
                                </config-template>

                                <config-toggle-slider
                                    v-model="show.config.release.requiredWordsExclude"
                                    label="Exclude required words"
                                    id="required_words_exclude"
                                >
                                    <p>Use the Required Words list to exclude these from the global required words list</p>
                                    <p>Currently the effective list is: {{ effectiveRequired }}</p>
                                </config-toggle-slider>

                                <config-template label-for="scene_exceptions" label="Scene Exception">
                                    <config-scene-exceptions v-bind="{ show, exceptions: show.config.aliases }" />
                                </config-template>

                                <config-textbox-number
                                    :min="-168"
                                    :max="168"
                                    :step="1"
                                    v-model="show.config.airdateOffset"
                                    label="Airdate offset"
                                    id="airdate_offset"
                                    :explanations="[
                                        'Amount of hours we want to start searching early (-1) or late (1) for new episodes.',
                                        'This only applies to daily searches.'
                                    ]"
                                />

                            </fieldset>
                        </div>
                    </v-tab>
                </vue-tabs>

                <br>
                <input
                    id="submit"
                    type="submit"
                    :value="saveButton"
                    class="btn-medusa pull-left button"
                    :disabled="saving || !showLoaded"
                >
            </form>
        </div>
    </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'vuex';

import { arrayUnique, arrayExclude, combineQualities } from '../utils/core';
import { VueTabs, VTab } from 'vue-nav-tabs/dist/vue-tabs.js';
import AnidbReleaseGroupUi from './anidb-release-group-ui.vue';
import Backstretch from './backstretch.vue';
import {
    AppLink,
    ConfigSceneExceptions,
    ConfigTemplate,
    ConfigTextboxNumber,
    ConfigToggleSlider,
    FileBrowser,
    LanguageSelect,
    QualityChooser,
    SelectList
} from './helpers';

import Multiselect from 'vue-multiselect';
import 'vue-multiselect/dist/vue-multiselect.min.css';

export default {
    name: 'edit-show',
    components: {
        AnidbReleaseGroupUi,
        AppLink,
        Backstretch,
        ConfigSceneExceptions,
        ConfigTemplate,
        ConfigTextboxNumber,
        ConfigToggleSlider,
        FileBrowser,
        LanguageSelect,
        Multiselect,
        QualityChooser,
        SelectList,
        VueTabs,
        VTab
    },
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
            saving: false,
            loadError: null
        };
    },
    computed: {
        ...mapState({
            general: state => state.config.general,
            indexers: state => state.config.indexers,
            anime: state => state.config.anime,
            layout: state => state.config.layout,
            episodeStatuses: state => state.config.consts.statuses,
            search: state => state.config.search
        }),
        ...mapGetters({
            show: 'getCurrentShow',
            getStatus: 'getStatus'
        }),
        showLists: {
            get() {
                const { show } = this;
                return show.config.showLists.map(list => list.toLowerCase());
            },
            set(value) {
                const { show, setShowConfig } = this;
                setShowConfig({ show, config: { ...show.config, showLists: value } });
            }
        },
        indexer() {
            return this.showIndexer || this.$route.query.indexername;
        },
        id() {
            return this.showId || Number(this.$route.query.seriesid) || undefined;
        },
        showLoaded() {
            return Boolean(this.show.id.slug);
        },
        defaultEpisodeStatusOptions() {
            if (this.episodeStatuses.length === 0) {
                return [];
            }
            // Get status objects, in this order
            return ['wanted', 'skipped', 'ignored'].map(key => this.getStatus({ key }));
        },
        availableLanguages() {
            if (this.indexers.main.validLanguages) {
                return this.indexers.main.validLanguages.join(',');
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
        globalIgnored() {
            const { search } = this;
            return search.filters.ignored.map(x => x.toLowerCase());
        },
        globalRequired() {
            const { search } = this;
            return search.filters.required.map(x => x.toLowerCase());
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
        }
    },
    created() {
        this.loadShow();
    },
    methods: {
        ...mapActions({
            getShow: 'getShow',
            setShow: 'setShow',
            setCurrentShow: 'setCurrentShow',
            setShowConfig: 'setShowConfig'
        }),
        loadShow() {
            const { setCurrentShow, id, indexer, getShow } = this;

            // We need detailed info for the xem / scene exceptions, so let's get it.
            getShow({ id, indexer, detailed: true });

            // Let's tell the store which show we currently want as current.
            // Run this after getShow(), as it will trigger the initializeEpisodes() method.
            setCurrentShow({
                indexer,
                id
            });
        },
        async saveShow(subject) {
            const { show, showLoaded } = this;

            // We want to wait until the page has been fully loaded, before starting to save stuff.
            if (!showLoaded) {
                return;
            }

            if (!['show', 'all'].includes(subject)) {
                return;
            }

            // Disable the save button until we're done.
            this.saving = true;

            const showConfig = show.config;
            const data = {
                config: {
                    aliases: showConfig.aliases,
                    defaultEpisodeStatus: showConfig.defaultEpisodeStatus,
                    dvdOrder: showConfig.dvdOrder,
                    seasonFolders: showConfig.seasonFolders,
                    anime: showConfig.anime,
                    scene: showConfig.scene,
                    sports: showConfig.sports,
                    paused: showConfig.paused,
                    location: showConfig.location,
                    airByDate: showConfig.airByDate,
                    subtitlesEnabled: showConfig.subtitlesEnabled,
                    release: {
                        requiredWords: showConfig.release.requiredWords,
                        ignoredWords: showConfig.release.ignoredWords,
                        requiredWordsExclude: showConfig.release.requiredWordsExclude,
                        ignoredWordsExclude: showConfig.release.ignoredWordsExclude
                    },
                    qualities: {
                        preferred: showConfig.qualities.preferred,
                        allowed: showConfig.qualities.allowed
                    },
                    airdateOffset: showConfig.airdateOffset,
                    showLists: showConfig.showLists
                },
                language: show.language
            };

            if (data.config.anime) {
                data.config.release.blacklist = showConfig.release.blacklist;
                data.config.release.whitelist = showConfig.release.whitelist;
            }

            const { indexer, id, setShow } = this;
            try {
                await setShow({ indexer, id, data });
                this.$snotify.success(
                    'You may need to "Re-scan files" or "Force Full Update".',
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to save ${this.show.title}: ${error.message || 'Unknown'}`,
                    'Error'
                );
            } finally {
                // Re-enable the save button.
                this.saving = false;
            }
        },
        onChangeIgnoredWords(items) {
            this.show.config.release.ignoredWords = items.map(item => item.value);
        },
        onChangeRequiredWords(items) {
            this.show.config.release.requiredWords = items.map(item => item.value);
        },
        onChangeReleaseGroupsAnime(groupNames) {
            this.show.config.release.whitelist = groupNames.whitelist;
            this.show.config.release.blacklist = groupNames.blacklist;
        },
        updateLanguage(value) {
            this.show.language = value;
        },
        changeFormat(value, formatOption) {
            const { anime, general } = this;
            this.show.config[formatOption] = value;
            if (value) {
                // Check each format option, disable the other options.
                ['anime', 'sports', 'airByDate'].filter(item => item !== formatOption).forEach(option => {
                    this.show.config[option] = false;
                });
            }

            if (formatOption === 'anime' && anime.autoAnimeToList) {
                if (value) {
                    // Auto anime to list is enabled. If changing the show format to anime, add 'Anime' to show lists.
                    this.showLists = anime.showlistDefaultAnime;
                    // The filter makes sure there are unique strings.
                    this.showLists = this.showLists.filter((v, i, a) => a.indexOf(v) === i);
                } else {
                    // Return to default show lists.
                    this.showLists = general.showDefaults.showLists;
                }
            }
        }
    }
};
</script>

<style scoped>
</style>
