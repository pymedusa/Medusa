<template>
    <div id="config" class="row">
        <div class="col-md-12">
            <app-link href="manage">
                <svg class="back-arrow"><use xlink:href="images/svg/go-back-arrow.svg#arrow" /></svg>
            </app-link>
            <h3>Main Settings</h3>
            <em class="note"><b>Note:</b> Changing any settings marked with (<span class="separator">*</span>) will force a refresh of the selected shows.</em>

            <fieldset class="component-group-list">
                <config-template label-for="selected_shows" label="Selected Shows" class="field-pair">
                    <span v-for="show in shows" :key="show.id.slug" class="title" style="font-size: 14px;">{{show.name}}</span><br>
                </config-template>

                <config-template>
                    <template v-slot:label>
                        Root Directories (<span class="separator">*</span>)
                    </template>
                    <edit-root-dirs :root-dirs="setRootDirs" @update="config.rootDirs = $event" />
                </config-template>

                <config-template label-for="qualityPreset" label="Quality">
                    <quality-chooser
                        v-if="general.showDefaults.quality !== null"
                        :keep="config.qualities.allowed.length === 0 && config.qualities.preferred.length === 0 ? 'keep' : 'show'"
                        :overall-quality="combinedQualities"
                        @update:quality:allowed="config.qualities.allowed = $event"
                        @update:quality:preferred="config.qualities.preferred = $event"
                    />
                </config-template>

                <config-template>
                    <template v-slot:label>
                        Season folders (<span class="separator">*</span>)
                    </template>
                    <select v-model="config.seasonFolders" id="season_folders" name="season_folders" class="form-control form-control-inline input-sm">
                        <option :value="null">&lt; Keep &gt;</option>
                        <option :value="true">Yes</option>
                        <option :value="false">No</option>
                    </select>
                </config-template>

                <config-template label="Paused">
                    <select v-model="config.paused" id="edit_paused" name="paused" class="form-control form-control-inline input-sm">
                        <option :value="null">&lt; Keep &gt;</option>
                        <option :value="true">Yes</option>
                        <option :value="false">No</option>
                    </select><br>
                    Pause these shows (Medusa will not download episodes).
                </config-template>

                <config-template label="Default Episode Status">
                    <select v-model="config.defaultEpisodeStatus" id="edit_default_ep_status" name="default_ep_status" class="form-control form-control-inline input-sm">
                        <option :value="null">&lt; Keep &gt;</option>
                        <option value="Wanted">Wanted</option>
                        <option value="Skipped">Skipped</option>
                        <option value="Ignored">Ignored</option>
                    </select><br>
                    This will set the status for future episodes.
                </config-template>

                <config-template label="Scene Numbering">
                    <select v-model="config.scene" id="edit_scene" name="scene" class="form-control form-control-inline input-sm">
                        <option :value="null">&lt; Keep &gt;</option>
                        <option :value="true">Yes</option>
                        <option :value="false">No</option>
                    </select>
                    <p>Search by scene numbering (set to "No" to search by indexer numbering).</p>
                </config-template>

                <config-template label="Anime">
                    <select v-model="config.anime" id="edit_anime" name="anime" class="form-control form-control-inline input-sm">
                        <option :value="null">&lt; Keep &gt;</option>
                        <option :value="true">Yes</option>
                        <option :value="false">No</option>
                    </select>
                    <p>Set if these shows are Anime and episodes are released as Show.265 rather than Show.S02E03</p>
                </config-template>

                <config-template label="Sports">
                    <select v-model="config.sports" id="edit_sports" name="sports" class="form-control form-control-inline input-sm">
                        <option :value="null">&lt; Keep &gt;</option>
                        <option :value="true">Yes</option>
                        <option :value="false">No</option>
                    </select>
                    <p>Set if these shows are sporting or MMA events released as Show.03.02.2010 rather than Show.S02E03.<br>
                        <span style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</span>
                    </p>
                </config-template>

                <config-template label="Air by date">
                    <select v-model="config.airByDate" id="edit_air_by_date" name="air_by_date" class="form-control form-control-inline input-sm">
                        <option :value="null">&lt; Keep &gt;</option>
                        <option :value="true">Yes</option>
                        <option :value="false">No</option>
                    </select>
                    <p>Set if these shows are released as Show.03.02.2010 rather than Show.S02E03.<br>
                        <span style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</span>
                    </p>
                </config-template>

                <config-template label="Dvd order">
                    <select v-model="config.dvdOrder" id="edit_dvd_order" name="dvd_order" class="form-control form-control-inline input-sm">
                        <option :value="null">&lt; Keep &gt;</option>
                        <option :value="true">Yes</option>
                        <option :value="false">No</option>
                    </select>
                    <p>use the DVD order instead of the air order<br>
                        <span>A "Force Full Update" is necessary, and if you have existing episodes you need to sort them manually.</span>
                    </p>
                </config-template>

                <config-template label="Subtitles">
                    <select v-model="config.subtitles" id="edit_subtitles" name="subtitles" class="form-control form-control-inline input-sm">
                        <option :value="null">&lt; Keep &gt;</option>
                        <option :value="true">Yes</option>
                        <option :value="false">No</option>
                    </select>
                    <p>Search for subtitles.</p>
                </config-template>

                <config-toggle-slider v-model="config.languageKeep" id="keep_language" label="Keep language" />
                <config-template v-if="!config.languageKeep" label-for="indexerLangSelect" label="Info Language">
                    <language-select
                        id="indexerLangSelect"
                        @update-language="config.language = $event"
                        :language="config.language"
                        :available="availableLanguages"
                        name="indexer_lang"
                        class="form-control form-control-inline input-sm"
                    />
                    <div class="clear-left"><p>This only applies to episode filenames and the contents of metadata files.</p></div>
                </config-template>
            </fieldset>
            <button class="btn-medusa config_submitter pull-left"
                    :disabled="saving"
                    @click="save"
            >Save Changes</button>
            <state-switch v-if="saving" state="loading" :theme="layout.themeName" />
        </div>
    </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import {
    AppLink,
    LanguageSelect,
    ConfigToggleSlider,
    StateSwitch,
    QualityChooser
} from './helpers';
import ConfigTemplate from './helpers/config-template.vue';
import EditRootDirs from './helpers/edit-root-dirs.vue';
import { combineQualities } from '../utils/core';

export default {
    name: 'manage-mass-edit',
    components: {
        AppLink,
        ConfigTemplate,
        ConfigToggleSlider,
        EditRootDirs,
        LanguageSelect,
        QualityChooser,
        StateSwitch
    },
    props: {
        shows: {
            type: Array,
            required: true
        }
    },
    data() {
        return {
            saving: false,
            config: {
                qualities: { allowed: [], preferred: [] },
                seasonFolders: null,
                paused: null,
                defaultEpisodeStatus: null,
                scene: null,
                anime: null,
                sports: null,
                airByDate: null,
                dvdOrder: null,
                subtitles: null,
                language: null,
                languageKeep: null,
                rootDirs: []
            }
        };
    },
    mounted() {
        const { shows } = this;
        // Helper to check if all the values in an array are equal to each other.
        const allEqual = arr => arr.every(val => val === arr[0]);

        this.config.qualities.allowed = allEqual(shows.map(show => combineQualities(show.config.qualities.allowed, show.config.qualities.preferred))) ? shows[0].config.qualities.allowed : [];
        this.config.qualities.preferred = allEqual(shows.map(show => combineQualities(show.config.qualities.allowed, show.config.qualities.preferred))) ? shows[0].config.qualities.preferred : [];
        this.config.seasonFolders = allEqual(shows.map(show => show.config.seasonFolders)) ? shows[0].config.seasonFolders : null;
        this.config.paused = allEqual(shows.map(show => show.config.paused)) ? shows[0].config.paused : null;
        this.config.defaultEpisodeStatus = allEqual(shows.map(show => show.config.defaultEpisodeStatus)) ? shows[0].config.defaultEpisodeStatus : null;
        this.config.scene = allEqual(shows.map(show => show.config.scene)) ? shows[0].config.scene : null;
        this.config.anime = allEqual(shows.map(show => show.config.anime)) ? shows[0].config.anime : null;
        this.config.sports = allEqual(shows.map(show => show.config.sports)) ? shows[0].config.sports : null;
        this.config.airByDate = allEqual(shows.map(show => show.config.airByDate)) ? shows[0].config.airByDate : null;
        this.config.dvdOrder = allEqual(shows.map(show => show.config.dvdOrder)) ? shows[0].config.dvdOrder : null;
        this.config.subtitles = allEqual(shows.map(show => show.config.subtitlesEnabled)) ? shows[0].config.subtitlesEnabled : null;
        this.config.rootDirs = this.setRootDirs.map(rd => ({ old: rd, new: rd }));
        this.config.language = shows[0].language;
        this.config.languageKeep = !allEqual(shows.map(show => show.language));
    },
    computed: {
        ...mapState({
            general: state => state.config.general,
            layout: state => state.config.layout,
            client: state => state.auth.client,
            indexers: state => state.config.indexers
        }),
        setRootDirs() {
            return [...new Set(this.shows.map(show => show.config.rootDir))];
        },
        combinedQualities() {
            const { config } = this;
            const { qualities } = config;
            if (qualities.allowed === null || qualities.preferred === null) {
                return 0;
            }
            return combineQualities(qualities.allowed, qualities.preferred);
        },
        availableLanguages() {
            if (this.indexers.main.validLanguages) {
                return this.indexers.main.validLanguages.join(',');
            }

            return '';
        }
    },
    methods: {
        ...mapActions(['getShow']),
        async save() {
            const { client, shows, config } = this;
            try {
                this.saving = true;
                const { data } = await client.api.post('massedit', {
                    shows: shows.map(s => s.id.slug), options: config
                }, { timeout: 20000 });
                if (data && data.errors > 0) {
                    this.$snotify.success(
                        `Mass edited shows but with ${data.errors} errors`,
                        'Saved',
                        { timeout: 5000 }
                    );
                } else {
                    this.$snotify.success(
                        'Successfully mass edited shows',
                        'Saved',
                        { timeout: 2000 }
                    );
                }
            } catch (error) {
                console.log(`Error trying massedit shows: ${shows.map(s => s.name).join(', ')}`);
                this.$snotify.error(
                    'Error while trying to mass edit shows',
                    'Error'
                );
            } finally {
                this.saving = false;
                for (const show of this.shows) {
                    this.getShow({ showSlug: show.id.slug });
                }
                this.$router.push({ name: 'manage' });
            }
        }
    }
};
</script>

<style scoped>
svg.back-arrow {
    width: 20px;
    height: 20px;
    float: left;
    margin-right: 1em;
    cursor: pointer;
}

svg.back-arrow:hover {
    transform: translateX(-2px);
    transition: transform ease-in-out 0.2s;
}

span.title {
    margin: 0 3px;
    background-color: rgb(245, 241, 228);
    border-radius: 5px;
    padding: 1px 5px;
    color: black;
    font-weight: 500;
    word-break: break-all;
    margin-bottom: 4px;
    float: left;
}
</style>
