<template>
    <div id="config">
        <div id="config-content">
            <form id="configForm" method="post" @submit.prevent="save()">
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
                                        <span>Should Medusa use data from AniDB?</span>
                                    </config-toggle-slider>

                                    <div v-if="anime.anidb.enabled" id="content_use_anidb">
                                        <config-textbox v-model="anime.anidb.username" label="AniDB Username" id="anidb_username">
                                            <span>Username of your AniDB account</span>
                                        </config-textbox>

                                        <config-textbox v-model="anime.anidb.password" label="AniDB Password" id="anidb_password">
                                            <span>Password of your AniDB account</span>
                                        </config-textbox>

                                        <config-toggle-slider v-model="anime.anidb.useMyList" label="AniDB MyList" id="anidb_use_my_list">
                                            <span>Do you want to add the PostProcessed Episodes to the MyList ?</span>
                                        </config-toggle-slider>

                                    </div><!-- #content_use_anidb //-->
                                    <input type="submit"
                                           class="btn-medusa config_submitter"
                                           value="Save Changes"
                                           :disabled="saving"
                                    >
                                </fieldset><!-- .component-group-list //-->
                            </div>
                        </div>
                    </v-tab>

                    <v-tab key="look_and_feel" title="Look &amp; Feel">
                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <span class="icon-notifiers-look" title="look" />
                                <h3><a>Look and Feel</a></h3>
                                <p>How should the anime functions show and behave.</p>
                            </div>
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">
                                    <config-toggle-slider v-model="anime.autoAnimeToList" label="Connect anime to Anime list" id="auto_anime_to_list">
                                        <span>Connect every show marked as anime, to the 'Anime' show list?</span>
                                    </config-toggle-slider>

                                    <config-template v-if="anime.autoAnimeToList" label-for="showlist_default_anime" label="Showlists for Anime">
                                        <multiselect
                                            v-model="animeShowlistDefaultAnime"
                                            :multiple="true"
                                            :options="layout.show.showListOrder"
                                        />
                                        <span>Customize the showslist when auto anime lists is enabled</span>
                                    </config-template>

                                    <input type="submit"
                                           class="btn-medusa config_submitter"
                                           value="Save Changes"
                                           :disabled="saving"
                                           @click="save"
                                    >
                                </fieldset><!-- .component-group-list //-->
                            </div>
                        </div><!-- row component-group //-->
                    </v-tab>
                </vue-tabs>
            </form><!-- #configForm //-->
        </div><!-- #config-content //-->
    </div><!-- #config //-->
</template>
<script>
import { mapActions, mapState } from 'vuex';
import { AppLink, ConfigTemplate, ConfigTextbox, ConfigToggleSlider } from './helpers';
import { VueTabs, VTab } from 'vue-nav-tabs/dist/vue-tabs.js';
import Multiselect from 'vue-multiselect';
import 'vue-multiselect/dist/vue-multiselect.min.css';

export default {
    name: 'config-anime',
    components: {
        AppLink,
        ConfigTemplate,
        ConfigTextbox,
        ConfigToggleSlider,
        Multiselect,
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
            'setConfig',
            'updateShowlistDefault'
        ]),
        async save() {
            const { anime, setConfig } = this;

            // Disable the save button until we're done.
            this.saving = true;
            const section = 'main';

            try {
                await setConfig({ section, config: { anime } });
                this.$snotify.success(
                    'Saved Anime config',
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to save anime config',
                    'Error'
                );
            } finally {
                this.saving = false;
            }
        }
    },
    computed: {
        ...mapState({
            anime: state => state.config.anime,
            layout: state => state.config.layout
        }),
        animeShowlistDefaultAnime: {
            get() {
                const { anime } = this;
                return anime.showlistDefaultAnime;
            },
            set(value) {
                const { anime, updateShowlistDefault } = this;
                updateShowlistDefault(value, anime.showlistDefaultAnime);
            }
        }
    }
};
</script>
<style>
</style>
