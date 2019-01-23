<template>
    <div id="add-show-options-content">
        <fieldset class="component-group-list">
            <div class="form-group">
                <div class="row">
                    <label for="customQuality" class="col-sm-2 control-label">
                        <span>Quality</span>
                    </label>
                    <div class="col-sm-10 content">
                        <quality-chooser :overall-quality="defaultConfig.quality" @update:quality:allowed="quality.allowed = $event" @update:quality:preferred="quality.preferred = $event"></quality-chooser>
                    </div>
                </div>
            </div>

            <div v-if="subtitlesEnabled" id="use-subtitles">
                <config-toggle-slider label="Subtitles" id="subtitles" :value="selectedSubtitleEnabled" @input="selectedSubtitleEnabled = $event"
                    :explanations="['Download subtitles for this show?']">
                </config-toggle-slider>
            </div>

           <div class="form-group">
                <div class="row">
                    <label for="defaultStatus" class="col-sm-2 control-label">
                        <span>Status for previously aired episodes</span>
                    </label>
                    <div class="col-sm-10 content">
                        <select id="defaultStatus" class="form-control form-control-inline input-sm" v-model="selectedStatus">
                            <option v-for="option in defaultEpisodeStatusOptions" :value="option.value" :key="option.value">{{ option.text }}</option>
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
                            <option v-for="option in defaultEpisodeStatusOptions" :value="option.value" :key="option.value">{{ option.text }}</option>
                        </select>
                    </div>
                </div>
            </div>

            <config-toggle-slider label="Season Folders" id="season_folders" :value="selectedSeasonFoldersEnabled" :disabled="namingForceFolders"
                :explanations="['Group episodes by season folders?']" @input="selectedSeasonFoldersEnabled = $event">
            </config-toggle-slider>

            <config-toggle-slider v-if="enableAnimeOptions" label="Anime" id="anime"
                :explanations="['Is this show an Anime?']" :value="selectedAnimeEnabled" @input="selectedAnimeEnabled = $event">
            </config-toggle-slider>

            <div v-if="enableAnimeOptions && selectedAnimeEnabled" class="form-group">
                <div class="row">
                    <label for="anidbReleaseGroup" class="col-sm-2 control-label">
                        <span>Release Groups</span>
                    </label>
                    <div class="col-sm-10 content">
                        <anidb-release-group-ui class="max-width" :blacklist="release.blacklist" :whitelist="release.whitelist"
                            :all-groups="release.allgroups" @change="onChangeReleaseGroupsAnime">
                        </anidb-release-group-ui>
                    </div>
                </div>
            </div>

            <config-toggle-slider label="Scene Numbering" id="scene" :value="selectedSceneEnabled"
                :explanations="['Is this show scene numbered?']" @input="selectedSceneEnabled = $event">
            </config-toggle-slider>

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
import { mapState } from 'vuex';
import { apiRoute } from '../api';
import { combineQualities } from '../utils';
import { ConfigToggleSlider } from './helpers';
import AnidbReleaseGroupUi from './anidb-release-group-ui.vue';

export default {
    name: 'add-show-options',
    components: {
        AnidbReleaseGroupUi,
        ConfigToggleSlider
        // @TODO: Add `QualityChooser`
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
        }
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
                whitelist: [],
                allgroups: []
            }
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
            vm.selectedAnimeEnabled
        ].join(), () => {
            this.update();
        });
    },
    methods: {
        getReleaseGroups(showName) {
            const params = {
                series_name: showName // eslint-disable-line camelcase
            };

            return apiRoute
                .get('home/fetch_releasegroups', { params, timeout: 30000 })
                .then(response => response.data)
                .catch(error => {
                    this.$snotify.warning(
                        `Error while trying to fetch release groups for show "${showName}": ${error || 'Unknown'}`,
                        'Error'
                    );
                    console.warn(error);
                    return null;
                });
        },
        update() {
            const {
                selectedSubtitleEnabled,
                selectedStatus,
                selectedStatusAfter,
                selectedSeasonFoldersEnabled,
                selectedAnimeEnabled,
                selectedSceneEnabled,
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
                    release,
                    quality
                });
            });
        },
        onChangeReleaseGroupsAnime(items) {
            this.release.whitelist = items.filter(item => item.memberOf === 'whitelist').map(item => item.name);
            this.release.blacklist = items.filter(item => item.memberOf === 'blacklist').map(item => item.name);
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
                selectedSceneEnabled
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
                    scene: selectedSceneEnabled
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
    computed: {
        ...mapState({
            defaultConfig: state => state.config.showDefaults,
            namingForceFolders: state => state.config.namingForceFolders,
            subtitlesEnabled: state => state.config.subtitles.enabled,
            episodeStatuses: state => state.statuses
        }),
        defaultEpisodeStatusOptions() {
            const { strings, values } = this.episodeStatuses;
            const { skipped, wanted, ignored } = values;
            return [skipped, wanted, ignored].map(value => ({
                value,
                text: strings[value]
            }));
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
                selectedSceneEnabled
            } = this;

            return [
                selectedStatus === defaultConfig.status,
                selectedStatusAfter === defaultConfig.statusAfter,
                combinedQualities === defaultConfig.quality,
                selectedSeasonFoldersEnabled === (defaultConfig.seasonFolders || namingForceFolders),
                selectedSubtitleEnabled === defaultConfig.subtitles,
                !enableAnimeOptions || selectedAnimeEnabled === defaultConfig.anime,
                selectedSceneEnabled === defaultConfig.scene
            ].every(Boolean);
        }
    },
    asyncComputed: {
        releaseGroups() {
            const { selectedAnimeEnabled, showName } = this;
            if (!selectedAnimeEnabled || !showName) {
                return Promise.resolve([]);
            }

            return this.getReleaseGroups(showName).then(result => {
                if (result.groups) {
                    return result.groups;
                }
            });
        }
    },
    watch: {
        releaseGroups(groups) {
            this.release.allgroups = groups;
        },
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
        selectedAnimeEnabled() {
            this.$emit('refresh');
            this.update();
        },
        defaultConfig(newValue) {
            const { namingForceFolders } = this;
            this.selectedStatus = newValue.status;
            this.selectedStatusAfter = newValue.statusAfter;
            this.selectedSubtitleEnabled = newValue.subtitles;
            this.selectedAnimeEnabled = newValue.anime;
            this.selectedSeasonFoldersEnabled = newValue.seasonFolders || namingForceFolders;
            this.selectedSceneEnabled = newValue.scene;
        }
    }
};
</script>
<style>

</style>
