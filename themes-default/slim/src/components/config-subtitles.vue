<template>
    <div id="config">
        <div id="config-content">
            <form id="configForm" action="config/subtitles/saveSubtitles" method="post" @submit.prevent="save">

                <vue-tabs>
                    <v-tab key="subtitles_search" title="Subtitles Search">
                        <div id="subtitles-search" class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Subtitles Search</h3>
                                <p>Settings that dictate how Medusa handles subtitles search results.</p>
                            </div>
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">
                                    <config-toggle-slider v-model="subtitles.enabled" label="Search Subtitles" id="search_subtitles">
                                        <p>Search subtitles for episodes with DOWNLOADED status</p>
                                    </config-toggle-slider>

                                    <template v-if="subtitles.enabled">
                                        <config-template label="Subtitle Languages" labelFor="wanted_languages">
                                            <config-subtitle-languages id="wanted_languages" :languages="subtitles.wantedLanguages"
                                                                       @change="subtitles.languages = $event.map(tag => tag.text)"
                                            />
                                        </config-template>

                                        <config-toggle-slider v-model="subtitles.stopAtFirst" label="Download only one language (any)" id="subtitles_stop_at_first">
                                            <p>Stop downloading subtitles after first download</p>
                                        </config-toggle-slider>

                                        <config-toggle-slider v-model="subtitles.eraseCache" label="Erase subtitles cache on next boot" id="subtitles_erase_cache">
                                            <p>Erases all subtitles cache files. May fix some subtitles not being found</p>
                                        </config-toggle-slider>

                                        <config-textbox v-model="subtitles.location" label="Subtitle Directory" id="subtitles_dir">
                                            <span>The directory where Medusa should store your <i>Subtitles</i> files.</span>
                                            <span><b>Note:</b> Leave empty if you want store subtitle in episode path.</span>
                                        </config-textbox>

                                        <config-textbox-number v-model="subtitles.finderFrequency" :min="1" :step="1"
                                                               label="Subtitle Find Frequency" id="subtitles_finder_frequency">
                                            <span>time in hours between scans (default: 1)</span>
                                        </config-textbox-number>

                                        <config-toggle-slider v-model="subtitles.perfectMatch" label="Perfect matches" id="subtitles_perfect_match">
                                            <p>Only download subtitles that match release group</p>
                                            <p>If disabled you may get out of sync subtitles</p>
                                        </config-toggle-slider>

                                        <config-toggle-slider v-model="subtitles.logHistory" label="Subtitles History" id="subtitles_history">
                                            <p>Log downloaded Subtitle on History page?</p>
                                        </config-toggle-slider>

                                        <config-toggle-slider v-model="subtitles.multiLanguage" label="Subtitles Multi-Language" id="subtitles_multi">
                                            <p>Append language codes to subtitle filenames?</p>
                                            <span><b>Note:</b> This option is required if you use multiple subtitle languages.</span>
                                        </config-toggle-slider>

                                        <config-toggle-slider v-model="subtitles.keepOnlyWanted" label="Delete unwanted subtitles" id="subtitles_keep_only_wanted">
                                            <p>Enable to delete unwanted subtitle languages bundled with release</p>
                                            <p>Avoid post-process releases with unwanted language subtitles when feature 'postpone if no subs' is enabled</p>
                                        </config-toggle-slider>

                                        <config-toggle-slider v-model="subtitles.ignoreEmbeddedSubs" label="Embedded Subtitles" id="embedded_subtitles_all">
                                            <p>Ignore subtitles embedded inside video file?</p>
                                            <p><b>Warning: </b>this will ignore <em>all</em> embedded subtitles for every video file!</p>
                                        </config-toggle-slider>

                                        <config-toggle-slider v-model="subtitles.acceptUnknownEmbeddedSubs" label="Unknown language" id="embedded_subtitles_unknown_lang">
                                            <p>Consider unknown embedded subtitles as wanted language to avoid postponing the post-processor</p>
                                            <p>Only works with setting 'Postpone post-processing' enabled</p>
                                        </config-toggle-slider>

                                        <config-toggle-slider v-model="subtitles.hearingImpaired" label="Hearing Impaired Subtitles" id="subtitles_hearing_impaired">
                                            <p>Download hearing impaired style subtitles?</p>
                                        </config-toggle-slider>

                                        <config-template label-for="subtitles_pre_scripts" label="Pre-Scripts">
                                            <select-list name="subtitles_pre_scripts" id="subtitles_pre_scripts" :list-items="subtitles.preScripts" @change="subtitles.preScripts = $event.map(x => x.value)" />
                                            <p>Show's media filename is passed as argument for the pre-scripts. Pre-scripts are executed before trying to find subtitles from usual sources.</p>
                                        </config-template>

                                        <config-template label-for="subtitles_pre_scripts" label="Extra Scripts">
                                            <select-list name="subtitles_pre_scripts" id="subtitles_pre_scripts" :list-items="subtitles.extraScripts" @change="subtitles.extraScripts = $event.map(x => x.value)" />
                                            <ul class="extra-scripts">
                                                <li>See the <app-link :href="subtitles.wikiUrl" class="wiki"><strong>Wiki</strong></app-link> for a script arguments description.</li>
                                                <li>Additional scripts separated by <b>|</b>.</li>
                                                <li>Scripts are called after each episode has searched and downloaded subtitles.</li>
                                                <li>Only Python scripts are allowed to be executed.</li>
                                            </ul>
                                        </config-template>
                                    </template>
                                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes">
                                </fieldset>

                            </div>
                        </div><!-- /component-group1 //-->
                    </v-tab>

                    <v-tab key="subtitles_plugin" title="Subtitles Plugin">
                        <div id="subtitles-plugin" class="row component-group">
                            <div class="col-xs-12 col-md-2 component-group-desc">
                                <h3>Subtitle Providers</h3>
                                <p>Check off and drag the plugins into the order you want them to be used.</p>
                                <p class="note">At least one plugin is required.</p>
                            </div>

                            <div class="col-xs-12 col-md-10">
                                <draggable id="service_order_list" tag="ul" v-model="subtitles.services" class="list-group" handle=".ui-state-default">
                                    <li v-for="service in subtitles.services" :key="service.name" class="ui-state-default" :id="service.name">
                                        <input v-model="service.enabled" type="checkbox" :id="`enable_${service.name}`" :checked="service.enabled">
                                        <app-link :href="service.url" class="imgLink">
                                            <img :src="`images/subtitles/${service.image}`" :alt="service.url" :title="service.url" width="16" height="16" style="vertical-align: middle;">
                                        </app-link>
                                        <span style="vertical-align: middle;">{{service.name | capitalize}}</span>
                                        <span class="ui-icon ui-icon-arrowthick-2-n-s pull-right" style="vertical-align:middle;" />
                                    </li>
                                </draggable>
                                <br><input type="submit" class="btn-medusa config_submitter" value="Save Changes"><br>
                            </div>
                        </div><!-- /component-group2 //-->

                    </v-tab>

                    <v-tab key="plugin_settings" title="Plugin Settings">
                        <div id="plugin-settings" class="row component-group">
                            <div class="col-xs-12 col-md-2 component-group-desc">
                                <h3>Provider Settings</h3>
                                <p>Set user and password for each provider.</p>
                            </div><!-- /component-group-desc-legacy //-->

                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list" style="margin-left: 50px; margin-top:36px;">
                                    <config-textbox v-model="subtitles.providerLogins.addic7ed.user" label="Addic7ed User ID" id="addic7ed_username" />
                                    <div v-if="subtitles.providerLogins.addic7ed.user" style="margin-bottom: 4rem;">
                                        <p style="color: red">To bypass addic7ed captcha protection we authenticate using a set cookie. The cookie requires your user id and password.</p>
                                        <span>You can find your user id by following these steps</span>
                                        <ul>
                                            <li>Navigate and login on addic7ed.com</li>
                                            <li>Click on My Profile</li>
                                            <li>Click on your own username</li>
                                            <li>Your user id should now be visible in the address bar</li>
                                            <li>For example: https://www.addic7ed.com/user/12345</li>
                                        </ul>
                                    </div>
                                    <config-textbox type="password" v-model="subtitles.providerLogins.addic7ed.pass" label="Addic7ed Password" id="addic7ed_password" />

                                    <config-textbox v-model="subtitles.providerLogins.opensubtitles.user" label="Opensubtitles User Name" id="opensubtitles_username" />
                                    <config-textbox type="password" v-model="subtitles.providerLogins.opensubtitles.pass" label="Opensubtitles Password" id="opensubtitles_password" />

                                    <config-textbox v-model="subtitles.providerLogins.legendastv.user" label="Legendastv User Name" id="legandas_username" />
                                    <config-textbox type="password" v-model="subtitles.providerLogins.legendastv.pass" label="Legendastv Password" id="legandas_password" />

                                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes"><br>
                                </fieldset>
                            </div>
                        </div><!-- /component-group3 //-->
                    </v-tab>
                </vue-tabs>
            </form>
        </div>
    </div>
</template>
<script>
import { mapActions, mapState } from 'vuex';
import {
    AppLink,
    ConfigSubtitleLanguages,
    ConfigTemplate,
    ConfigTextbox,
    ConfigTextboxNumber,
    ConfigToggleSlider,
    SelectList
} from './helpers';
import Draggable from 'vuedraggable';
import { VueTabs, VTab } from 'vue-nav-tabs/dist/vue-tabs.js';

export default {
    name: 'config-subtitles',
    components: {
        AppLink,
        Draggable,
        ConfigSubtitleLanguages,
        ConfigTemplate,
        ConfigTextbox,
        ConfigTextboxNumber,
        ConfigToggleSlider,
        SelectList,
        VueTabs,
        VTab
    },
    data() {
        return {
            saving: false
        };
    },
    methods: {
        ...mapActions([
            'setConfig'
        ]),
        async save() {
            const { subtitles, setConfig } = this;

            // Disable the save button until we're done.
            this.saving = true;
            const section = 'main';

            // Remove codeFilter key from object.
            const { codeFilter, wantedLanguages, ...rest } = subtitles;

            try {
                await setConfig({ section, config: { subtitles: rest } });
                this.$snotify.success(
                    'Saved Subtitles config',
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to save subtitles config',
                    'Error'
                );
            } finally {
                this.saving = false;
            }
        }
    },
    computed: {
        ...mapState({
            subtitles: state => state.config.subtitles,
            layout: state => state.config.layout
        })
    },
    filters: {
        capitalize: str => str.replace(/\b\w/g, str => str.toUpperCase())
    }
};
</script>
<style>
ul.extra-scripts {
    padding: 0;
    margin-left: 15px;
}
</style>
