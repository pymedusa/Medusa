<template>
    <div id="config">
        <div id="config-content">
            <form id="configForm" class="form-horizontal" @submit.prevent="save()">
                <div id="config-components">
                    <ul>
                        <li><app-link href="#post-processing">Post-Processing</app-link></li>
                        <li><app-link href="#episode-naming">Episode Naming</app-link></li>
                        <li><app-link href="#metadata">Metadata</app-link></li>
                    </ul>
                    <div id="post-processing">
                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Scheduled Post-Processing</h3>
                                <p>Settings that dictate how Medusa should process completed downloads.</p>
                                <p>The scheduled post-processor will periodically scan a folder for media to process.</p>
                            </div>

                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">
                                    <div class="form-group">
                                        <label for="process_automatically" class="col-sm-2 control-label">
                                            <span>Scheduled Post-Processor</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="process_automatically" name="process_automatically" v-model="postprocessing.processAutomatically" sync />
                                            <p>Enable the scheduled post-processor to scan and process any files in your <i>Post-Processing Dir</i>?</p>
                                            <div class="clear-left"><p><b>Note:</b> Do not use if you use an external post-processing script</p></div>
                                        </div>
                                    </div>

                                    <div v-show="postprocessing.processAutomatically" id="post-process-toggle-wrapper">
                                        <div class="form-group">
                                            <label for="tv_download_dir" class="col-sm-2 control-label">
                                                <span>Post-Processing Dir</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <file-browser id="tv_download_dir" name="tv_download_dir" title="Select series download location" :initial-dir="postprocessing.showDownloadDir" @update="postprocessing.showDownloadDir = $event" />
                                                <span class="clear-left">The folder where your download client puts the completed TV downloads.</span>
                                                <div class="clear-left"><p><b>Note:</b> Please use separate downloading and completed folders in your download client if possible.</p></div>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="process_method" class="col-sm-2 control-label">
                                                <span>Processing Method</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <select id="naming_multi_ep" name="naming_multi_ep" v-model="postprocessing.processMethod" class="form-control input-sm">
                                                    <option :value="option.value" v-for="option in processMethods" :key="option.value">{{ option.text }}</option>
                                                </select>
                                                <span>What method should be used to put files into the library?</span>
                                                <p><b>Note:</b> If you keep seeding torrents after they finish, please avoid the 'move' processing method to prevent errors.</p>
                                                <p v-if="postprocessing.processMethod == 'reflink'">To use reference linking, the <app-link href="http://www.dereferer.org/?https://pypi.python.org/pypi/reflink/0.1.4">reflink package</app-link> needs to be installed.</p>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="autopostprocessor_frequency" class="col-sm-2 control-label">
                                                <span>Auto Post-Processing Frequency</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <input type="number" min="10" step="1" name="autopostprocessor_frequency" id="autopostprocessor_frequency" v-model.number="postprocessing.autoPostprocessorFrequency" class="form-control input-sm input75">
                                                <span>Time in minutes to check for new files to auto post-process (min 10)</span>
                                            </div>
                                        </div>
                                    </div> <!-- End of content wrapper -->
                                </fieldset>
                            </div> <!-- end of col -->
                        </div> <!-- end of row -->

                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>General Post-Processing</h3>
                                <p>Generic post-processing settings that apply both to the scheduled post-processor as external scripts</p>
                            </div>
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">
                                    <div class="form-group">
                                        <label for="postpone_if_sync_files" class="col-sm-2 control-label">
                                            <span>Postpone post-processing</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="postpone_if_sync_files" name="postpone_if_sync_files" v-model="postprocessing.postponeIfSyncFiles" sync />
                                            <span>Wait to process a folder if sync files are present.</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label for="sync_files" class="col-sm-2 control-label">
                                            <span>Sync File Extensions</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <select-list name="sync_files" id="sync_files" csv-enabled :list-items="postprocessing.syncFiles" @change="onChangeSyncFiles" />
                                            <span>Comma separated list of extensions or filename globs Medusa ignores when post-processing</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label for="postpone_if_no_subs" class="col-sm-2 control-label">
                                            <span>Postpone if no subtitle</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="postpone_if_no_subs" name="postpone_if_no_subs" v-model="postprocessing.postponeIfNoSubs" sync />
                                            <span>Wait to process a file until subtitles are present</span><br>
                                            <span>Language names are allowed in subtitle filename (en.srt, pt-br.srt, ita.srt, etc.)</span><br>
                                            <span><b>Note:</b> Automatic post-processor should be disabled to avoid files with pending subtitles being processed over and over.</span><br>
                                            <span>If you have any active show with subtitle search disabled, you must enable Automatic post-processor.</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label for="rename_episodes" class="col-sm-2 control-label">
                                            <span>Rename Episodes</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="rename_episodes" name="rename_episodes" v-model="postprocessing.renameEpisodes" sync />
                                            <span>Rename episode using the Episode Naming settings?</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label for="create_missing_show_dirs" class="col-sm-2 control-label">
                                            <span>Create missing show directories</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="create_missing_show_dirs" name="create_missing_show_dirs" v-model="postprocessing.createMissingShowDirs" sync />
                                            <span>Create missing show directories when they get deleted</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label for="add_shows_wo_dir" class="col-sm-2 control-label">
                                            <span>Add shows without directory</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="add_shows_wo_dir" name="add_shows_wo_dir" v-model="postprocessing.addShowsWithoutDir" sync />
                                            <span>Add shows without creating a directory (not recommended)</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label for="move_associated_files" class="col-sm-2 control-label">
                                            <span>Delete associated files</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="move_associated_files" name="move_associated_files" v-model="postprocessing.moveAssociatedFiles" sync />
                                            <span>Delete srt/srr/sfv/etc files while post-processing?</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label class="col-sm-2 control-label">
                                            <span>Keep associated file extensions</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <select-list name="allowed_extensions" id="allowed_extensions" csv-enabled :list-items="postprocessing.allowedExtensions" @change="onChangeAllowedExtensions" />
                                            <span>Comma separated list of associated file extensions Medusa should keep while post-processing.</span><br>
                                            <span>Leaving it empty means all associated files will be deleted</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label for="nfo_rename" class="col-sm-2 control-label">
                                            <span>Rename .nfo file</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="nfo_rename" name="nfo_rename" v-model="postprocessing.nfoRename" sync />
                                            <span>Rename the original .nfo file to .nfo-orig to avoid conflicts?</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label for="airdate_episodes" class="col-sm-2 control-label">
                                            <span>Change File Date</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="airdate_episodes" name="airdate_episodes" v-model="postprocessing.airdateEpisodes" sync />
                                            <span>Set last modified filedate to the date that the episode aired?</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label for="file_timestamp_timezone" class="col-sm-2 control-label">
                                            <span>Timezone for File Date:</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <select id="file_timestamp_timezone" name="file_timestamp_timezone" v-model="postprocessing.fileTimestampTimezone" class="form-control input-sm">
                                                <option :value="option.value" v-for="option in timezoneOptions" :key="option.value">{{ option.text }}</option>
                                            </select>
                                            <span>What timezone should be used to change File Date?</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label for="unpack" class="col-sm-2 control-label">
                                            <span>Unpack</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="unpack" name="unpack" v-model="postprocessing.unpack" sync />
                                            <span>Unpack any TV releases in your <i>TV Download Dir</i>?</span><br>
                                            <span><b>Note:</b> Only working with RAR archive</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label for="del_rar_contents" class="col-sm-2 control-label">
                                            <span>Delete RAR contents</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="del_rar_contents" name="del_rar_contents" v-model="postprocessing.deleteRarContent" sync />
                                            <span>Delete content of RAR files, even if Process Method not set to move?</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label for="no_delete" class="col-sm-2 control-label">
                                            <span>Don't delete empty folders</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="no_delete" name="no_delete" v-model="postprocessing.noDelete" sync />
                                            <span>Leave empty folders when post-processing?</span><br>
                                            <span><b>Note:</b> Can be overridden using manual post-processing</span>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <label class="col-sm-2 control-label">
                                            <span>Extra Scripts</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <select-list name="extra_scripts" id="extra_scripts" csv-enabled :list-items="postprocessing.extraScripts" @change="onChangeExtraScripts" />
                                            <span>See <app-link :href="postprocessing.extraScriptsUrl" class="wikie"><strong>Wiki</strong></app-link> for script arguments description and usage.</span>
                                        </div>
                                    </div>
                                </fieldset>
                                <input type="submit"
                                       class="btn-medusa config_submitter"
                                       value="Save Changes"
                                       :disabled="saving"
                                >
                            </div> <!-- /col -->
                        </div> <!-- /row -->
                    </div><!-- /component-group1 //-->

                    <div id="episode-naming">
                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Episode Naming</h3>
                                <p>How Medusa will name and sort your episodes.</p>
                            </div>

                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">

                                    <!-- default name-pattern component -->
                                    <name-pattern
                                        class="component-item" :naming-pattern="postprocessing.naming.pattern"
                                        :naming-presets="presets" :multi-ep-style="postprocessing.naming.multiEp"
                                        :multi-ep-styles="multiEpStringsSelect" @change="saveNaming" :flag-loaded="configLoaded"
                                    />

                                    <!-- default sports name-pattern component -->
                                    <name-pattern
                                        class="component-item" :enabled="postprocessing.naming.enableCustomNamingSports"
                                        :naming-pattern="postprocessing.naming.patternSports" :naming-presets="presets" type="sports"
                                        :enabled-naming-custom="postprocessing.naming.enableCustomNamingSports" @change="saveNamingSports" :flag-loaded="configLoaded"
                                    />

                                    <!-- default airs by date name-pattern component -->
                                    <name-pattern
                                        class="component-item" :enabled="postprocessing.naming.enableCustomNamingAirByDate"
                                        :naming-pattern="postprocessing.naming.patternAirByDate" :naming-presets="presets" type="airs by date"
                                        :enabled-naming-custom="postprocessing.naming.enableCustomNamingAirByDate" @change="saveNamingAbd" :flag-loaded="configLoaded"
                                    />

                                    <!-- default anime name-pattern component -->
                                    <name-pattern
                                        class="component-item" :enabled="postprocessing.naming.enableCustomNamingAnime"
                                        :naming-pattern="postprocessing.naming.patternAnime" :naming-presets="presets" type="anime" :multi-ep-style="postprocessing.naming.animeMultiEp"
                                        :multi-ep-styles="multiEpStringsSelect" :anime-naming-type="postprocessing.naming.animeNamingType"
                                        :enabled-naming-custom="postprocessing.naming.enableCustomNamingAnime" @change="saveNamingAnime" :flag-loaded="configLoaded"
                                    />

                                    <div class="form-group component-item">
                                        <label for="naming_strip_year" class="col-sm-2 control-label">
                                            <span>Strip Show Year</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button
                                                :width="45" :height="22" id="naming_strip_year" name="naming_strip_year"
                                                v-model="postprocessing.naming.stripYear" sync
                                            />
                                            <span>Remove the TV show's year when renaming the file?</span>
                                            <p>Only applies to shows that have year inside parentheses</p>
                                        </div>
                                    </div>
                                </fieldset>
                            </div>
                        </div>
                    </div>

                    <div id="metadata">
                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Metadata</h3>
                                <p>The data associated to the data. These are files associated to a TV show in the form of images and text that, when supported, will enhance the viewing experience.</p>
                            </div>
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">
                                    <div class="form-group">
                                        <label for="metadataType" class="col-sm-2 control-label">
                                            <span>Metadata Type</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <select id="metadataType" name="metadataType" v-model="metadataProviderSelected" class="form-control input-sm">
                                                <option :value="option.id" v-for="option in metadata.metadataProviders" :key="option.id">{{ option.name }}</option>
                                            </select>
                                            <span class="d-block">Toggle the metadata options that you wish to be created. <b>Multiple targets may be used.</b></span>
                                        </div>
                                    </div>

                                    <div class="metadataDiv" v-show="provider.id === metadataProviderSelected" v-for="provider in metadata.metadataProviders" :key="provider.id" id="provider.id">
                                        <div class="metadata_options_wrapper">
                                            <h4>Create:</h4>
                                            <div class="metadata_options">
                                                <label :for="provider.id + '_show_metadata'"><input type="checkbox" class="metadata_checkbox" :id="provider.id + '_show_metadata'" v-model="provider.showMetadata">&nbsp;Show Metadata</label>
                                                <label :for="provider.id + '_episode_metadata'"><input type="checkbox" class="metadata_checkbox" :id="provider.id + '_episode_metadata'" v-model="provider.episodeMetadata" :disabled="provider.example.episodeMetadata.includes('not supported')">&nbsp;Episode Metadata</label>
                                                <label :for="provider.id + '_fanart'"><input type="checkbox" class="float-left metadata_checkbox" :id="provider.id + '_fanart'" v-model="provider.fanart" :disabled="provider.example.fanart.includes('not supported')">&nbsp;Show Fanart</label>
                                                <label :for="provider.id + '_poster'"><input type="checkbox" class="float-left metadata_checkbox" :id="provider.id + '_poster'" v-model="provider.poster" :disabled="provider.example.poster.includes('not supported')">&nbsp;Show Poster</label>
                                                <label :for="provider.id + '_banner'"><input type="checkbox" class="float-left metadata_checkbox" :id="provider.id + '_banner'" v-model="provider.banner" :disabled="provider.example.banner.includes('not supported')">&nbsp;Show Banner</label>
                                                <label :for="provider.id + '_episode_thumbnails'"><input type="checkbox" class="float-left metadata_checkbox" :id="provider.id + '_episode_thumbnails'" v-model="provider.episodeThumbnails" :disabled="provider.example.episodeThumbnails.includes('not supported')">&nbsp;Episode Thumbnails</label>
                                                <label :for="provider.id + '_season_posters'"><input type="checkbox" class="float-left metadata_checkbox" :id="provider.id + '_season_posters'" v-model="provider.seasonPosters" :disabled="provider.example.seasonPosters.includes('not supported')">&nbsp;Season Posters</label>
                                                <label :for="provider.id + '_season_banners'"><input type="checkbox" class="float-left metadata_checkbox" :id="provider.id + '_season_banners'" v-model="provider.seasonBanners" :disabled="provider.example.seasonBanners.includes('not supported')">&nbsp;Season Banners</label>
                                                <label :for="provider.id + '_season_all_poster'"><input type="checkbox" class="float-left metadata_checkbox" :id="provider.id + '_season_all_poster'" v-model="provider.seasonAllPoster" :disabled="provider.example.seasonAllPoster.includes('not supported')">&nbsp;Season All Poster</label>
                                                <label :for="provider.id + '_season_all_banner'"><input type="checkbox" class="float-left metadata_checkbox" :id="provider.id + '_season_all_banner'" v-model="provider.seasonAllBanner" :disabled="provider.example.seasonAllBanner.includes('not supported')">&nbsp;Season All Banner</label>
                                            </div>
                                        </div>
                                        <div class="metadata_example_wrapper">
                                            <h4>Results:</h4>
                                            <div class="metadata_example">
                                                <label :for="provider.id + '_show_metadata'"><span :id="provider.id + '_eg_show_metadata'" :class="{disabled: !provider.showMetadata}"><span v-html="'<span>' + provider.example.showMetadata + '</span>'" /></span></label>
                                                <label :for="provider.id + '_episode_metadata'"><span :id="provider.id + '_eg_episode_metadata'" :class="{disabled: !provider.episodeMetadata}"><span v-html="'<span>' + provider.example.episodeMetadata + '</span>'" /></span></label>
                                                <label :for="provider.id + '_fanart'"><span :id="provider.id + '_eg_fanart'" :class="{disabled: !provider.fanart}"><span v-html="'<span>' + provider.example.fanart + '</span>'" /></span></label>
                                                <label :for="provider.id + '_poster'"><span :id="provider.id + '_eg_poster'" :class="{disabled: !provider.poster}"><span v-html="'<span>' + provider.example.poster + '</span>'" /></span></label>
                                                <label :for="provider.id + '_banner'"><span :id="provider.id + '_eg_banner'" :class="{disabled: !provider.banner}"><span v-html="'<span>' + provider.example.banner + '</span>'" /></span></label>
                                                <label :for="provider.id + '_episode_thumbnails'"><span :id="provider.id + '_eg_episode_thumbnails'" :class="{disabled: !provider.episodeThumbnails}"><span v-html="'<span>' + provider.example.episodeThumbnails + '</span>'" /></span></label>
                                                <label :for="provider.id + '_season_posters'"><span :id="provider.id + '_eg_season_posters'" :class="{disabled: !provider.seasonPosters}"><span v-html="'<span>' + provider.example.seasonPosters + '</span>'" /></span></label>
                                                <label :for="provider.id + '_season_banners'"><span :id="provider.id + '_eg_season_banners'" :class="{disabled: !provider.seasonBanners}"><span v-html="'<span>' + provider.example.seasonBanners + '</span>'" /></span></label>
                                                <label :for="provider.id + '_season_all_poster'"><span :id="provider.id + '_eg_season_all_poster'" :class="{disabled: !provider.seasonAllPoster}"><span v-html="'<span>' + provider.example.seasonAllPoster + '</span>'" /></span></label>
                                                <label :for="provider.id + '_season_all_banner'"><span :id="provider.id + '_eg_season_all_banner'" :class="{disabled: !provider.seasonAllBanner}"><span v-html="'<span>' + provider.example.seasonAllBanner + '</span>'" /></span></label>
                                            </div>
                                        </div>
                                    </div>
                                </fieldset>
                                <input type="submit"
                                       class="btn-medusa config_submitter"
                                       value="Save Changes"
                                       :disabled="saving"
                                >

                            </div> <!-- end of col -->
                        </div> <!-- end of row -->
                    </div> <!-- end of metatdata id -->

                    <h6 class="pull-right"><b>All non-absolute folder locations are relative to <span class="path">{{system.dataDir}}</span></b> </h6>
                    <input type="submit"
                           class="btn-medusa pull-left config_submitter button"
                           value="Save Changes"
                           :disabled="saving"
                    >
                </div><!--/config-components//-->
            </form>
        </div><!--/config-content//-->
    </div><!--/config//-->
</template>
<script>
import { mapActions, mapState } from 'vuex';
import { ToggleButton } from 'vue-js-toggle-button';
import { AppLink, FileBrowser, NamePattern, SelectList } from './helpers';

export default {
    name: 'config-post-processing',
    components: {
        AppLink,
        FileBrowser,
        NamePattern,
        SelectList,
        ToggleButton
    },
    data() {
        return {
            presets: [
                { pattern: 'Season %0S/%SN - %Sx%0E - %EN', example: 'Season 02/Show Name - 2x03 - Ep Name' },
                { pattern: 'Season %0S/%S.N.S%0SE%0E.%E.N', example: 'Season 02/Show.Name.S02E03.Ep.Name' },
                { pattern: 'Season %S/%S_N_%Sx%0E_%E_N', example: 'Season 2/Show_Name_2x03_Ep_Name' },
                { pattern: 'Season %S/%SN S%0SE%0E %SQN', example: 'Season 2/Show Name S02E03 720p HDTV x264' },
                { pattern: 'Season %0S/%S.N.S%0SE%0E.%Q.N-%RG', example: 'Season 02/Show.Name.S02E03.720p.HDTV-RLSGROUP' }
            ],
            processMethods: [
                { value: 'copy', text: 'Copy' },
                { value: 'move', text: 'Move' },
                { value: 'hardlink', text: 'Hard Link' },
                { value: 'symlink', text: 'Symbolic Link' },
                { value: 'keeplink', text: 'Keep Link' }
            ],
            timezoneOptions: [
                { value: 'local', text: 'Local' },
                { value: 'network', text: 'Network' }
            ],
            metadataProviderSelected: null,
            saving: false
        };
    },
    methods: {
        ...mapActions([
            'setConfig'
        ]),
        onChangeSyncFiles(items) {
            const { postprocessing } = this;
            postprocessing.syncFiles = items.map(item => item.value);
        },
        onChangeAllowedExtensions(items) {
            const { postprocessing } = this;
            postprocessing.allowedExtensions = items.map(item => item.value);
        },
        onChangeExtraScripts(items) {
            const { postprocessing } = this;
            postprocessing.extraScripts = items.map(item => item.value);
        },
        saveNaming(values) {
            const { postprocessing } = this;
            if (!this.configLoaded) {
                return;
            }
            postprocessing.naming.pattern = values.pattern;
            postprocessing.naming.multiEp = values.multiEpStyle;
        },
        saveNamingSports(values) {
            const { postprocessing } = this;
            if (!this.configLoaded) {
                return;
            }
            postprocessing.naming.patternSports = values.pattern;
            postprocessing.naming.enableCustomNamingSports = values.enabled;
        },
        saveNamingAbd(values) {
            const { postprocessing } = this;
            if (!this.configLoaded) {
                return;
            }
            postprocessing.naming.patternAirByDate = values.pattern;
            postprocessing.naming.enableCustomNamingAirByDate = values.enabled;
        },
        saveNamingAnime(values) {
            const { postprocessing } = this;
            if (!this.configLoaded) {
                return;
            }
            postprocessing.naming.patternAnime = values.pattern;
            postprocessing.naming.animeMultiEp = values.multiEpStyle;
            postprocessing.naming.animeNamingType = values.animeNamingType;
            postprocessing.naming.enableCustomNamingAnime = values.enabled;
        },
        async save() {
            const { postprocessing, metadata, setConfig } = this;
            // We want to wait until the page has been fully loaded, before starting to save stuff.
            if (!this.configLoaded) {
                return;
            }
            // Disable the save button until we're done.
            this.saving = true;

            // Clone the config into a new object
            const config = Object.assign({}, {
                postProcessing: postprocessing,
                metadata
            });

            // Use destructuring to remove the unwanted keys.
            const { multiEpStrings, reflinkAvailable, extraScriptsUrl, ...rest } = postprocessing;
            // Assign the object with the keys removed to our copied object.
            config.postProcessing = rest;

            const section = 'main';

            try {
                await setConfig({ section, config });
                this.$snotify.success(
                    'Saved Post-Processing config',
                    'Saved',
                    { timeout: 5000 }
                );
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to save Post-Processing config',
                    'Error'
                );
            } finally {
                this.saving = false;
            }
        },
        /**
         * Get the first enabled metadata provider based on enabled features.
         * @param {Object} providers - The metadata providers object.
         * @return {String} - The id of the first enabled provider.
         */
        getFirstEnabledMetadataProvider() {
            const { metadata } = this;
            const firstEnabledProvider = Object.values(metadata.metadataProviders).find(provider => {
                return provider.showMetadata || provider.episodeMetadata;
            });
            return firstEnabledProvider === undefined ? 'kodi' : firstEnabledProvider.id;
        }
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            metadata: state => state.config.metadata,
            postprocessing: state => state.config.postprocessing,
            system: state => state.config.system
        }),
        configLoaded() {
            const { postprocessing } = this;
            return postprocessing.processAutomatically !== null;
        },
        multiEpStringsSelect() {
            const { postprocessing } = this;
            if (!postprocessing.multiEpStrings) {
                return [];
            }
            return Object.keys(postprocessing.multiEpStrings).map(k => ({
                value: Number(k),
                text: postprocessing.multiEpStrings[k]
            }));
        }
    },
    beforeMount() {
        // Wait for the next tick, so the component is rendered
        this.$nextTick(() => {
            $('#config-components').tabs();
        });
    },
    watch: {
        'metadata.metadataProviders': function(providers) { // eslint-disable-line object-shorthand
            const { getFirstEnabledMetadataProvider } = this;
            if (Object.keys(providers).length > 0) {
                this.metadataProviderSelected = getFirstEnabledMetadataProvider();
            }
        }
    }
};
</script>
<style>
</style>
