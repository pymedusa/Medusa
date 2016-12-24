<%inherit file="/layouts/main.mako"/>
<%!
    import os.path
    import datetime
    from medusa import app
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import Quality, qualityPresets, statusStrings, qualityPresetStrings, cpu_presets, MULTI_EP_STRINGS
    from medusa import config
    from medusa import metadata
    from medusa.metadata.generic import GenericMetadata
    from medusa import naming
%>
<%block name="content">
<div id="content960">
    % if not header is UNDEFINED:
        <h1 class="header">${header}</h1>
    % else:
        <h1 class="title">${title}</h1>
    % endif
    <div id="config">
        <div id="config-content">
            <form id="configForm" action="config/postProcessing/savePostProcessing" method="post">
                <div id="config-components">
                    <ul>
                        ## @TODO: Fix this stupid hack
                        <script>document.write('<li><a href="' + document.location.href + '#post-processing">Post Processing</a></li>');</script>
                        <script>document.write('<li><a href="' + document.location.href + '#episode-naming">Episode Naming</a></li>');</script>
                        <script>document.write('<li><a href="' + document.location.href + '#metadata">Metadata</a></li>');</script>
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
                                            <% process_method_text = {'copy': "Copy", 'move': "Move", 'hardlink': "Hard Link", 'symlink' : "Symbolic Link"} %>
                                            % for cur_action in ('copy', 'move', 'hardlink', 'symlink'):
                                            <option value="${cur_action}" ${'selected="selected"' if app.PROCESS_METHOD == cur_action else ''}>${process_method_text[cur_action]}</option>
                                            % endfor
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
                                    <input type="text" name="sync_files" id="sync_files" value="${app.SYNC_FILES}" class="form-control input-sm input350"/>
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
                                    <input type="text" name="allowed_extensions" id="allowed_extensions" value="${app.ALLOWED_EXTENSIONS}" class="form-control input-sm input350"/>
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
                                    <span class="component-desc">See <a href="${app.EXTRA_SCRIPTS_URL}" class="wikie"><strong>Wiki</strong></a> for script arguments description and usage.</span>
                                </label>
                            </div>
                            <input type="submit" class="btn config_submitter" value="Save Changes" /><br>
                        </fieldset>
                    </div><!-- /component-group1 //-->
                    <div id="episode-naming" class="component-group">
                        <div class="component-group-desc">
                            <h3>Episode Naming</h3>
                            <p>How Medusa will name and sort your episodes.</p>
                        </div>
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label class="nocheck" for="name_presets">
                                    <span class="component-title">Name Pattern:</span>
                                    <span class="component-desc">
                                        <select id="name_presets" class="form-control input-sm">
                                            <% is_custom = True %>
                                            % for cur_preset in naming.name_presets:
                                                <% tmp = naming.test_name(cur_preset, anime_type=3) %>
                                                % if cur_preset == app.NAMING_PATTERN:
                                                    <% is_custom = False %>
                                                % endif
                                                <option id="${cur_preset}" ${'selected="selected"' if app.NAMING_PATTERN == cur_preset else ''}>${os.path.join(tmp['dir'], tmp['name'])}</option>
                                            % endfor
                                            <option id="${app.NAMING_PATTERN}" ${'selected="selected"' if is_custom else ''}>Custom...</option>
                                        </select>
                                    </span>
                                </label>
                            </div>
                            <div id="naming_custom">
                                <div class="field-pair" style="padding-top: 0;">
                                    <label class="nocheck">
                                        <span class="component-title">
                                            &nbsp;
                                        </span>
                                        <span class="component-desc">
                                            <input type="text" name="naming_pattern" id="naming_pattern" value="${app.NAMING_PATTERN}" class="form-control input-sm input350"/>
                                            <img src="images/legend16.png" width="16" height="16" alt="[Toggle Key]" id="show_naming_key" title="Toggle Naming Legend" class="legend" class="legend" />
                                        </span>
                                    </label>
                                </div>
                                <div id="naming_key" class="nocheck" style="display: none;">
                                      <table class="Key">
                                        <thead>
                                            <tr>
                                              <th class="align-right">Meaning</th>
                                              <th>Pattern</th>
                                              <th width="60%">Result</th>
                                            </tr>
                                        </thead>
                                        <tfoot>
                                            <tr>
                                              <th colspan="3">Use lower case if you want lower case names (eg. %sn, %e.n, %q_n etc)</th>
                                            </tr>
                                        </tfoot>
                                        <tbody>
                                            <tr>
                                              <td class="align-right"><b>Show Name:</b></td>
                                              <td>%SN</td>
                                              <td>Show Name</td>
                                            </tr>
                                            <tr class="even">
                                              <td>&nbsp;</td>
                                              <td>%S.N</td>
                                              <td>Show.Name</td>
                                            </tr>
                                            <tr>
                                              <td>&nbsp;</td>
                                              <td>%S_N</td>
                                              <td>Show_Name</td>
                                            </tr>
                                            <tr class="even">
                                              <td class="align-right"><b>Season Number:</b></td>
                                              <td>%S</td>
                                              <td>2</td>
                                            </tr>
                                            <tr>
                                              <td>&nbsp;</td>
                                              <td>%0S</td>
                                              <td>02</td>
                                            </tr>
                                            <tr class="even">
                                              <td class="align-right"><b>XEM Season Number:</b></td>
                                              <td>%XS</td>
                                              <td>2</td>
                                            </tr>
                                            <tr>
                                              <td>&nbsp;</td>
                                              <td>%0XS</td>
                                              <td>02</td>
                                            </tr>
                                            <tr class="even">
                                              <td class="align-right"><b>Episode Number:</b></td>
                                              <td>%E</td>
                                              <td>3</td>
                                            </tr>
                                            <tr>
                                              <td>&nbsp;</td>
                                              <td>%0E</td>
                                              <td>03</td>
                                            </tr>
                                            <tr class="even">
                                              <td class="align-right"><b>XEM Episode Number:</b></td>
                                              <td>%XE</td>
                                              <td>3</td>
                                            </tr>
                                            <tr>
                                              <td>&nbsp;</td>
                                              <td>%0XE</td>
                                              <td>03</td>
                                            </tr>
                                            <tr class="even">
                                              <td class="align-right"><b>Episode Name:</b></td>
                                              <td>%EN</td>
                                              <td>Episode Name</td>
                                            </tr>
                                            <tr>
                                              <td>&nbsp;</td>
                                              <td>%E.N</td>
                                              <td>Episode.Name</td>
                                            </tr>
                                            <tr class="even">
                                              <td>&nbsp;</td>
                                              <td>%E_N</td>
                                              <td>Episode_Name</td>
                                            </tr>
                                            <tr>
                                              <td class="align-right"><b>Air Date:</b></td>
                                              <td>%M</td>
                                              <td>${datetime.date.today().month}</td>
                                            </tr>
                                            <tr class="even">
                                              <td>&nbsp;</td>
                                              <td>%D</td>
                                              <td>${datetime.date.today().day}</td>
                                            </tr>
                                            <tr>
                                              <td>&nbsp;</td>
                                              <td>%Y</td>
                                              <td>${datetime.date.today().year}</td>
                                            </tr>
                                            <tr>
                                              <td class="align-right"><b>Post-Processing Date:</b></td>
                                              <td>%CM</td>
                                              <td>${datetime.date.today().month}</td>
                                            </tr>
                                            <tr class="even">
                                              <td>&nbsp;</td>
                                              <td>%CD</td>
                                              <td>${datetime.date.today().day}</td>
                                            </tr>
                                            <tr>
                                              <td>&nbsp;</td>
                                              <td>%CY</td>
                                              <td>${datetime.date.today().year}</td>
                                            </tr>
                                            <tr>
                                              <td class="align-right"><b>Quality:</b></td>
                                              <td>%QN</td>
                                              <td>720p BluRay</td>
                                            </tr>
                                            <tr class="even">
                                              <td>&nbsp;</td>
                                              <td>%Q.N</td>
                                              <td>720p.BluRay</td>
                                            </tr>
                                            <tr>
                                              <td>&nbsp;</td>
                                              <td>%Q_N</td>
                                              <td>720p_BluRay</td>
                                            </tr>
                                            <tr>
                                              <td class="align-right"><b>Scene Quality:</b></td>
                                              <td>%SQN</td>
                                              <td>720p HDTV x264</td>
                                            </tr>
                                            <tr class="even">
                                              <td>&nbsp;</td>
                                              <td>%SQ.N</td>
                                              <td>720p.HDTV.x264</td>
                                            </tr>
                                            <tr>
                                              <td>&nbsp;</td>
                                              <td>%SQ_N</td>
                                              <td>720p_HDTV_x264</td>
                                            </tr>
                                            <tr class="even">
                                              <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="Multi-EP style is ignored"></i> <b>Release Name:</b></td>
                                              <td>%RN</td>
                                              <td>Show.Name.S02E03.HDTV.x264-RLSGROUP</td>
                                            </tr>
                                            <tr>
                                              <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="'${app.UNKNOWN_RELEASE_GROUP}' is used in place of RLSGROUP if it could not be properly detected"></i> <b>Release Group:</b></td>
                                              <td>%RG</td>
                                              <td>RLSGROUP</td>
                                            </tr>
                                            <tr class="even">
                                              <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="If episode is proper/repack add 'proper' to name."></i> <b>Release Type:</b></td>
                                              <td>%RT</td>
                                              <td>PROPER</td>
                                            </tr>
                                        </tbody>
                                      </table>
                                      <br>
                                </div>
                            </div>
                            <div class="field-pair">
                                <label class="nocheck" for="naming_multi_ep">
                                    <span class="component-title">Multi-Episode Style:</span>
                                    <span class="component-desc">
                                        <select id="naming_multi_ep" name="naming_multi_ep" class="form-control input-sm">
                                        % for cur_multi_ep in sorted(MULTI_EP_STRINGS.iteritems(), key=lambda x: x[1]):
                                            <option value="${cur_multi_ep[0]}" ${('', 'selected="selected"')[cur_multi_ep[0] == app.NAMING_MULTI_EP]}>${cur_multi_ep[1]}</option>
                                        % endfor
                                        </select>
                                    </span>
                                </label>
                            </div>
                            <div id="naming_example_div">
                                <h3>Single-EP Sample:</h3>
                                <div class="example">
                                    <span class="jumbo" id="naming_example">&nbsp;</span>
                                </div>
                                <br>
                            </div>
                            <div id="naming_example_multi_div">
                                <h3>Multi-EP sample:</h3>
                                <div class="example">
                                    <span class="jumbo" id="naming_example_multi">&nbsp;</span>
                                </div>
                                <br>
                            </div>
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
                            <div class="field-pair">
                                <input type="checkbox" class="enabler" id="naming_custom_abd" name="naming_custom_abd" ${'checked="checked"' if app.NAMING_CUSTOM_ABD else ''}/>
                                <label for="naming_custom_abd">
                                    <span class="component-title">Custom Air-By-Date</span>
                                    <span class="component-desc">Name Air-By-Date shows differently than regular shows?</span>
                                </label>
                            </div>
                            <div id="content_naming_custom_abd">
                                <div class="field-pair">
                                    <label class="nocheck" for="name_abd_presets">
                                        <span class="component-title">Name Pattern:</span>
                                        <span class="component-desc">
                                            <select id="name_abd_presets" class="form-control input-sm">
                                                <% is_abd_custom = True %>
                                                % for cur_preset in naming.name_abd_presets:
                                                    <% tmp = naming.test_name(cur_preset) %>
                                                    % if cur_preset == app.NAMING_ABD_PATTERN:
                                                        <% is_abd_custom = False %>
                                                    % endif
                                                    <option id="${cur_preset}" ${'selected="selected"' if app.NAMING_ABD_PATTERN == cur_preset else ''}>${os.path.join(tmp['dir'], tmp['name'])}</option>
                                                % endfor
                                                <option id="${app.NAMING_ABD_PATTERN}" ${'selected="selected"' if is_abd_custom else ''}>Custom...</option>
                                            </select>
                                        </span>
                                    </label>
                                </div>
                                <div id="naming_abd_custom">
                                    <div class="field-pair">
                                        <label class="nocheck">
                                            <span class="component-title">
                                                &nbsp;
                                            </span>
                                            <span class="component-desc">
                                                <input type="text" name="naming_abd_pattern" id="naming_abd_pattern" value="${app.NAMING_ABD_PATTERN}" class="form-control input-sm input350"/>
                                                <img src="images/legend16.png" width="16" height="16" alt="[Toggle Key]" id="show_naming_abd_key" title="Toggle ABD Naming Legend" class="legend" />
                                            </span>
                                        </label>
                                    </div>
                                    <div id="naming_abd_key" class="nocheck" style="display: none;">
                                          <table class="Key">
                                            <thead>
                                                <tr>
                                                  <th class="align-right">Meaning</th>
                                                  <th>Pattern</th>
                                                  <th width="60%">Result</th>
                                                </tr>
                                            </thead>
                                            <tfoot>
                                                <tr>
                                                  <th colspan="3">Use lower case if you want lower case names (eg. %sn, %e.n, %q_n etc)</th>
                                                </tr>
                                            </tfoot>
                                            <tbody>
                                                <tr>
                                                  <td class="align-right"><b>Show Name:</b></td>
                                                  <td>%SN</td>
                                                  <td>Show Name</td>
                                                </tr>
                                                <tr class="even">
                                                  <td>&nbsp;</td>
                                                  <td>%S.N</td>
                                                  <td>Show.Name</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%S_N</td>
                                                  <td>Show_Name</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><b>Regular Air Date:</b></td>
                                                  <td>%AD</td>
                                                  <td>2010 03 09</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%A.D</td>
                                                  <td>2010.03.09</td>
                                                </tr>
                                                <tr class="even">
                                                  <td>&nbsp;</td>
                                                  <td>%A_D</td>
                                                  <td>2010_03_09</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%A-D</td>
                                                  <td>2010-03-09</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><b>Episode Name:</b></td>
                                                  <td>%EN</td>
                                                  <td>Episode Name</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%E.N</td>
                                                  <td>Episode.Name</td>
                                                </tr>
                                                <tr class="even">
                                                  <td>&nbsp;</td>
                                                  <td>%E_N</td>
                                                  <td>Episode_Name</td>
                                                </tr>
                                                <tr>
                                                  <td class="align-right"><b>Quality:</b></td>
                                                  <td>%QN</td>
                                                  <td>720p BluRay</td>
                                                </tr>
                                                <tr class="even">
                                                  <td>&nbsp;</td>
                                                  <td>%Q.N</td>
                                                  <td>720p.BluRay</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%Q_N</td>
                                                  <td>720p_BluRay</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><b>Year:</b></td>
                                                  <td>%Y</td>
                                                  <td>2010</td>
                                                </tr>
                                                <tr>
                                                  <td class="align-right"><b>Month:</b></td>
                                                  <td>%M</td>
                                                  <td>3</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right">&nbsp;</td>
                                                  <td>%0M</td>
                                                  <td>03</td>
                                                </tr>
                                                <tr>
                                                  <td class="align-right"><b>Day:</b></td>
                                                  <td>%D</td>
                                                  <td>9</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right">&nbsp;</td>
                                                  <td>%0D</td>
                                                  <td>09</td>
                                                </tr>
                                                <tr>
                                                  <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="Multi-EP style is ignored"></i> <b>Release Name:</b></td>
                                                  <td>%RN</td>
                                                  <td>Show.Name.2010.03.09.HDTV.x264-RLSGROUP</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="'${app.UNKNOWN_RELEASE_GROUP}' is used in place of RLSGROUP if it could not be properly detected"></i> <b>Release Group:</b></td>
                                                  <td>%RG</td>
                                                  <td>RLSGROUP</td>
                                                </tr>
                                                <tr>
                                                  <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="If episode is proper/repack add 'proper' to name."></i> <b>Release Type:</b></td>
                                                  <td>%RT</td>
                                                  <td>PROPER</td>
                                                </tr>
                                            </tbody>
                                          </table>
                                          <br>
                                    </div>
                                </div><!-- /naming_abd_custom -->
                                <div id="naming_abd_example_div">
                                    <h3>Sample:</h3>
                                    <div class="example">
                                        <span class="jumbo" id="naming_abd_example">&nbsp;</span>
                                    </div>
                                    <br>
                                </div>
                            </div><!-- /naming_abd_different -->
                            <div class="field-pair">
                                <input type="checkbox" class="enabler" id="naming_custom_sports" name="naming_custom_sports" ${'checked="checked"' if app.NAMING_CUSTOM_SPORTS else ''}/>
                                <label for="naming_custom_sports">
                                    <span class="component-title">Custom Sports</span>
                                    <span class="component-desc">Name Sports shows differently than regular shows?</span>
                                </label>
                            </div>
                            <div id="content_naming_custom_sports">
                                <div class="field-pair">
                                    <label class="nocheck" for="name_sports_presets">
                                        <span class="component-title">Name Pattern:</span>
                                        <span class="component-desc">
                                            <select id="name_sports_presets" class="form-control input-sm">
                                                <% is_sports_custom = True %>
                                                % for cur_preset in naming.name_sports_presets:
                                                    <% tmp = naming.test_name(cur_preset) %>
                                                    % if cur_preset == app.NAMING_SPORTS_PATTERN:
                                                        <% is_sports_custom = False %>
                                                    % endif
                                                    <option id="${cur_preset}" ${'selected="selected"' if app.NAMING_SPORTS_PATTERN == cur_preset else ''}>${os.path.join(tmp['dir'], tmp['name'])}</option>
                                                % endfor
                                                <option id="${app.NAMING_SPORTS_PATTERN}" ${'selected="selected"' if is_sports_custom else ''}>Custom...</option>
                                            </select>
                                        </span>
                                    </label>
                                </div>
                                <div id="naming_sports_custom">
                                    <div class="field-pair" style="padding-top: 0;">
                                        <label class="nocheck">
                                            <span class="component-title">
                                                &nbsp;
                                            </span>
                                            <span class="component-desc">
                                                <input type="text" name="naming_sports_pattern" id="naming_sports_pattern" value="${app.NAMING_SPORTS_PATTERN}" class="form-control input-sm input350"/>
                                                <img src="images/legend16.png" width="16" height="16" alt="[Toggle Key]" id="show_naming_sports_key" title="Toggle Sports Naming Legend" class="legend" />
                                            </span>
                                        </label>
                                    </div>
                                    <div id="naming_sports_key" class="nocheck" style="display: none;">
                                          <table class="Key">
                                            <thead>
                                                <tr>
                                                  <th class="align-right">Meaning</th>
                                                  <th>Pattern</th>
                                                  <th width="60%">Result</th>
                                                </tr>
                                            </thead>
                                            <tfoot>
                                                <tr>
                                                  <th colspan="3">Use lower case if you want lower case names (eg. %sn, %e.n, %q_n etc)</th>
                                                </tr>
                                            </tfoot>
                                            <tbody>
                                                <tr>
                                                  <td class="align-right"><b>Show Name:</b></td>
                                                  <td>%SN</td>
                                                  <td>Show Name</td>
                                                </tr>
                                                <tr class="even">
                                                  <td>&nbsp;</td>
                                                  <td>%S.N</td>
                                                  <td>Show.Name</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%S_N</td>
                                                  <td>Show_Name</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><b>Sports Air Date:</b></td>
                                                  <td>%AD</td>
                                                  <td>9 Mar 2011</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%A.D</td>
                                                  <td>9.Mar.2011</td>
                                                </tr>
                                                <tr class="even">
                                                  <td>&nbsp;</td>
                                                  <td>%A_D</td>
                                                  <td>9_Mar_2011</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%A-D</td>
                                                  <td>9-Mar-2011</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><b>Episode Name:</b></td>
                                                  <td>%EN</td>
                                                  <td>Episode Name</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%E.N</td>
                                                  <td>Episode.Name</td>
                                                </tr>
                                                <tr class="even">
                                                  <td>&nbsp;</td>
                                                  <td>%E_N</td>
                                                  <td>Episode_Name</td>
                                                </tr>
                                                <tr>
                                                  <td class="align-right"><b>Quality:</b></td>
                                                  <td>%QN</td>
                                                  <td>720p BluRay</td>
                                                </tr>
                                                <tr class="even">
                                                  <td>&nbsp;</td>
                                                  <td>%Q.N</td>
                                                  <td>720p.BluRay</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%Q_N</td>
                                                  <td>720p_BluRay</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><b>Year:</b></td>
                                                  <td>%Y</td>
                                                  <td>2010</td>
                                                </tr>
                                                <tr>
                                                  <td class="align-right"><b>Month:</b></td>
                                                  <td>%M</td>
                                                  <td>3</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right">&nbsp;</td>
                                                  <td>%0M</td>
                                                  <td>03</td>
                                                </tr>
                                                <tr>
                                                  <td class="align-right"><b>Day:</b></td>
                                                  <td>%D</td>
                                                  <td>9</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right">&nbsp;</td>
                                                  <td>%0D</td>
                                                  <td>09</td>
                                                </tr>
                                                <tr>
                                                  <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="Multi-EP style is ignored"></i> <b>Release Name:</b></td>
                                                  <td>%RN</td>
                                                  <td>Show.Name.9th.Mar.2011.HDTV.x264-RLSGROUP</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="'${app.UNKNOWN_RELEASE_GROUP}' is used in place of RLSGROUP if it could not be properly detected"></i> <b>Release Group:</b></td>
                                                  <td>%RG</td>
                                                  <td>RLSGROUP</td>
                                                </tr>
                                                <tr>
                                                  <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="If episode is proper/repack add 'proper' to name."></i> <b>Release Type:</b></td>
                                                  <td>%RT</td>
                                                  <td>PROPER</td>
                                                </tr>
                                            </tbody>
                                          </table>
                                          <br>
                                    </div>
                                </div><!-- /naming_sports_custom -->
                                <div id="naming_sports_example_div">
                                    <h3>Sample:</h3>
                                    <div class="example">
                                        <span class="jumbo" id="naming_sports_example">&nbsp;</span>
                                    </div>
                                    <br>
                                </div>
                            </div><!-- /naming_sports_different -->
                            <!-- naming_anime_custom -->
                            <div class="field-pair">
                                <input type="checkbox" class="enabler" id="naming_custom_anime" name="naming_custom_anime" ${'checked="checked"' if app.NAMING_CUSTOM_ANIME else ''}/>
                                <label for="naming_custom_anime">
                                    <span class="component-title">Custom Anime</span>
                                    <span class="component-desc">Name Anime shows differently than regular shows?</span>
                                </label>
                            </div>
                            <div id="content_naming_custom_anime">
                                <div class="field-pair">
                                    <label class="nocheck" for="name_anime_presets">
                                        <span class="component-title">Name Pattern:</span>
                                        <span class="component-desc">
                                            <select id="name_anime_presets" class="form-control input-sm">
                                                <% is_anime_custom = True %>
                                                % for cur_preset in naming.name_anime_presets:
                                                    <% tmp = naming.test_name(cur_preset) %>
                                                    % if cur_preset == app.NAMING_ANIME_PATTERN:
                                                        <% is_anime_custom = False %>
                                                    % endif
                                                    <option id="${cur_preset}" ${'selected="selected"' if cur_preset == app.NAMING_ANIME_PATTERN else ''}>${os.path.join(tmp['dir'], tmp['name'])}</option>
                                                % endfor
                                                <option id="${app.NAMING_ANIME_PATTERN}" ${'selected="selected"' if is_anime_custom else ''}>Custom...</option>
                                            </select>
                                        </span>
                                    </label>
                                </div>
                                <div id="naming_anime_custom">
                                    <div class="field-pair" style="padding-top: 0;">
                                        <label class="nocheck">
                                            <span class="component-title">
                                                &nbsp;
                                            </span>
                                            <span class="component-desc">
                                                <input type="text" name="naming_anime_pattern" id="naming_anime_pattern" value="${app.NAMING_ANIME_PATTERN}" class="form-control input-sm input350"/>
                                                <img src="images/legend16.png" width="16" height="16" alt="[Toggle Key]" id="show_naming_anime_key" title="Toggle Anime Naming Legend" class="legend" />
                                            </span>
                                        </label>
                                    </div>
                                    <div id="naming_anime_key" class="nocheck" style="display: none;">
                                          <table class="Key">
                                            <thead>
                                                <tr>
                                                  <th class="align-right">Meaning</th>
                                                  <th>Pattern</th>
                                                  <th width="60%">Result</th>
                                                </tr>
                                            </thead>
                                            <tfoot>
                                                <tr>
                                                  <th colspan="3">Use lower case if you want lower case names (eg. %sn, %e.n, %q_n etc)</th>
                                                </tr>
                                            </tfoot>
                                            <tbody>
                                                <tr>
                                                  <td class="align-right"><b>Show Name:</b></td>
                                                  <td>%SN</td>
                                                  <td>Show Name</td>
                                                </tr>
                                                <tr class="even">
                                                  <td>&nbsp;</td>
                                                  <td>%S.N</td>
                                                  <td>Show.Name</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%S_N</td>
                                                  <td>Show_Name</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><b>Season Number:</b></td>
                                                  <td>%S</td>
                                                  <td>2</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%0S</td>
                                                  <td>02</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><b>XEM Season Number:</b></td>
                                                  <td>%XS</td>
                                                  <td>2</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%0XS</td>
                                                  <td>02</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><b>Episode Number:</b></td>
                                                  <td>%E</td>
                                                  <td>3</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%0E</td>
                                                  <td>03</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><b>XEM Episode Number:</b></td>
                                                  <td>%XE</td>
                                                  <td>3</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%0XE</td>
                                                  <td>03</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><b>Episode Name:</b></td>
                                                  <td>%EN</td>
                                                  <td>Episode Name</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%E.N</td>
                                                  <td>Episode.Name</td>
                                                </tr>
                                                <tr class="even">
                                                  <td>&nbsp;</td>
                                                  <td>%E_N</td>
                                                  <td>Episode_Name</td>
                                                </tr>
                                                <tr>
                                                  <td class="align-right"><b>Quality:</b></td>
                                                  <td>%QN</td>
                                                  <td>720p BluRay</td>
                                                </tr>
                                                <tr class="even">
                                                  <td>&nbsp;</td>
                                                  <td>%Q.N</td>
                                                  <td>720p.BluRay</td>
                                                </tr>
                                                <tr>
                                                  <td>&nbsp;</td>
                                                  <td>%Q_N</td>
                                                  <td>720p_BluRay</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="Multi-EP style is ignored"></i> <b>Release Name:</b></td>
                                                  <td>%RN</td>
                                                  <td>Show.Name.S02E03.HDTV.x264-RLSGROUP</td>
                                                </tr>
                                                <tr>
                                                  <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="'${app.UNKNOWN_RELEASE_GROUP}' is used in place of RLSGROUP if it could not be properly detected"></i> <b>Release Group:</b></td>
                                                  <td>%RG</td>
                                                  <td>RLSGROUP</td>
                                                </tr>
                                                <tr class="even">
                                                  <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="If episode is proper/repack add 'proper' to name."></i> <b>Release Type:</b></td>
                                                  <td>%RT</td>
                                                  <td>PROPER</td>
                                                </tr>
                                            </tbody>
                                          </table>
                                          <br>
                                    </div>
                                </div><!-- /naming_anime_custom -->
                                <div class="field-pair">
                                    <label class="nocheck" for="naming_anime_multi_ep">
                                        <span class="component-title">Multi-Episode Style:</span>
                                        <span class="component-desc">
                                            <select id="naming_anime_multi_ep" name="naming_anime_multi_ep" class="form-control input-sm">
                                            % for cur_multi_ep in sorted(MULTI_EP_STRINGS.iteritems(), key=lambda x: x[1]):
                                                <option value="${cur_multi_ep[0]}" ${('', 'selected="selected" class="selected"')[cur_multi_ep[0] == app.NAMING_ANIME_MULTI_EP]}>${cur_multi_ep[1]}</option>
                                            % endfor
                                            </select>
                                        </span>
                                    </label>
                                </div>
                                <div id="naming_example_anime_div">
                                    <h3>Single-EP Anime Sample:</h3>
                                    <div class="example">
                                        <span class="jumbo" id="naming_example_anime">&nbsp;</span>
                                    </div>
                                    <br>
                                </div>
                                <div id="naming_example_multi_anime_div">
                                    <h3>Multi-EP Anime sample:</h3>
                                    <div class="example">
                                        <span class="jumbo" id="naming_example_multi_anime">&nbsp;</span>
                                    </div>
                                    <br>
                                </div>
                                <div class="field-pair">
                                    <input type="radio" name="naming_anime" id="naming_anime" value="1" ${'checked="checked"' if app.NAMING_ANIME == 1 else ''}/>
                                    <label for="naming_anime">
                                        <span class="component-title">Add Absolute Number</span>
                                        <span class="component-desc">Add the absolute number to the season/episode format?</span>
                                    </label>
                                    <label class="nocheck">
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Only applies to animes. (eg. S15E45 - 310 vs S15E45)</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <input type="radio" name="naming_anime" id="naming_anime_only" value="2" ${'checked="checked"' if app.NAMING_ANIME == 2 else ''}/>
                                    <label for="naming_anime_only">
                                        <span class="component-title">Only Absolute Number</span>
                                        <span class="component-desc">Replace season/episode format with absolute number</span>
                                    </label>
                                    <label class="nocheck">
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Only applies to animes.</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <input type="radio" name="naming_anime" id="naming_anime_none" value="3" ${'checked="checked"' if app.NAMING_ANIME == 3 else ''}/>
                                    <label for="naming_anime_none">
                                        <span class="component-title">No Absolute Number</span>
                                        <span class="component-desc">Dont include the absolute number</span>
                                    </label>
                                    <label class="nocheck">
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Only applies to animes.</span>
                                    </label>
                                </div>
                            </div><!-- /naming_anime_different -->
                            <input type="submit" class="btn config_submitter" value="Save Changes" /><br>
                        </fieldset>
                    </div><!-- /component-group2 //-->
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
                            <input type="submit" class="btn config_submitter" value="Save Changes" /><br>
                        </fieldset>
                    </div><!-- /component-group3 //-->
                    <br>
                    <h6 class="pull-right"><b>All non-absolute folder locations are relative to <span class="path">${app.DATA_DIR}</span></b> </h6>
                    <input type="submit" class="btn pull-left config_submitter button" value="Save Changes" />
            </form>
        </div>
    </div>
    <div class="clearfix"></div>
</div><!-- #content960 //-->
</div>
</%block>
