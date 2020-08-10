<template>
    <div id="config">
        <div id="config-content">
            <form id="configForm" method="post" @submit.prevent="save()">
                <div id="config-components">
                    <vue-tabs>
                        <v-tab key="anidb_settings" title="AnimeDB Settings">
                            <div class="row component-group">
                                <div class="component-group-desc col-xs-12 col-md-2">
                                    <span class="icon-notifiers-anime" title="AniDB" />
                                    <h3>
                                        <app-link href="http://anidb.info">AniDB</app-link>
                                    </h3>
                                    <p>AniDB is non-profit database of anime information that is freely open to the public</p>
                                </div>
                                <div class="col-xs-12 col-md-10">
                                    <fieldset class="component-group-list">
                                        <config-toggle-slider v-model="anime.anidb.enabled" label="Use AniDB" id="use_anidb">
                                            <span class="component-title">Enable</span>
                                            <span class="component-desc">Should Medusa use data from AniDB?</span>
                                        </config-toggle-slider>

                                        <div v-if="anime.anidb.enabled" id="content_use_anidb">
                                            <config-textbox v-model="anime.anidb.username" label="AniDB Username" id="anidb_username">
                                                <span class="component-desc">Username of your AniDB account</span>
                                            </config-textbox>

                                            <config-textbox v-model="anime.anidb.password" label="AniDB Password" id="anidb_password">
                                                <span class="component-desc">Password of your AniDB account</span>
                                            </config-textbox>

                                            <config-toggle-slider v-model="anime.anidb.useMyList" label="AniDB MyList" id="anidb_use_my_list">
                                                <span class="component-title">AniDB MyList</span>
                                                <span class="component-desc">Do you want to add the PostProcessed Episodes to the MyList ?</span>
                                            </config-toggle-slider>

                                        </div><!-- #content_use_anidb //-->
                                        <input type="submit" class="btn-medusa config_submitter" value="Save Changes">
                                    </fieldset><!-- .component-group-list //-->
                                </div>
                            </div>
                        </v-tab>

                        <v-tab>
                            <div class="row component-group">
                                <div class="component-group-desc col-xs-12 col-md-2">
                                    <span class="icon-notifiers-look" title="look" />
                                    <h3><a>Look and Feel</a></h3>
                                    <p>How should the anime functions show and behave.</p>
                                </div>
                                <div class="col-xs-12 col-md-10">
                                    <fieldset class="component-group-list">
                                        <config-toggle-slider v-model="anime.autoAnimeToList" label="Connect anime to Anime list" id="auto_anime_to_list">
                                            <span class="component-desc">Connect every show marked as anime, to the 'Anime' show list?</span>
                                        </config-toggle-slider>

                                        <input type="submit" class="btn-medusa config_submitter" value="Save Changes">
                                    </fieldset><!-- .component-group-list //-->
                                </div>
                            </div><!-- .component-group-desc-legacy //-->
                        </v-tab>
                    </vue-tabs>
                </div><!-- #config-components //-->
            </form><!-- #configForm //-->
        </div><!-- #config-content //-->
    </div><!-- #config //-->
</template>
<script>
import { mapActions, mapState } from 'vuex';
import { AppLink, ConfigTextbox, ConfigToggleSlider } from './helpers';
import { VueTabs, VTab } from 'vue-nav-tabs/dist/vue-tabs.js';

export default {
    name: 'config-post-processing',
    components: {
        AppLink,
        ConfigTextbox,
        ConfigToggleSlider,
        VueTabs,
        VTab
    },
    data() {
        return {
        };
    },
    methods: {
        ...mapActions([
            'setConfig'
        ]),
        async save() {
            // const { postprocessing, metadata, setConfig } = this;
            // // We want to wait until the page has been fully loaded, before starting to save stuff.
            // if (!this.configLoaded) {
            //     return;
            // }
            // // Disable the save button until we're done.
            // this.saving = true;

            // // Clone the config into a new object
            // const config = Object.assign({}, {
            //     postProcessing: postprocessing,
            //     metadata
            // });

            // // Use destructuring to remove the unwanted keys.
            // const { multiEpStrings, reflinkAvailable, extraScriptsUrl, ...rest } = postprocessing;
            // // Assign the object with the keys removed to our copied object.
            // config.postProcessing = rest;

            // const section = 'main';

            // try {
            //     await setConfig({ section, config });
            //     this.$snotify.success(
            //         'Saved Post-Processing config',
            //         'Saved',
            //         { timeout: 5000 }
            //     );
            // } catch (error) {
            //     this.$snotify.error(
            //         'Error while trying to save Post-Processing config',
            //         'Error'
            //     );
            // } finally {
            //     this.saving = false;
            // }
        }
    },
    computed: {
        ...mapState({
            anime: state => state.config.anime
        })
    }
};
</script>
<style>
</style>
