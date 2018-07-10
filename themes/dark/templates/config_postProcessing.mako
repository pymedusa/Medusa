<%inherit file="/layouts/main.mako"/>
<%namespace name="inc_defs" file="/inc_defs.mako"/>
<%!
    import os.path
    import datetime
    import pkgutil
    from medusa import app
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import Quality, qualityPresets, statusStrings, qualityPresetStrings, cpu_presets, MULTI_EP_STRINGS
    from medusa import config
    from medusa import metadata
    from medusa.metadata.generic import GenericMetadata
    from medusa import naming
%>

<%block name="scripts">
<%include file="/vue-components/name-pattern.mako"/>
<script>

window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        store,
        metaInfo: {
            title: 'Config - Post Processing'
        },
        data() {
            // FIXME: replace with MEUDSA.config.
            const multiEpStrings = ${inc_defs.convert([{'value': str(x), 'text': y} for x, y in MULTI_EP_STRINGS.items()])};
            
            const processMethods = [
                { value: 'copy', text: 'Copy'},
                { value: 'move', text: 'Move'},
                { value: 'hardlink', text: 'Hard Link'},
                { value: 'symlink', text: 'Symbolic Link'}                
            ];
            // if (config.postProcessing.reflinkAvailable) {
            //     processMethods.push({ value: 'reflink', text: 'Reference Link' })
            // }
            const timezoneOptions = [
                { value: 'local', text: 'Local'},
                { value: 'network', text: 'Network'}
            ]

            return {
                header: 'Post Processing',
                presets: [
                    '%SN - %Sx%0E - %EN',
                    '%S.N.S%0SE%0E.%E.N',
                    '%Sx%0E - %EN',
                    'S%0SE%0E - %EN',
                    'Season %0S/%S.N.S%0SE%0E.%Q.N-%RG'
                ],
                processMethods: processMethods,
                multiEpStrings: multiEpStrings,
                animeMultiEpStrings: multiEpStrings,
                timezoneOptions: timezoneOptions
                // multiEpSelected: config.postProcessing.naming.multiEp,

                // enabledSports: config.postProcessing.naming.enableCustomNamingSports,
                // sportsPattern: config.postProcessing.naming.patternSports,

                // enabledAirByDate: config.postProcessing.naming.enableCustomNamingAirByDate,
                // abdPattern: config.postProcessing.naming.patternAirByDate,
                
                // enabledAnime: config.postProcessing.naming.enableCustomNamingAnime,
                // animePattern: config.postProcessing.naming.patternAnime,
                // animeMultiEpSelected: config.postProcessing.naming.animeMultiEp,      
                // animeNamingType: config.postProcessing.naming.animeNamingType,
                // seriesDownloadDir: config.postProcessing.seriesDownloadDir,
                // processAutomatically: config.postProcessing.processAutomatically,
                // processMethod: config.postProcessing.processMethod,
                // deleteRarContent: config.postProcessing.deleteRarContent,
                // unpack: config.postProcessing.unpack,
                // noDelete: config.postProcessing.noDelete,
                // reflinkAvailable: config.postProcessing.reflinkAvailable,
                // postponeIfSyncFiles: config.postProcessing.postponeIfSyncFiles,
                // autoPostprocessorFrequency: config.postProcessing.autoPostprocessorFrequency || 10,
                // airdateEpisodes: config.postProcessing.airdateEpisodes,
                // moveAssociatedFiles: config.postProcessing.moveAssociatedFiles,
                // allowedExtensions: config.postProcessing.allowedExtensions || [],
                // addShowsWithoutDir: config.postProcessing.addShowsWithoutDir,
                // createMissingShowDirs: config.postProcessing.createMissingShowDirs,
                // renameEpisodes: config.postProcessing.renameEpisodes,
                // postponeIfNoSubs: config.postProcessing.postponeIfNoSubs,
                // nfoRename: config.postProcessing.nfoRename,
                // syncFiles: config.postProcessing.syncFiles || [],
                // fileTimestampTimezone: config.postProcessing.fileTimestampTimezone || 'local',
                // extraScripts: config.postProcessing.extraScripts || [],
                // extraScriptsUrl: config.postProcessing.extraScriptsUrl,
                // appNamingStripYear: config.postProcessing.appNamingStripYear
            };
        },
        methods: {
            onChangePattern(pattern) {
                const savePatternMap = new Map(
                    [
                        ['sports', 'sportsPattern'],
                        ['airs by date', 'abdPattern'],
                        ['anime', 'animePattern']
                    ]
                ).get(pattern.type)
                if (savePatternMap) {
                    this[savePatternMap] = pattern.pattern;
                } else {
                    this.pattern = pattern.pattern;
                }
            },
            savePostprocessing() {
                const { $store } = this;
                // We want to wait until the page has been fully loaded, before starting to save stuff.
                if (!this.configLoaded) {
                    return
                }
                // Disable the save button until we're done.
                this.saving = true;
                $store.dispatch('setConfig', {section: 'main', config: { }}).then(() => {
                    this.$snotify.success('Saved postprocessing config', 'Saved', { timeout: 5000 });
                }).catch(error => {
                    this.$snotify.error(
                        'Error while trying to save postprocessing config',
                        'Error'
                    );
                });
            }
        },
        computed: Object.assign(store.mapState(['config']), {
            processMethodDescription(processMethod) {
                return this.processMethods.get(processMethod)
            }
        }),
        mounted() {
            const { $store } = this;

            if (this.configLoaded) return;

            $store.dispatch('getConfig', 'main').then(() => {
                this.configLoaded = true;
            }).catch(error => {
                console.debug(error);
            });
        }
    });
};
</script>
</%block>
<%block name="content">
<div id="content960">
    <h1 class="header">{{header}}</h1>
    <div id="config">
        <div id="config-content">
            <form id="configForm" class="form-horizontal" @submit.prevent="savePostprocessing()"/>
                <div id="config-components">
                    <ul>
                        <li><app-link href="#post-processing">Post Processing</app-link></li>
                        <li><app-link href="#episode-naming">Episode Naming</app-link></li>
                        <li><app-link href="#metadata">Metadata</app-link></li>
                    </ul>
                    <div id="post-processing" class="component-group">
                        <div class="row">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                    <h3>Post-Processing</h3>
                                    <p>Settings that dictate how Medusa should process completed downloads.</p>
                            </div>
                        
                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">
                                    <div class="form-group">
                                        <label for="process_automatically" class="col-sm-2 control-label">
                                            <span>Enable</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="process_automatically" name="process_automatically" v-model="config.postProcessing.processAutomatically" sync></toggle-button>
                                            <p>Enable the automatic post processor to scan and process any files in your <i>Post Processing Dir</i>?</p>
                                            <div class="clear-left"><p><b>NOTE:</b> Do not use if you use an external Post Processing script</p></div>
                                        </div>
                                    </div>
                                
                                    <div v-if="config.postProcessing.processAutomatically" id="post-process-toggle-wrapper">   
                                        
                                        <div class="form-group">
                                            <label for="tv_download_dir" class="col-sm-2 control-label">
                                                <span>Post Processing Dir</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <file-browser id="tv_download_dir" name="tv_download_dir" title="Select series download location" :initial-dir="config.postProcessing.seriesDownloadDir" @update="config.postProcessing.seriesDownloadDir = $event"></file-browser>
                                                <span class="clear-left">The folder where your download client puts the completed TV downloads.</span>
                                                <div class="clear-left"><p><b>NOTE:</b> Please use seperate downloading and completed folders in your download client if possible.</p></div>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="process_method" class="col-sm-2 control-label">
                                                <span>Processing Method:</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <select id="naming_multi_ep" name="naming_multi_ep" v-model="config.postProcessing.processMethod" class="form-control input-sm">
                                                    <option :value="option.value" v-for="option in processMethods">{{ option.text }}</option>
                                                </select>
                                                <span>What method should be used to put files into the library?</span>
                                                <p><b>NOTE:</b> If you keep seeding torrents after they finish, please avoid the 'move' processing method to prevent errors.</p>
                                                <p v-if="config.postProcessing.processMethod == 'reflink'">To use reference linking, the <app-link href="http://www.dereferer.org/?https://pypi.python.org/pypi/reflink/0.1.4">reflink package</app-link> needs to be installed.</p>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="autopostprocessor_frequency" class="col-sm-2 control-label">
                                                <span>Auto Post-Processing Frequency</span>                                          
                                            </label>
                                            <div class="col-sm-10 content">
                                                <input type="number" min="10" step="1" name="autopostprocessor_frequency" id="autopostprocessor_frequency" v-model="config.postProcessing.autoPostprocessorFrequency || 10" class="form-control input-sm input75" />
                                                <span>Time in minutes to check for new files to auto post-process (min 10)</span>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="postpone_if_sync_files" class="col-sm-2 control-label">
                                                <span>Postpone post processing</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="postpone_if_sync_files" name="postpone_if_sync_files" v-model="config.postProcessing.postponeIfSyncFiles" sync></toggle-button>
                                                <span>Wait to process a folder if sync files are present.</span>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="sync_files" class="col-sm-2 control-label">
                                                <span>Sync File Extensions</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <select-list name="sync_files" id="sync_files" csv-enabled :list-items="config.postProcessing.syncFiles" @change="config.postProcessing.syncFiles = $event"></select-list>
                                                <span>comma seperated list of extensions or filename globs Medusa ignores when Post Processing</span>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="postpone_if_no_subs" class="col-sm-2 control-label">
                                                <span>Postpone if no subtitle</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                    <toggle-button :width="45" :height="22" id="postpone_if_no_subs" name="postpone_if_no_subs" v-model="config.postProcessing.postponeIfNoSubs" sync></toggle-button>
                                                    <span>Wait to process a file until subtitles are present</span>
                                                    <span>Language names are allowed in subtitle filename (en.srt, pt-br.srt, ita.srt, etc.)</span>
                                                    <span>&nbsp;</span>
                                                    <span><b>NOTE:</b> Automatic post processor should be disabled to avoid files with pending subtitles being processed over and over.</span>
                                                    <span>If you have any active show with subtitle search disabled, you must enable Automatic post processor.</span>    
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="rename_episodes" class="col-sm-2 control-label">
                                                <span>Rename Episodes</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="rename_episodes" name="rename_episodes" v-model="config.postProcessing.renameEpisodes" sync></toggle-button>
                                                <span>Rename episode using the Episode Naming settings?</span>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="create_missing_show_dirs" class="col-sm-2 control-label">
                                                <span>Create missing show directories</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="create_missing_show_dirs" name="create_missing_show_dirs" v-model="config.postProcessing.createMissingShowDirs" sync></toggle-button>
                                                <span >Create missing show directories when they get deleted</span>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="add_shows_wo_dir" class="col-sm-2 control-label">
                                                <span>Add shows without directory</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="add_shows_wo_dir" name="add_shows_wo_dir" v-model="config.postProcessing.addShowsWithoutDir" sync></toggle-button>
                                                <span>Add shows without creating a directory (not recommended)</span>
                                            </div>
                                        </div>
                                        
                                        <div class="form-group">
                                            <label for="move_associated_files" class="col-sm-2 control-label">
                                                <span>Delete associated files</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="move_associated_files" name="move_associated_files" v-model="config.postProcessing.moveAssociatedFiles" sync></toggle-button>
                                                <span>Delete srt/srr/sfv/etc files while post processing?</span>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label class="col-sm-2 control-label">
                                                <span>Keep associated file extensions</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <select-list name="allowed_extensions" id="allowed_extensions" :list-items="config.postProcessing.allowedExtensions" @change="config.postProcessing.allowedExtensions = $event"></select-list>
                                                <span>Comma seperated list of associated file extensions Medusa should keep while post processing. Leaving it empty means all associated files will be deleted</span>
                                            </div>
                                        </div>
                                        
                                        <div class="form-group">
                                            <label for="nfo_rename" class="col-sm-2 control-label">
                                                <span>Rename .nfo file</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="nfo_rename" name="nfo_rename" v-model="config.postProcessing.nfoRename" sync></toggle-button>
                                                <span >Rename the original .nfo file to .nfo-orig to avoid conflicts?</span>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="airdate_episodes" class="col-sm-2 control-label">
                                                <span>Change File Date</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="airdate_episodes" name="airdate_episodes" v-model="config.postProcessing.airdateEpisodes" sync></toggle-button>
                                                <span >Set last modified filedate to the date that the episode aired?</span>                                            
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="file_timestamp_timezone" class="col-sm-2 control-label">
                                                <span>Timezone for File Date:</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <select id="file_timestamp_timezone" name="file_timestamp_timezone" v-model="config.postProcessing.fileTimestampTimezone" class="form-control input-sm">
                                                    <option :value="option.value" v-for="option in timezoneOptions">{{ option.text }}</option>
                                                </select>     
                                                <span >What timezone should be used to change File Date?</span>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="unpack" class="col-sm-2 control-label">
                                                <span>Unpack</span>
                                                <span >Unpack any TV releases in your <i>TV Download Dir</i>?</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="unpack" name="unpack" v-model="config.postProcessing.unpack" sync></toggle-button>
                                                <span ><b>NOTE:</b> Only working with RAR archive</span>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="del_rar_contents" class="col-sm-2 control-label">
                                                <span>Delete RAR contents</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="del_rar_contents" name="del_rar_contents" v-model="config.postProcessing.deleteRarContent" sync></toggle-button>
                                                <span>Delete content of RAR files, even if Process Method not set to move?</span>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label for="no_delete" class="col-sm-2 control-label">
                                                <span>Don't delete empty folders</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="no_delete" name="no_delete" v-model="config.postProcessing.noDelete" sync></toggle-button>
                                                <span><b>NOTE:</b> Can be overridden using manual Post Processing</span>
                                                <span>Leave empty folders when Post Processing?</span>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label class="col-sm-2 control-label">
                                                <span>Extra Scripts</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <select-list name="extra_scripts" id="extra_scripts" :list-items="config.postProcessing.extraScripts" @change="config.postProcessing.extraScripts = $event"></select-list>
                                                <span>See <app-link :href="config.postProcessing.extraScriptsUrl" class="wikie"><strong>Wiki</strong></app-link> for script arguments description and usage.</span>
                                            </div>
                                        </div>

                                    </div> <!-- End of content wrapper -->
                                </fieldset>
                            </div> <!-- /col -->
                            </div> <!-- /row -->
                            <input type="submit" class="btn-medusa config_submitter" value="Save Changes" />
                    </div><!-- /component-group1 //-->

                    <div id="episode-naming" class="component-group">
                        <div class="row">
                            <div class="component-group-desc col-xs-12 col-md-2">
                                <h3>Episode Naming</h3>
                                <p>How Medusa will name and sort your episodes.</p>
                            </div>

                            <div class="col-xs-12 col-md-10">
                                <fieldset class="component-group-list">
                                    
                                    <!-- default name-pattern component -->
                                    <name-pattern class="component-group" :naming-pattern="config.postProcessing.naming.pattern" 
                                        :naming-presets="presets" :multi-ep-style="config.postProcessing.naming.multiEp" 
                                        :multi-ep-styles="multiEpStrings" @change="onChangePattern">
                                    </name-pattern>
        
                                    <!-- default sports name-pattern component -->
                                    <name-pattern class="component-group" :enabled="config.postProcessing.naming.enableCustomNamingSports" 
                                        :naming-pattern="config.postProcessing.naming.patternSports" :naming-presets="presets" type="sports" 
                                        :enabled-naming-custom="config.postProcessing.naming.enableCustomNamingSports" @change="onChangePattern">
                                    </name-pattern>
        
                                    <!-- default airs by date name-pattern component -->
                                    <name-pattern class="component-group" :enabled="config.postProcessing.naming.enableCustomNamingAirByDate" 
                                        :naming-pattern="config.postProcessing.naming.patternAirByDate" :naming-presets="presets" type="airs by date" 
                                        :enabled-naming-custom="config.postProcessing.naming.enableCustomNamingAirByDate" @change="onChangePattern">
                                    </name-pattern>
        
                                    <!-- default anime name-pattern component -->
                                    <name-pattern class="component-group" :enabled="config.postProcessing.naming.enableCustomNamingAnime" 
                                        :naming-pattern="config.postProcessing.naming.patternAnime" :naming-presets="presets" type="anime" :multi-ep-style="config.postProcessing.naming.animeMultiEp" 
                                        :multi-ep-styles="animeMultiEpStrings" :anime-naming-type="config.postProcessing.naming.animeNamingType" 
                                        :enabled-naming-custom="config.postProcessing.naming.enableCustomNamingAnime" @change="onChangePattern">
                                    </name-pattern>
        
                                    <div class="form-group component-group">
                                        <label for="naming_strip_year" class="col-sm-2 control-label">
                                            <span>Strip Show Year</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="naming_strip_year" name="naming_strip_year" 
                                                v-model="config.postProcessing.appNamingStripYear" sync>
                                            </toggle-button>
                                            <span>Remove the TV show's year when renaming the file?</span>
                                            <p>Only applies to shows that have year inside parentheses</p>
                                        </div>
                                    </div>

                                </fieldset>
                            </div>
                        </div>
                    </div>
                    <div id="metadata" class="component-group">
                        <div class="component-group-desc">
                            <h3>Metadata</h3>
                            <p>The data associated to the data. These are files associated to a TV show in the form of images and text that, when supported, will enhance the viewing experience.</p>
                        </div>
                        <fieldset class="component-group-list">
                            <div class="form-group">
                                <label>
                                    <span>Metadata Type:</span>
                                    <span >
                                        <% m_dict = metadata.get_metadata_generator_dict() %>
                                        <select id="metadataType" class="form-control input-sm">
                                        % for (cur_name, cur_generator) in sorted(m_dict.iteritems()):
                                            <option value="${cur_generator.get_id()}">${cur_name}</option>
                                        % endfor
                                        </select>
                                    </span>
                                </label>
                                <span>Toggle the metadata options that you wish to be created. <b>Multiple targets may be used.</b></span>
                            </div>
                            % for (cur_name, cur_generator) in m_dict.iteritems():
                            <% cur_metadata_inst = app.metadata_provider_dict[cur_generator.name] %>
                            <% cur_id = cur_generator.get_id() %>
                            <div class="metadataDiv" id="${cur_id}">
                                <div class="metadata_options_wrapper">
                                    <h4>Create:</h4>
                                    <div class="metadata_options">
                                        <label for="${cur_id}_show_metadata"><input type="checkbox" class="metadata_checkbox" id="${cur_id}_show_metadata" ${'checked="checked"' if cur_metadata_inst.show_metadata else ''}/>&nbsp;Show Metadata</label>
                                        <label for="${cur_id}_episode_metadata"><input type="checkbox" class="metadata_checkbox" id="${cur_id}_episode_metadata" ${'checked="checked"' if cur_metadata_inst.episode_metadata else ''}/>&nbsp;Episode Metadata</label>
                                        <label for="${cur_id}_fanart"><input type="checkbox" class="float-left metadata_checkbox" id="${cur_id}_fanart" ${'checked="checked"' if cur_metadata_inst.fanart else ''}/>&nbsp;Show Fanart</label>
                                        <label for="${cur_id}_poster"><input type="checkbox" class="float-left metadata_checkbox" id="${cur_id}_poster" ${'checked="checked"' if cur_metadata_inst.poster else ''}/>&nbsp;Show Poster</label>
                                        <label for="${cur_id}_banner"><input type="checkbox" class="float-left metadata_checkbox" id="${cur_id}_banner" ${'checked="checked"' if cur_metadata_inst.banner else ''}/>&nbsp;Show Banner</label>
                                        <label for="${cur_id}_episode_thumbnails"><input type="checkbox" class="float-left metadata_checkbox" id="${cur_id}_episode_thumbnails" ${'checked="checked"' if cur_metadata_inst.episode_thumbnails else ''}/>&nbsp;Episode Thumbnails</label>
                                        <label for="${cur_id}_season_posters"><input type="checkbox" class="float-left metadata_checkbox" id="${cur_id}_season_posters" ${'checked="checked"' if cur_metadata_inst.season_posters else ''}/>&nbsp;Season Posters</label>
                                        <label for="${cur_id}_season_banners"><input type="checkbox" class="float-left metadata_checkbox" id="${cur_id}_season_banners" ${'checked="checked"' if cur_metadata_inst.season_banners else ''}/>&nbsp;Season Banners</label>
                                        <label for="${cur_id}_season_all_poster"><input type="checkbox" class="float-left metadata_checkbox" id="${cur_id}_season_all_poster" ${'checked="checked"' if cur_metadata_inst.season_all_poster else ''}/>&nbsp;Season All Poster</label>
                                        <label for="${cur_id}_season_all_banner"><input type="checkbox" class="float-left metadata_checkbox" id="${cur_id}_season_all_banner" ${'checked="checked"' if cur_metadata_inst.season_all_banner else ''}/>&nbsp;Season All Banner</label>
                                    </div>
                                </div>
                                <div class="metadata_example_wrapper">
                                    <h4>Results:</h4>
                                    <div class="metadata_example">
                                        <label for="${cur_id}_show_metadata"><span id="${cur_id}_eg_show_metadata">${cur_metadata_inst.eg_show_metadata}</span></label>
                                        <label for="${cur_id}_episode_metadata"><span id="${cur_id}_eg_episode_metadata">${cur_metadata_inst.eg_episode_metadata}</span></label>
                                        <label for="${cur_id}_fanart"><span id="${cur_id}_eg_fanart">${cur_metadata_inst.eg_fanart}</span></label>
                                        <label for="${cur_id}_poster"><span id="${cur_id}_eg_poster">${cur_metadata_inst.eg_poster}</span></label>
                                        <label for="${cur_id}_banner"><span id="${cur_id}_eg_banner">${cur_metadata_inst.eg_banner}</span></label>
                                        <label for="${cur_id}_episode_thumbnails"><span id="${cur_id}_eg_episode_thumbnails">${cur_metadata_inst.eg_episode_thumbnails}</span></label>
                                        <label for="${cur_id}_season_posters"><span id="${cur_id}_eg_season_posters">${cur_metadata_inst.eg_season_posters}</span></label>
                                        <label for="${cur_id}_season_banners"><span id="${cur_id}_eg_season_banners">${cur_metadata_inst.eg_season_banners}</span></label>
                                        <label for="${cur_id}_season_all_poster"><span id="${cur_id}_eg_season_all_poster">${cur_metadata_inst.eg_season_all_poster}</span></label>
                                        <label for="${cur_id}_season_all_banner"><span id="${cur_id}_eg_season_all_banner">${cur_metadata_inst.eg_season_all_banner}</span></label>
                                    </div>
                                </div>
                                <input type="hidden" name="${cur_id}_data" id="${cur_id}_data" value="${cur_metadata_inst.get_config()}" />
                            </div>
                            % endfor
                            <div class="clearfix"></div><br>
                            <input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                        </fieldset>
                    </div><!-- /component-group3 //-->
                    <br>
                    <h6 class="pull-right"><b>All non-absolute folder locations are relative to <span class="path">${app.DATA_DIR}</span></b> </h6>
                    <input type="submit" class="btn-medusa pull-left config_submitter button" value="Save Changes" />
                </div><!--/config-components//-->
            </form>
        </div><!--/config-content//-->
    </div><!--/config//-->
    <div class="clearfix"></div>
</div><!-- #content960 //-->
</%block>
