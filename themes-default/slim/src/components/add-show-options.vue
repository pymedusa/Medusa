<template>
    <div id="add-show-options-content">
        <fieldset class="component-group-list">
            <div class="form-group">
                <div class="row">
                    <label for="customQuality" class="col-sm-2 control-label">
                        <span>Quality</span>
                    </label>
                    <div class="col-sm-10 content">
                        <quality-chooser
                            :overall-quality="defaultConfig.quality"
                            @update:quality:allowed="quality.allowed = $event"
                            @update:quality:preferred="quality.preferred = $event"
                        />
                    </div>
                </div>
            </div>

            <div v-if="subtitlesEnabled" id="use-subtitles">
                <config-toggle-slider
                    label="Subtitles"
                    id="subtitles"
                    :value="selectedSubtitleEnabled"
                    :explanations="['Download subtitles for this show?']"
                    @input="selectedSubtitleEnabled = $event"
                />
            </div>

            <div class="form-group">
                <div class="row">
                    <label for="defaultStatus" class="col-sm-2 control-label">
                        <span>Status for previously aired episodes</span>
                    </label>
                    <div class="col-sm-10 content">
                        <select id="defaultStatus" class="form-control form-control-inline input-sm" v-model="selectedStatus">
                            <option v-for="option in defaultEpisodeStatusOptions" :value="option.value" :key="option.value">{{ option.name }}</option>
                        </select>
                    </div>
                </div>
            </div>

            <div class="form-group">
                <div class="row">
                    <label for="defaultStatusAfter" class="col-sm-2 control-label">
                        <span>Status for all future episodes</span>
                    </label>
                    <div class="col-sm-10 content">
                        <select id="defaultStatusAfter" class="form-control form-control-inline input-sm" v-model="selectedStatusAfter">
                            <option v-for="option in defaultEpisodeStatusOptions" :value="option.value" :key="option.value">{{ option.name }}</option>
                        </select>
                    </div>
                </div>
            </div>

            <config-toggle-slider
                label="Season Folders"
                id="season_folders"
                :value="selectedSeasonFoldersEnabled"
                :disabled="namingForceFolders"
                :explanations="['Group episodes by season folders?']"
                @input="selectedSeasonFoldersEnabled = $event"
            />

            <config-toggle-slider
                v-if="enableAnimeOptions"
                label="Anime"
                id="anime"
                :value="selectedAnimeEnabled"
                :explanations="['Is this show an Anime?']"
                @input="selectedAnimeEnabled = $event"
            />

            <div ref="blackAndWhiteList" v-if="enableAnimeOptions && selectedAnimeEnabled && !disableReleaseGroups" class="form-group">
                <div class="row">
                    <label for="anidbReleaseGroup" class="col-sm-2 control-label">
                        <span>Release Groups</span>
                    </label>
                    <div class="col-sm-10 content">
                        <anidb-release-group-ui
                            class="max-width"
                            :show-name="showName"
                            @change="onChangeReleaseGroupsAnime"
                        />
                    </div>
                </div>
            </div>

            <config-toggle-slider
                label="Scene Numbering"
                id="scene"
                :value="selectedSceneEnabled"
                :explanations="['Is this show scene numbered?']"
                @input="selectedSceneEnabled = $event"
            />

            <config-template label-for="show_lists" label="Display in show lists">
                <multiselect
                    v-model="selectedShowLists"
                    :multiple="true"
                    :options="layout.show.showListOrder.map(list => list.toLowerCase())"
                    @input="selectedShowLists = $event"
                />
            </config-template>

            <div class="form-group">
                <div class="row">
                    <label for="saveDefaultsButton" class="col-sm-2 control-label">
                        <span>Use current values as the defaults</span>
                    </label>
                    <div class="col-sm-10 content">
                        <button type="button" class="btn-medusa btn-inline" @click.prevent="saveDefaults" :disabled="saving || saveDefaultsDisabled">Save Defaults</button>
                    </div>
                </div>
            </div>
        </fieldset>
    </div>
</template>

<script>
import { mapActions, mapState, mapGetters } from 'vuex';
import { combineQualities } from '../utils/core';
import {
    ConfigTemplate,
    ConfigToggleSlider,
    QualityChooser
} from './helpers';
import AnidbReleaseGroupUi from './anidb-release-group-ui.vue';
import Multiselect from 'vue-multiselect';

export default {
    name: 'add-show-options',
    components: {
        AnidbReleaseGroupUi,
        ConfigTemplate,
        ConfigToggleSlider,
        Multiselect,
        QualityChooser
    },
    props: {
        showName: {
            type: String,
            default: '',
            required: false
        },
        enableAnimeOptions: {
            type: Boolean,
            default: false
        },
        disableReleaseGroups: Boolean
    },
    data() {
        return {
            saving: false,
            selectedStatus: null,
            selectedStatusAfter: null,
            quality: {
                allowed: [],
                preferred: []
            },
            selectedSubtitleEnabled: false,
            selectedSeasonFoldersEnabled: false,
            selectedAnimeEnabled: false,
            selectedSceneEnabled: false,
            release: {
                blacklist: [],
                whitelist: []
            },
            selectedShowLists: []
        };
    },
    mounted() {
        const { defaultConfig, update } = this;
        this.selectedStatus = defaultConfig.status;
        this.selectedStatusAfter = defaultConfig.statusAfter;
        this.$nextTick(() => update());

        this.$watch(vm => [
            vm.selectedStatus,
            vm.selectedStatusAfter,
            vm.selectedSubtitleEnabled,
            vm.selectedSeasonFoldersEnabled,
            vm.selectedSceneEnabled,
            vm.selectedAnimeEnabled,
            vm.selectedShowLists
        ].join(), () => {
            this.update();
        });
    },
    computed: {
        ...mapState({
            defaultConfig: state => state.config.general.showDefaults,
            layout: state => state.config.layout,
            namingForceFolders: state => state.config.general.namingForceFolders,
            subtitlesEnabled: state => state.config.general.subtitles.enabled,
            episodeStatuses: state => state.config.consts.statuses,
            anime: state => state.config.anime
        }),
        ...mapGetters([
            'getStatus'
        ]),
        defaultEpisodeStatusOptions() {
            const { getStatus } = this;
            if (this.episodeStatuses.length === 0) {
                return [];
            }
            // Get status objects, in this order
            return ['skipped', 'wanted', 'ignored'].map(key => getStatus({ key }));
        },
        /**
         * Calculate the combined value of the selected qualities.
         * @returns {number} - An unsigned integer.
         */
        combinedQualities() {
            const { quality } = this;
            const { allowed, preferred } = quality;
            return combineQualities(allowed, preferred);
        },
        /**
         * Check if any changes were made to determine if the "Save Defaults" button should be enabled.
         * @returns {boolean} - Should the save default buttons be disabled?
         */
        saveDefaultsDisabled() {
            const {
                enableAnimeOptions,
                defaultConfig,
                namingForceFolders,
                selectedStatus,
                selectedStatusAfter,
                combinedQualities,
                selectedSeasonFoldersEnabled,
                selectedSubtitleEnabled,
                selectedAnimeEnabled,
                selectedSceneEnabled,
                selectedShowLists
            } = this;

            return [
                selectedStatus === defaultConfig.status,
                selectedStatusAfter === defaultConfig.statusAfter,
                combinedQualities === defaultConfig.quality,
                selectedSeasonFoldersEnabled === (defaultConfig.seasonFolders || namingForceFolders),
                selectedSubtitleEnabled === defaultConfig.subtitles,
                !enableAnimeOptions || selectedAnimeEnabled === defaultConfig.anime,
                selectedSceneEnabled === defaultConfig.scene,
                selectedShowLists === defaultConfig.showLists
            ].every(Boolean);
        }
    },
    methods: {
        ...mapActions({
            setShowConfig: 'setShowConfig'
        }),
        update() {
            const {
                selectedSubtitleEnabled,
                selectedStatus,
                selectedStatusAfter,
                selectedSeasonFoldersEnabled,
                selectedAnimeEnabled,
                selectedSceneEnabled,
                selectedShowLists,
                release,
                quality
            } = this;
            this.$nextTick(() => {
                this.$emit('change', {
                    subtitles: selectedSubtitleEnabled,
                    status: selectedStatus,
                    statusAfter: selectedStatusAfter,
                    seasonFolders: selectedSeasonFoldersEnabled,
                    anime: selectedAnimeEnabled,
                    scene: selectedSceneEnabled,
                    showLists: selectedShowLists,
                    release,
                    quality
                });
            });
        },
        onChangeReleaseGroupsAnime(groupNames) {
            this.release.whitelist = groupNames.whitelist;
            this.release.blacklist = groupNames.blacklist;
            this.update();
        },
        saveDefaults() {
            const {
                $store,
                selectedStatus,
                selectedStatusAfter,
                combinedQualities,
                selectedSubtitleEnabled,
                selectedSeasonFoldersEnabled,
                selectedAnimeEnabled,
                selectedSceneEnabled,
                selectedShowLists
            } = this;

            const section = 'main';
            const config = {
                showDefaults: {
                    status: selectedStatus,
                    statusAfter: selectedStatusAfter,
                    quality: combinedQualities,
                    subtitles: selectedSubtitleEnabled,
                    seasonFolders: selectedSeasonFoldersEnabled,
                    anime: selectedAnimeEnabled,
                    scene: selectedSceneEnabled,
                    showLists: selectedShowLists
                }
            };

            this.saving = true;
            $store.dispatch('setConfig', { section, config }).then(() => {
                this.$snotify.success(
                    'Your "add show" defaults have been set to your current selections.',
                    'Saved Defaults'
                );
            }).catch(error => {
                this.$snotify.error(
                    'Error while trying to save "add show" defaults: ' + (error.message || 'Unknown'),
                    'Error'
                );
            }).finally(() => {
                this.saving = false;
            });
        }
    },

    watch: {
        release: {
            handler() {
                this.$emit('refresh');
                this.update();
            },
            deep: true,
            immediate: false
        },
        /**
         * Whenever something changes that can impact the height of the component,
         * we need to update the parent formWizard, and make it resize.
         */
        quality: {
            handler() {
                this.$emit('refresh');
                this.update();
            },
            deep: true,
            immediate: false
        },
        selectedAnimeEnabled(value) {
            const { anime } = this;

            if (anime.autoAnimeToList) {
                if (value) {
                    // Auto anime to list is enabled. If changing the show format to anime, add 'Anime' to show lists.
                    this.selectedShowLists.push('anime');
                    // The filter makes sure there are unique strings.
                    this.selectedShowLists = this.selectedShowLists.filter((v, i, a) => a.indexOf(v) === i);
                } else {
                    // Remove the anime list.
                    this.selectedShowLists = this.selectedShowLists.filter(list => list.toLowerCase() !== 'anime');
                }
            }

            this.$emit('refresh');
            this.update();
        },
        defaultConfig(newValue) {
            const { layout, namingForceFolders } = this;
            this.selectedStatus = newValue.status;
            this.selectedStatusAfter = newValue.statusAfter;
            this.selectedSubtitleEnabled = newValue.subtitles;
            this.selectedAnimeEnabled = newValue.anime;
            this.selectedSeasonFoldersEnabled = newValue.seasonFolders || namingForceFolders;
            this.selectedSceneEnabled = newValue.scene;
            this.selectedShowLists = newValue.showLists.filter(
                list => layout.show.showListOrder.map(list => list.toLowerCase()).includes(list.toLowerCase())
            ) || [];
        }
    }
};
</script>

<style>
</style>
