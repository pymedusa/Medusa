<template>
    <div id="add-show-options-content">
        <fieldset class="component-group-list">
            <div class="form-group">
                <div class="row">
                    <label for="customQuality" class="col-sm-2 control-label">
                        <span>Preferred Quality</span>
                    </label>
                    <div class="col-sm-10 content">
                        <quality-chooser @update:quality:allowed="quality.allowed = $event" @update:quality:preferred="quality.preferred = $event"></quality-chooser>
                    </div>
                </div>
            </div>

            <!-- app.USE_SUBTITLES: -->
            <div v-show="config.subtitles.enabled" id="use-subtitles">
                <config-toggle-slider label="Subtitles" id="subtitles" :checked="config.subtitles.enabled" @update="selectedSubtitleEnabled = $event"
                    :explanations="['Download subtitles for this show?']">
                </config-toggle-slider>
            </div>

           <div class="form-group">
                <div class="row">
                    <label for="defaultStatus" class="col-sm-2 control-label">
                        <span>Status for previously aired episodes</span>
                    </label>
                    <div class="col-sm-10 content">
                        <select name="defaultStatus" id="defaultStatus" class="form-control form-control-inline input-sm" v-model="selectedStatus">
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
                        <select name="defaultStatusAfter" id="defaultStatusAfter" class="form-control form-control-inline input-sm" v-model="selectedStatusAfter">
                            <option v-for="option in defaultEpisodeStatusOptions" :value="option.value" :key="option.value">{{ option.text }}</option>
                        </select>
                    </div>
                </div>
            </div>

            <config-toggle-slider label="Season Folders" id="season_folders" :checked="defaultConfig.seasonFolders"
                :explanations="['Group episodes by season folder?']" @update="selectedSeasonFolderEnabled = $event">
            </config-toggle-slider>

            <config-toggle-slider label="Anime" id="anime" :checked="defaultConfig.anime"
                :explanations="['Is this show an Anime?']" @update="selectedAnimeEnabled = $event">
            </config-toggle-slider>

            <div v-show="enableAnimeOptions && selectedAnimeEnabled" class="form-group">
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

            <config-toggle-slider label="Scene Numbering" id="scene" :checked="defaultConfig.scene"
                :explanations="['Is this show scene numbered?']" @update="selectedSceneEnabled = $event">
            </config-toggle-slider>

            <div class="form-group">
                <div class="row">
                    <label for="saveDefaultsButton" class="col-sm-2 control-label">
                        <span>Use current values as the defaults</span>
                    </label>
                    <div class="col-sm-10 content">
                        <input class="btn-medusa btn-inline" type="button" id="saveDefaultsButton" value="Save Defaults" disabled="disabled" />
                    </div>
                </div>
            </div>
        </fieldset>
    </div>
</template>
<script>

import ConfigToggleSlider from './config-toggle-slider.vue';
import AnidbReleaseGroupUi from './anidb-release-group-ui.vue';

export default {
    name: 'add-show-options',
    components: {
        AnidbReleaseGroupUi,
        ConfigToggleSlider
    },
    props: ['selectedShow'],
    data() {
        return {
            enableAnimeOptions: true,
            useSubtitles: false,
            defaultEpisodeStatusOptions: [
                { text: 'Wanted', value: 'Wanted' },
                { text: 'Skipped', value: 'Skipped' },
                { text: 'Ignored', value: 'Ignored' }
            ],
            release: {
                blacklist: [],
                whitelist: [],
                allgroups: []
            },
            show: '',
            selectedSubtitleEnabled: false,
            selectedStatus: '',
            selectedStatusAfter: '',
            selectedSeasonFolderEnabled: false,
            selectedAnimeEnabled: false,
            selectedSceneEnabled: false,
            quality: {
                allowed: [],
                preferred: []
            },
            defaultOptions: null
        };
    },
    mounted() {
        const { selectedShow, defaultConfig, update } = this;
        this.show = selectedShow;
        this.selectedStatus = defaultConfig.status;
        this.selectedStatusAfter = defaultConfig.statusAfter;
        this.$nextTick(() => update());
    },
    methods: {
        getReleaseGroups(showName) {
            const params = {
                'series_name': showName // eslint-disable-line quote-props
            };

            try {
                return apiRoute.get('home/fetch_releasegroups', { params, timeout: 30000 }).then(res => res.data);
            } catch (error) {
                console.warn(error);
                return '';
            }
        },
        update() {
            const {
                selectedSubtitleEnabled,
                selectedStatus,
                selectedStatusAfter,
                selectedSeasonFolderEnabled,
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
                    seasonFolder: selectedSeasonFolderEnabled,
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
        }
    },
    computed: {
        header() {
            return this.$route.meta.header;
        },
        releaseGroups() {
            if (!this.show) {
                return;
            }

            return this.getReleaseGroups(this.show).then(result => {
                if (result.groups) {
                    return result.groups;
                }
            });
        },
        /**
         * Map the vuex state config.default on defaulConfig so we can watch it.
         * @returns {Object} config.default from state.
         */
        defaultConfig() {
            return this.config.default;
        },
        selectedShowName() {
            if (this.selectedShow) {
                return this.selectedShow.showName;
            }
            return '';
        }
    },
    watch: {
        selectedShowName() {
            const { selectedShowName } = this;
            this.show = selectedShowName;
            if (this.releaseGroups) {
                this.releaseGroups.then(groups => {
                    if (groups) {
                        this.release.allgroups = groups;
                    }
                });
            }
        },
        /**
         * Whenever something changes that can impact the hight of the component, we need to update the parent formWizard.
         * And make it resize.
         */
        release: {
            handler() {
                this.$emit('refresh');
                this.update();
            },
            deep: true
        },
        selectedAnimeEnabled() {
            this.$emit('refresh');
            this.update();
        },
        selectedStatus() {
            this.update();
        },
        selectedStatusAfter() {
            this.update();
        },
        selectedSeasonFolderEnabled() {
            this.update();
        },
        selectedSceneEnabled() {
            this.update();
        },
        selectedShow(newValue) {
            this.show = newValue;
        },
        defaultConfig(newValue) {
            this.selectedStatus = newValue.status;
            this.selectedStatusAfter = newValue.statusAfter;
        }
    }
};
</script>
<style>
/* placeholder */
</style>
