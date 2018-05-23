<%inherit file="/layouts/main.mako"/>
<%namespace name="main" file="/layouts/main.mako"/>
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
        metaInfo: {
            title: 'Config - Post Processing'
        },
        data() {
            const multiEpStrings = ${main.convert([{'value': str(x), 'text': y} for x, y in MULTI_EP_STRINGS.items()])};

            return {
                header: 'Post Processing',
                pattern: 'lalalala',
                presets: [
                    '%SN - %Sx%0E - %EN',
                    '%S.N.S%0SE%0E.%E.N',
                    '%Sx%0E - %EN',
                    'S%0SE%0E - %EN',
                    'Season %0S/%S.N.S%0SE%0E.%Q.N-%RG'
                ],
                multiEpStrings: multiEpStrings,
                multiEpSelected: '1',
                enabledSports: false,
                enabledAnime: false,
                enabledAirByDate: false,
                animeNamingType: 3
            };
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
            <form id="configForm" action="config/postProcessing/savePostProcessing" method="post">
                <div id="config-components">
                    <ul>
                        <li><app-link href="#post-processing">Post Processing</app-link></li>
                        <li><app-link href="#episode-naming">Episode Naming</app-link></li>
                        <li><app-link href="#metadata">Metadata</app-link></li>
                    </ul>
                    <div id="post-processing" class="component-group">
                        <div class="component-group-desc">
                            <h3>Post-Processing</h3>
                            <p>Settings that dictate how Medusa should process completed downloads.</p>
                        </div>
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <input type="checkbox" name="process_automatically" id="process_automatically" ${'checked="checked"' if app.PROCESS_AUTOMATICALLY else ''}/>
                                <label for="process_automatically">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">Enable the automatic post processor to scan and process any files in your <i>Post Processing Dir</i>?</span>
                                </label>
                                <label class="nocheck" for="process_automatically">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc"><b>NOTE:</b> Do not use if you use an external Post Processing script</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="nocheck" for="tv_download_dir">
                                    <span class="component-title">Post Processing Dir</span>
                                    <input type="text" name="tv_download_dir" id="tv_download_dir" value="${app.TV_DOWNLOAD_DIR}" class="form-control input-sm input350"/>
                                </label>
                                <label class="nocheck">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">The folder where your download client puts the completed TV downloads.</span>
                                </label>
                                <label class="nocheck">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc"><b>NOTE:</b> Please use seperate downloading and completed folders in your download client if possible.</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="nocheck" for="process_method">
                                    <span class="component-title">Processing Method:</span>
                                    <span class="component-desc">
                                        <select name="process_method" id="process_method" class="form-control input-sm">
                                            % if pkgutil.find_loader('reflink') is not None:
                                                <% process_method_text = {'copy': "Copy", 'move': "Move", 'hardlink': "Hard Link", 'symlink' : "Symbolic Link", 'reflink': "Reference Link"} %>
                                                % for cur_action in ('copy', 'move', 'hardlink', 'symlink', 'reflink'):
                                                    <option value="${cur_action}" ${'selected="selected"' if app.PROCESS_METHOD == cur_action else ''}>${process_method_text[cur_action]}</option>
                                                % endfor
                                            % else:
                                                <% process_method_text = {'copy': "Copy", 'move': "Move", 'hardlink': "Hard Link", 'symlink' : "Symbolic Link"} %>
                                                % for cur_action in ('copy', 'move', 'hardlink', 'symlink'):
                                                    <option value="${cur_action}" ${'selected="selected"' if app.PROCESS_METHOD == cur_action else ''}>${process_method_text[cur_action]}</option>
                                                % endfor
                                            % endif
                                        </select>
                                    </span>
                                </label>
                                <label class="nocheck">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">What method should be used to put files into the library?</span>
                                </label>
                                <label class="nocheck">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc"><b>NOTE:</b> If you keep seeding torrents after they finish, please avoid the 'move' processing method to prevent errors.</span>
                                    <span class="component-desc">To use reference linking, the <app-link href="http://www.dereferer.org/?https://pypi.python.org/pypi/reflink/0.1.4">reflink package</app-link> needs to be installed.</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="nocheck">
                                    <span class="component-title">Auto Post-Processing Frequency</span>
                                    <input type="number" min="10" step="1" name="autopostprocessor_frequency" id="autopostprocessor_frequency" value="${app.AUTOPOSTPROCESSOR_FREQUENCY}" class="form-control input-sm input75" />
                                </label>
                                <label class="nocheck">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">Time in minutes to check for new files to auto post-process (min 10)</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <input type="checkbox" name="postpone_if_sync_files" id="postpone_if_sync_files" ${'checked="checked"' if app.POSTPONE_IF_SYNC_FILES else ''}/>
                                <label for="postpone_if_sync_files">
                                    <span class="component-title">Postpone post processing</span>
                                    <span class="component-desc">Wait to process a folder if sync files are present.</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="nocheck">
                                    <span class="component-title">Sync File Extensions</span>
                                    <input type="text" name="sync_files" id="sync_files" value="${', '.join(app.SYNC_FILES)}" class="form-control input-sm input350"/>
                                </label>
                                <label class="nocheck">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">comma seperated list of extensions or filename globs Medusa ignores when Post Processing</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <input type="checkbox" name="postpone_if_no_subs" id="postpone_if_no_subs" ${'checked="checked"' if app.POSTPONE_IF_NO_SUBS else ''}/>
                                <label for="postpone_if_no_subs">
                                    <span class="component-title">Postpone if no subtitle</span>
                                    <span class="component-desc">Wait to process a file until subtitles are present</span>
                                    <span class="component-desc">Language names are allowed in subtitle filename (en.srt, pt-br.srt, ita.srt, etc.)</span>
                                    <span class="component-desc">&nbsp;</span>
                                    <span class="component-desc"><b>NOTE:</b> Automatic post processor should be disabled to avoid files with pending subtitles being processed over and over.</span>
                                    <span class="component-desc">If you have any active show with subtitle search disabled, you must enable Automatic post processor.</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <input type="checkbox" name="rename_episodes" id="rename_episodes" ${'checked="checked"' if app.RENAME_EPISODES else ''}/>
                                <label for="rename_episodes">
                                    <span class="component-title">Rename Episodes</span>
                                    <span class="component-desc">Rename episode using the Episode Naming settings?</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <input type="checkbox" name="create_missing_show_dirs" id="create_missing_show_dirs" ${'checked="checked"' if app.CREATE_MISSING_SHOW_DIRS else ''}/>
                                <label for="create_missing_show_dirs">
                                    <span class="component-title">Create missing show directories</span>
                                    <span class="component-desc">Create missing show directories when they get deleted</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <input type="checkbox" name="add_shows_wo_dir" id="add_shows_wo_dir" ${'checked="checked"' if app.ADD_SHOWS_WO_DIR else ''}/>
                                <label for="add_shows_wo_dir">
                                    <span class="component-title">Add shows without directory</span>
                                    <span class="component-desc">Add shows without creating a directory (not recommended)</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <input type="checkbox" name="move_associated_files" id="move_associated_files" ${'checked="checked"' if app.MOVE_ASSOCIATED_FILES else ''}/>
                                <label for="move_associated_files">
                                    <span class="component-title">Delete associated files</span>
                                    <span class="component-desc">Delete srt/srr/sfv/etc files while post processing?</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="nocheck">
                                    <span class="component-title">Keep associated file extensions</span>
                                    <input type="text" name="allowed_extensions" id="allowed_extensions" value="${', '.join(app.ALLOWED_EXTENSIONS)}" class="form-control input-sm input350"/>
                                </label>
                                <label class="nocheck">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">Comma seperated list of associated file extensions Medusa should keep while post processing. Leaving it empty means all associated files will be deleted</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <input type="checkbox" name="nfo_rename" id="nfo_rename" ${'checked="checked"' if app.NFO_RENAME else ''}/>
                                <label for="nfo_rename">
                                    <span class="component-title">Rename .nfo file</span>
                                    <span class="component-desc">Rename the original .nfo file to .nfo-orig to avoid conflicts?</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <input type="checkbox" name="airdate_episodes" id="airdate_episodes" ${'checked="checked"' if app.AIRDATE_EPISODES else ''}/>
                                <label for="airdate_episodes">
                                    <span class="component-title">Change File Date</span>
                                    <span class="component-desc">Set last modified filedate to the date that the episode aired?</span>
                                </label>
                                <label class="nocheck">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc"><b>NOTE:</b> Some systems may ignore this feature.</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="nocheck" for="file_timestamp_timezone">
                                    <span class="component-title">Timezone for File Date:</span>
                                    <span class="component-desc">
                                        <select name="file_timestamp_timezone" id="file_timestamp_timezone" class="form-control input-sm">
                                            % for curTimezone in ('local','network'):
                                            <option value="${curTimezone}" ${'selected="selected"' if app.FILE_TIMESTAMP_TIMEZONE == curTimezone else ''}>${curTimezone}</option>
                                            % endfor
                                        </select>
                                    </span>
                                </label>
                                <label class="nocheck">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">What timezone should be used to change File Date?</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <input id="unpack" type="checkbox" name="unpack" ${'checked="checked"' if app.UNPACK else ''} />
                                <label for="unpack">
                                    <span class="component-title">Unpack</span>
                                    <span class="component-desc">Unpack any TV releases in your <i>TV Download Dir</i>?</span>
                                </label>
                                <label class="nocheck" for="unpack">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc"><b>NOTE:</b> Only working with RAR archive</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <input type="checkbox" name="del_rar_contents" id="del_rar_contents" ${'checked="checked"' if app.DELRARCONTENTS else ''}/>
                                <label for="del_rar_contents">
                                    <span class="component-title">Delete RAR contents</span>
                                    <span class="component-desc">Delete content of RAR files, even if Process Method not set to move?</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <input type="checkbox" name="no_delete" id="no_delete" ${'checked="checked"' if app.NO_DELETE else ''}/>
                                <label for="no_delete">
                                    <span class="component-title">Don't delete empty folders</span>
                                    <span class="component-desc">Leave empty folders when Post Processing?</span>
                                </label>
                                <label class="nocheck" for="no_delete">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc"><b>NOTE:</b> Can be overridden using manual Post Processing</span>
                                </label>
                            </div>
                            <div class="field-pair">
                                <label class="nocheck">
                                    <span class="component-title">Extra Scripts</span>
                                    <input type="text" name="extra_scripts" value="${'|'.join(app.EXTRA_SCRIPTS)}" class="form-control input-sm input350"/>
                                </label>
                                <label class="nocheck">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">See <app-link href="${app.EXTRA_SCRIPTS_URL}" class="wikie"><strong>Wiki</strong></app-link> for script arguments description and usage.</span>
                                </label>
                            </div>
                            <input type="submit" class="btn-medusa config_submitter" value="Save Changes" /><br>
                        </fieldset>
                    </div><!-- /component-group1 //-->
                    
                    <div id="episode-naming" class="component-group">
                        <div class="component-group-desc">
                            <h3>Episode Naming</h3>
                            <p>How Medusa will name and sort your episodes.</p>
                        </div>
                        <fieldset class="component-group-list">
                            
                            <!-- default name-pattern component -->
                            <name-pattern :pattern="pattern" :presets="presets"></name-pattern>

                            <!-- default sports name-pattern component -->
                            <name-pattern :pattern="pattern" :presets="presets" naming-custom="sports" :enabled-naming-custom="enabledSports"></name-pattern>

                            <!-- default airs by date name-pattern component -->
                            <name-pattern :pattern="pattern" :presets="presets" naming-custom="airs by date" :enabled-naming-custom="enabledAirByDate"></name-pattern>

                            <!-- default sports name-pattern component -->
                            <name-pattern :pattern="pattern" :presets="presets" naming-custom="anime" :anime-type="animeNamingType" :enabled-naming-custom="enabledAnime"></name-pattern>

                            <div class="field-pair">
                                <input type="checkbox" id="naming_strip_year"  name="naming_strip_year" ${'checked="checked"' if app.NAMING_STRIP_YEAR else ''}/>
                                <label for="naming_strip_year">
                                    <span class="component-title">Strip Show Year</span>
                                    <span class="component-desc">Remove the TV show's year when renaming the file?</span>
                                </label>
                                <label class="nocheck">
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc">Only applies to shows that have year inside parentheses</span>
                                </label>
                            </div>
                        </fieldset>
                    </div>
                    <div id="metadata" class="component-group">
                        <div class="component-group-desc">
                            <h3>Metadata</h3>
                            <p>The data associated to the data. These are files associated to a TV show in the form of images and text that, when supported, will enhance the viewing experience.</p>
                        </div>
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label>
                                    <span class="component-title">Metadata Type:</span>
                                    <span class="component-desc">
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
