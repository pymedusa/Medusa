<template>
    <div id="config">
        <div v-if="configLoaded" id="config-content">
            <form id="configForm" class="form-horizontal" @submit.prevent="save()">
                <vue-tabs>
                    <v-tab key="post_processing" title="Post-Processing">
                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Scheduled Post-Processing</h3>
                                <p>Settings that dictate how Medusa should process completed downloads.</p>
                                <p>The scheduled post-processor will periodically scan a folder for media to process.</p>
                            </div>

                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">
                                    <config-toggle-slider v-model="postprocessing.processAutomatically" label="Scheduled Post-Processor" id="process_automatically">
                                        <p>Enable the scheduled post-processor to scan and process any files in your <i>Post-Processing Dir</i>?</p>
                                        <div class="clear-left"><p><b>Note:</b> Do not use if you use an external post-processing script</p></div>
                                    </config-toggle-slider>

                                    <config-textbox-number v-show="postprocessing.processAutomatically" v-model="postprocessing.autoPostprocessorFrequency"
                                                           label="Auto Post-Processing Frequency" id="autopostprocessor_frequency"
                                                           :min="10" :step="1">
                                        <span>Time in minutes to check for new files to auto post-process (min 10)</span>
                                    </config-textbox-number>
                                </fieldset>
                            </div> <!-- end of col -->
                        </div> <!-- end of row -->

                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <a name="automated-download-handling" /><h3>Automated Download Handling</h3>
                                <p>Check clients directly through api's for completed or failed downloads.</p>
                                <p>The download handler will periodically connect to the nzb or torrent clients and check for completed and failed downloads.</p>
                            </div>

                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">
                                    <config-toggle-slider v-model="postprocessing.downloadHandler.enabled" label="Enable download handler" id="enable_download_handler">
                                        <p>Enable download handler</p>
                                        <p><b>Note:</b>Do not combine with scheduled post processing or external pp scripts!</p>
                                    </config-toggle-slider>

                                    <config-textbox-number v-show="postprocessing.downloadHandler.enabled"
                                                           :min="postprocessing.downloadHandler.minFrequency" :step="1"
                                                           v-model.number="postprocessing.downloadHandler.frequency"
                                                           label="Download handler frequency" id="download_handler_frequency">
                                        <p>Time in minutes to check on the download clients (min 5, default: 60)</p>
                                    </config-textbox-number>

                                    <config-textbox-number
                                        v-if="postprocessing.downloadHandler.enabled"
                                        v-model="postprocessing.downloadHandler.torrentSeedRatio"
                                        label="Global torrent seed ratio" id="torrent_seed_ratio"
                                        :step="0.1" :min="0" :max="100"
                                    >
                                        <p>Torrent seed ratio used to trigger a torrent seed action</p>
                                    </config-textbox-number>

                                    <config-template label-for="torrent_seed_action" label="Torrent seed action">
                                        <select id="torrent_seed_action" name="torrent_seed_action" v-model="postprocessing.downloadHandler.torrentSeedAction" class="form-control input-sm">
                                            <option :value="option.value" v-for="option in seedActions" :key="option.value">{{ option.text }}</option>
                                        </select>
                                        <p>Setting the ratio to 0, will have it perform the action directly after postprocessing.)</p>
                                    </config-template>

                                    <config-template label-for="default_client_path" label="Default client path">
                                        <file-browser id="default_client_path" name="default_client_path" title="Select client download location" :initial-dir="postprocessing.defaultClientPath" @update="postprocessing.defaultClientPath = $event" />
                                        <span class="clear-left">To prevent postprocessing from deleting your (root) download location, select the location to protect it from removal.</span>
                                    </config-template>
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
                                    <config-template label-for="tv_download_dir" label="Post-Processing Dir">
                                        <file-browser id="tv_download_dir" name="tv_download_dir" title="Select series download location" :initial-dir="postprocessing.showDownloadDir" @update="postprocessing.showDownloadDir = $event" />
                                        <span class="clear-left">The folder where your download client puts the completed TV downloads.</span>
                                        <div class="clear-left"><p><b>Note:</b> Please use separate downloading and completed folders in your download client if possible.</p></div>
                                        <span>The Post processing dir is also used when your download client is running on a different machine. It will try to map a postprocessed folder to PP dir.</span>
                                    </config-template>

                                    <config-template label-for="processing_method" label="Processing Method">
                                        <select id="processing_method" name="processing_method" v-model="postprocessing.processMethod" class="form-control input-sm">
                                            <option :value="option.value" v-for="option in processMethods" :key="option.value">{{ option.text }}</option>
                                        </select>
                                        <span>What method should be used to put files into the library?</span>
                                        <p><b>Note:</b> If you keep seeding torrents after they finish, please avoid the 'move' processing method to prevent errors.</p>
                                        <p v-if="postprocessing.processMethod == 'reflink'">To use reference linking, the <app-link href="https://pypi.python.org/pypi/reflink/0.1.4">reflink package</app-link> needs to be installed.</p>
                                    </config-template>

                                    <config-toggle-slider v-model="postprocessing.specificProcessMethod" label="Specific postprocessing methods" id="specific_post_processing">
                                        <span>Enable this option if you want to use different processing methods (copy, move, etc..) for torrent and nzb downloads.</span>
                                        <p><b>Note:</b>This option is only used by the <a href="config/postProcessing/#automated-download-handling">Automated Download Handling</a> option</p>
                                    </config-toggle-slider>

                                    <config-template v-if="postprocessing.specificProcessMethod" label-for="processing_method_torrent" label="Processing Method Torrent">
                                        <select id="processing_method_torrent" name="processing_method_torrent" v-model="postprocessing.processMethodTorrent" class="form-control input-sm">
                                            <option :value="option.value" v-for="option in processMethods" :key="option.value">{{ option.text }}</option>
                                        </select>
                                        <span>What method should be used to put files into the library?</span>
                                        <p><b>Note:</b> If you keep seeding torrents after they finish, please avoid the 'move' processing method to prevent errors.</p>
                                        <p v-if="postprocessing.processMethod == 'reflink'">To use reference linking, the <app-link href="https://pypi.python.org/pypi/reflink/0.1.4">reflink package</app-link> needs to be installed.</p>
                                    </config-template>

                                    <config-template v-if="postprocessing.specificProcessMethod" label-for="processing_method_nzb" label="Processing Method Nzb">
                                        <select id="processing_method_nzb" name="processing_method_nzb" v-model="postprocessing.processMethodNzb" class="form-control input-sm">
                                            <option :value="option.value" v-for="option in processMethods" :key="option.value">{{ option.text }}</option>
                                        </select>
                                        <span>What method should be used to put files into the library?</span>
                                        <p v-if="postprocessing.processMethod == 'reflink'">To use reference linking, the <app-link href="https://pypi.python.org/pypi/reflink/0.1.4">reflink package</app-link> needs to be installed.</p>
                                    </config-template>

                                    <config-toggle-slider v-model="postprocessing.postponeIfSyncFiles" label="Postpone post-processing" id="postpone_if_sync_files">
                                        <span>Wait to process a folder if sync files are present.</span>
                                    </config-toggle-slider>

                                    <config-template label-for="sync_files" label="Sync File Extensions">
                                        <select-list name="sync_files" id="sync_files" csv-enabled :list-items="postprocessing.syncFiles" @change="onChangeSyncFiles" />
                                        <span>Comma separated list of extensions or filename globs Medusa ignores when post-processing</span>
                                    </config-template>

                                    <config-toggle-slider v-model="postprocessing.postponeIfNoSubs" label="Postpone if no subtitle" id="postpone_if_no_subs">
                                        <span>Wait to process a file until subtitles are present</span><br>
                                        <span>Language names are allowed in subtitle filename (en.srt, pt-br.srt, ita.srt, etc.)</span><br>
                                        <span><b>Note:</b> Automatic post-processor should be disabled to avoid files with pending subtitles being processed over and over.</span><br>
                                        <span>If you have any active show with subtitle search disabled, you must enable Automatic post-processor.</span>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="postprocessing.renameEpisodes" label="Rename Episodes" id="rename_episodes">
                                        <span>Rename episode using the Episode Naming settings?</span>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="postprocessing.createMissingShowDirs" label="Create missing show directories" id="create_missing_show_dirs">
                                        <span>Create missing show directories when they get deleted</span>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="postprocessing.addShowsWithoutDir" label="Add shows without directory" id="add_shows_wo_dir">
                                        <span>Add shows without creating a directory (not recommended)</span>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="postprocessing.moveAssociatedFiles" label="Delete associated files" id="move_associated_files">
                                        <span>Delete srt/srr/sfv/etc files while post-processing?</span>
                                    </config-toggle-slider>

                                    <config-template label-for="allowed_extensions" label="Keep associated file extensions">
                                        <select-list name="allowed_extensions" id="allowed_extensions" csv-enabled :list-items="postprocessing.allowedExtensions" @change="onChangeAllowedExtensions" />
                                        <span>Comma separated list of associated file extensions Medusa should keep while post-processing.</span><br>
                                        <span>Leaving it empty means all associated files will be deleted</span>
                                    </config-template>

                                    <config-toggle-slider v-model="postprocessing.nfoRename" label="Rename .nfo file" id="nfo_rename">
                                        <span>Rename the original .nfo file to .nfo-orig to avoid conflicts?</span>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="postprocessing.airdateEpisodes" label="Change File Date" id="airdate_episodes">
                                        <span>Set last modified filedate to the date that the episode aired?</span>
                                    </config-toggle-slider>

                                    <config-template label-for="file_timestamp_timezone" label="Timezone for File Date">
                                        <select id="file_timestamp_timezone" name="file_timestamp_timezone" v-model="postprocessing.fileTimestampTimezone" class="form-control input-sm">
                                            <option :value="option.value" v-for="option in timezoneOptions" :key="option.value">{{ option.text }}</option>
                                        </select>
                                        <span>What timezone should be used to change File Date?</span>
                                    </config-template>

                                    <config-toggle-slider v-model="postprocessing.unpack" label="Unpack" id="unpack">
                                        <span>Unpack any TV releases in your <i>TV Download Dir</i>?</span><br>
                                        <span><b>Note:</b> Only working with RAR archive</span>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="postprocessing.deleteRarContent" label="Delete RAR contents" id="del_rar_contents">
                                        <span>Delete content of RAR files, even if Process Method not set to move?</span>
                                    </config-toggle-slider>

                                    <config-toggle-slider v-model="postprocessing.noDelete" label="Don't delete empty folders" id="no_delete">
                                        <span>Leave empty folders when post-processing?</span><br>
                                        <span><b>Note:</b> Can be overridden using manual post-processing</span>
                                    </config-toggle-slider>

                                    <config-template label-for="extra_scripts" label="Extra Scripts">
                                        <select-list name="extra_scripts" id="extra_scripts" csv-enabled :list-items="postprocessing.extraScripts" @change="onChangeExtraScripts" />
                                        <span>See <app-link :href="postprocessing.extraScriptsUrl" class="wikie"><strong>Wiki</strong></app-link> for script arguments description and usage.</span>
                                    </config-template>

                                    <config-toggle-slider :disabled="system.ffprobeVersion === 'ffprobe not available'" v-model="postprocessing.ffmpeg.checkStreams" label="Use ffprobe to validate downloaded video files for a minimum of one video and audio stream" id="check_streams">
                                        <span>Use PPROBE to check a video for a minimum of one audio and video stream. This is the more safe version of the two. It will only scan the video files meta data.</span><br>
                                        <span v-if="system.ffprobeVersion === 'ffprobe not available'" style="color: red">Ffmpeg binary not found. Add the ffmpeg bin location to your system's environment or configure a path manually below.</span>
                                    </config-toggle-slider>

                                    <config-template label-for="ffmpeg_path" label="Alternative ffmpeg path">
                                        <file-browser id="ffmpeg_path" name="ffmpeg_path" title="Select folder location for the ffmpeg binary" :initial-dir="postprocessing.ffmpeg.path" @update="postprocessing.ffmpeg.path = $event" />
                                        <span>If you can't or don't want to depend on the os environment path, you can fix the location to your ffmpeg binary.</span>
                                    </config-template>

                                </fieldset>
                                <input type="submit"
                                       class="btn-medusa config_submitter"
                                       value="Save Changes"
                                       :disabled="saving"
                                >
                            </div> <!-- /col -->
                        </div> <!-- /row -->
                    </v-tab>
                    <v-tab key="Episode Naming" title="Episode Naming">
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
                                        :multi-ep-styles="multiEpStringsSelect"
                                        @update-pattern="postprocessing.naming.pattern = $event;" @change="saveNaming"
                                    />

                                    <!-- default sports name-pattern component -->
                                    <name-pattern
                                        class="component-item" :enabled="postprocessing.naming.enableCustomNamingSports"
                                        :naming-pattern="postprocessing.naming.patternSports" :naming-presets="presets" type="sports"
                                        :enabled-naming-custom="postprocessing.naming.enableCustomNamingSports"
                                        @update-pattern="postprocessing.naming.patternSports = $event" @change="saveNamingSports"
                                    />

                                    <!-- default airs by date name-pattern component -->
                                    <name-pattern
                                        class="component-item" :enabled="postprocessing.naming.enableCustomNamingAirByDate"
                                        :naming-pattern="postprocessing.naming.patternAirByDate" :naming-presets="presets" type="airs by date"
                                        :enabled-naming-custom="postprocessing.naming.enableCustomNamingAirByDate"
                                        @update-pattern="postprocessing.naming.patternAirByDate = $event" @change="saveNamingAbd"
                                    />

                                    <!-- default anime name-pattern component -->
                                    <name-pattern
                                        class="component-item" :enabled="postprocessing.naming.enableCustomNamingAnime"
                                        :naming-pattern="postprocessing.naming.patternAnime" :naming-presets="presets" type="anime" :multi-ep-style="postprocessing.naming.animeMultiEp"
                                        :multi-ep-styles="multiEpStringsSelect" :anime-naming-type="postprocessing.naming.animeNamingType"
                                        :enabled-naming-custom="postprocessing.naming.enableCustomNamingAnime"
                                        @update-pattern="postprocessing.naming.patternAnime = $event" @change="saveNamingAnime"
                                    />

                                    <config-toggle-slider v-model="postprocessing.naming.stripYear" label="Strip Show Year" id="naming_strip_year" style="margin-top: 1em;">
                                        <span>Remove the TV show's year when renaming the file?</span>
                                        <p>Only applies to shows that have year inside parentheses</p>
                                    </config-toggle-slider>

                                </fieldset>

                                <input type="submit"
                                       class="btn-medusa config_submitter"
                                       value="Save Changes"
                                       :disabled="saving"
                                >
                            </div>
                        </div>
                    </v-tab>
                    <v-tab key="metadata" title="Metadata">
                        <div class="row component-group">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Metadata</h3>
                                <p>The data associated to the data. These are files associated to a TV show in the form of images and text that, when supported, will enhance the viewing experience.</p>
                            </div>
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">
                                    <config-template label-for="metadata_type" label="Metadata Type">
                                        <select id="metadataType" name="metadataType" v-model="metadataProviderSelected" class="form-control input-sm">
                                            <option :value="option.id" v-for="option in metadata.metadataProviders" :key="option.id">{{ option.name }}</option>
                                        </select>
                                        <span class="d-block">Toggle the metadata options that you wish to be created. <b>Multiple targets may be used.</b></span>
                                    </config-template>

                                    <div class="metadata" v-show="provider.id === metadataProviderSelected" v-for="provider in metadata.metadataProviders" :key="provider.id" id="provider.id">
                                        <div class="metadata-options-wrapper">
                                            <h4>Create:</h4>
                                            <div class="metadata_options">
                                                <label :for="`${provider.id}_show_metadata`"><input type="checkbox" class="metadata_checkbox" :id="`${provider.id}_show_metadata`" v-model="provider.showMetadata">&nbsp;Show Metadata</label>
                                                <label :for="`${provider.id}_episode_metadata`"><input type="checkbox" class="metadata_checkbox" :id="`${provider.id}_episode_metadata`" v-model="provider.episodeMetadata" :disabled="provider.example.episodeMetadata.includes('not supported')">&nbsp;Episode Metadata</label>
                                                <label :for="`${provider.id}_fanart`"><input type="checkbox" class="float-left metadata_checkbox" :id="`${provider.id}_fanart`" v-model="provider.fanart" :disabled="provider.example.fanart.includes('not supported')">&nbsp;Show Fanart</label>
                                                <label :for="`${provider.id}_poster`"><input type="checkbox" class="float-left metadata_checkbox" :id="`${provider.id}_poster`" v-model="provider.poster" :disabled="provider.example.poster.includes('not supported')">&nbsp;Show Poster</label>
                                                <label :for="`${provider.id}_banner`"><input type="checkbox" class="float-left metadata_checkbox" :id="`${provider.id}_banner`" v-model="provider.banner" :disabled="provider.example.banner.includes('not supported')">&nbsp;Show Banner</label>
                                                <label :for="`${provider.id}_episode_thumbnails`"><input type="checkbox" class="float-left metadata_checkbox" :id="`${provider.id}_episode_thumbnails`" v-model="provider.episodeThumbnails" :disabled="provider.example.episodeThumbnails.includes('not supported')">&nbsp;Episode Thumbnails</label>
                                                <label :for="`${provider.id}_season_posters`"><input type="checkbox" class="float-left metadata_checkbox" :id="`${provider.id}_season_posters`" v-model="provider.seasonPosters" :disabled="provider.example.seasonPosters.includes('not supported')">&nbsp;Season Posters</label>
                                                <label :for="`${provider.id}_season_banners`"><input type="checkbox" class="float-left metadata_checkbox" :id="`${provider.id}_season_banners`" v-model="provider.seasonBanners" :disabled="provider.example.seasonBanners.includes('not supported')">&nbsp;Season Banners</label>
                                                <label :for="`${provider.id}_season_all_poster`"><input type="checkbox" class="float-left metadata_checkbox" :id="`${provider.id}_season_all_poster`" v-model="provider.seasonAllPoster" :disabled="provider.example.seasonAllPoster.includes('not supported')">&nbsp;Season All Poster</label>
                                                <label :for="`${provider.id}_season_all_banner`"><input type="checkbox" class="float-left metadata_checkbox" :id="`${provider.id}_season_all_banner`" v-model="provider.seasonAllBanner" :disabled="provider.example.seasonAllBanner.includes('not supported')">&nbsp;Season All Banner</label>
                                                <label :for="`${provider.id}_overwrite_nfo`"><input type="checkbox" class="float-left metadata_checkbox" :id="`${provider.id}_overwrite_nfo`" v-model="provider.overwriteNfo">&nbsp;Overwrite Nfo</label>
                                            </div>
                                        </div>
                                        <div class="metadata-example-wrapper">
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
                    </v-tab>
                    <v-tab key="guessit" title="Guessit">
                        <test-guessit />
                    </v-tab>
                </vue-tabs>
                <h6 class="pull-right"><b>All non-absolute folder locations are relative to <span class="path">{{system.dataDir}}</span></b> </h6>
            </form>
        </div><!--/config-content//-->
    </div><!--/config//-->
</template>
<script>
import { mapActions, mapState } from 'vuex';
import { VueTabs, VTab } from 'vue-nav-tabs/dist/vue-tabs.js';
import {
    AppLink,
    ConfigTextboxNumber,
    ConfigToggleSlider,
    ConfigTemplate,
    FileBrowser,
    NamePattern,
    SelectList,
    TestGuessit
} from './helpers';

export default {
    name: 'config-post-processing',
    components: {
        AppLink,
        ConfigTextboxNumber,
        ConfigToggleSlider,
        ConfigTemplate,
        FileBrowser,
        NamePattern,
        SelectList,
        TestGuessit,
        VueTabs,
        VTab
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
            'getConfig',
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
            postprocessing.naming.multiEp = values.multiEpStyle;
        },
        saveNamingSports(values) {
            const { postprocessing } = this;
            if (!this.configLoaded) {
                return;
            }
            postprocessing.naming.enableCustomNamingSports = values.enabled;
        },
        saveNamingAbd(values) {
            const { postprocessing } = this;
            if (!this.configLoaded) {
                return;
            }
            postprocessing.naming.enableCustomNamingAirByDate = values.enabled;
        },
        saveNamingAnime(values) {
            const { postprocessing } = this;
            if (!this.configLoaded) {
                return;
            }
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
                // Get system config to check for the ffmpeg binary.
                this.getConfig('system');
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
            torrentMethod: state => state.config.clients.torrents.method,
            system: state => state.config.system,
            configLoaded: state => state.config.system.configLoaded
        }),
        multiEpStringsSelect() {
            const { postprocessing } = this;
            if (!postprocessing.multiEpStrings) {
                return [];
            }
            return Object.keys(postprocessing.multiEpStrings).map(k => ({
                value: Number(k),
                text: postprocessing.multiEpStrings[k]
            }));
        },
        seedActions() {
            const { torrentMethod } = this;
            let actions = [
                { value: '', text: 'No action' },
                { value: 'remove', text: 'Remove torrent' },
                { value: 'pause', text: 'Pause torrent' }
            ];
            const removeWithData = [{ value: 'remove_with_data', text: 'Remove torrent with data' }];

            if (!['rtorrent'].includes(torrentMethod)) {
                actions = [...actions, ...removeWithData];
            }
            return actions;
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
.metadata {
    padding-left: 20px;
    display: flex;
}

.metadata-options-wrapper {
    min-width: 190px;
}

.metadata-example-wrapper {
    width: 325px;
    margin-left: 4em;
}

@media (max-width: 480px) {
    .metadata {
        flex-direction: column;
    }

    .metadata-example-wrapper {
        margin-left: 0;
    }
}
</style>
