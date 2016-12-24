<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa import common
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import Quality, qualityPresets, qualityPresetStrings, statusStrings
    from medusa.helper import exceptions
%>
<%block name="scripts">
<%
    if quality_value is not None:
        initial_quality = int(quality_value)
    else:
        initial_quality = common.SD
    allowed_qualities, preferred_qualities = common.Quality.split_quality(initial_quality)
%>
<script type="text/javascript" src="js/quality-chooser.js?${sbPID}"></script>
<script type="text/javascript" src="js/mass-edit.js?${sbPID}"></script>
</%block>
<%block name="content">
<div id="config">
    <div id="config-content">
        <form action="manage/massEditSubmit" method="post">
            <input type="hidden" name="toEdit" value="${showList}" />
            <div id="config-components">
                ## @TODO: Fix this stupid hack
                <script>document.write('<ul><li><a href="' + document.location.href + '#core-component-group1">Main</a></li></ul>');</script>
                <div id="core-component-group1">
                    <div class="component-group">
                        <h3>Main Settings</h3>
                        <em class="note">NOTE: Changing any settings marked with (<span class="separator">*</span>) will force a refresh of the selected shows.</em><br>
                        <br>
                        <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="shows">
                                <span class="component-title">Selected Shows</span>
                                <span class="component-desc">
                                    <span style="font-size: 14px;">${', '.join(sorted(showNames))}</span><br>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="edit_root_dir_0">
                                <span class="component-title">Root Directories (<span class="separator">*</span>)</span>
                                <span class="component-desc">
                                    <table class="defaultTable" cellspacing="1" cellpadding="0" border="0">
                                        <thead>
                                            <tr>
                                                <th class="nowrap tablesorter-header">Current</th>
                                                <th class="nowrap tablesorter-header">New</th>
                                                <th class="nowrap tablesorter-header" style="width: 140px;">-</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                        % for cur_dir in root_dir_list:
                                            <% cur_index = root_dir_list.index(cur_dir) %>
                                            <tr class="listing-default">
                                                <td align="center">${cur_dir}</td>
                                                <td align="center" id="display_new_root_dir_${cur_index}">${cur_dir}</td>
                                                <td>
                                                    <a href="#" class="btn edit_root_dir" class="edit_root_dir" id="edit_root_dir_${cur_index}">Edit</a>
                                                    <a href="#" class="btn delete_root_dir" class="delete_root_dir" id="delete_root_dir_${cur_index}">Delete</a>
                                                    <input type="hidden" name="orig_root_dir_${cur_index}" value="${cur_dir}" />
                                                    <input type="text" style="display: none;" name="new_root_dir_${cur_index}" id="new_root_dir_${cur_index}" class="new_root_dir" value="${cur_dir}"/>
                                                </td>
                                            </tr>
                                        % endfor
                                        </tbody>
                                    </table>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="qualityPreset">
                                <span class="component-title">Preferred Quality</span>
                                <span class="component-desc">
                                    <%
                                        if quality_value is not None:
                                            initial_quality = int(quality_value)
                                        else:
                                            initial_quality = common.SD
                                        allowed_qualities, preferred_qualities = common.Quality.split_quality(initial_quality)
                                    %>
                                    <select id="qualityPreset" name="quality_preset" class="form-control form-control-inline input-sm">
                                        <option value="keep">&lt; Keep &gt;</option>
                                        <% selected = None %>
                                        <option value="0" ${'selected="selected"' if quality_value is not None and quality_value not in common.qualityPresets else ''}>Custom</option>
                                        % for curPreset in sorted(common.qualityPresets):
                                        <option value="${curPreset}" ${'selected="selected"' if quality_value == curPreset else ''}>${common.qualityPresetStrings[curPreset]}</option>
                                        % endfor
                                    </select>
                                    <div id="customQuality" style="padding-left: 0;">
                                        <div style="padding-right: 40px; text-align: left; float: left;">
                                            <h5>Allowed</h5>
                                            <% anyQualityList = filter(lambda x: x > common.Quality.NONE, common.Quality.qualityStrings) %>
                                            <select id="allowed_qualities" name="allowed_qualities" multiple="multiple" size="${len(anyQualityList)}" class="form-control form-control-inline input-sm">
                                                % for curQuality in sorted(anyQualityList):
                                                <option value="${curQuality}" ${'selected="selected"' if curQuality in allowed_qualities else ''}>${common.Quality.qualityStrings[curQuality]}</option>
                                                % endfor
                                            </select>
                                        </div>
                                        <div style="text-align: left; float: left;">
                                            <h5>Preferred</h5>
                                            <% bestQualityList = filter(lambda x: x >= common.Quality.SDTV, common.Quality.qualityStrings) %>
                                            <select id="preferred_qualities" name="preferred_qualities" multiple="multiple" size="${len(bestQualityList)}" class="form-control form-control-inline input-sm">
                                                % for curQuality in sorted(bestQualityList):
                                                <option value="${curQuality}" ${'selected="selected"' if curQuality in preferred_qualities else ''}>${common.Quality.qualityStrings[curQuality]}</option>
                                                % endfor
                                            </select>
                                        </div>
                                    </div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="edit_flatten_folders">
                                <span class="component-title">Season folders (<span class="separator">*</span>)</span>
                                <span class="component-desc">
                                    <select id="" name="flatten_folders" class="form-control form-control-inline input-sm">
                                        <option value="keep" ${'selected="selected"' if flatten_folders_value is None else ''}>&lt; Keep &gt;</option>
                                        <option value="enable" ${'selected="selected"' if flatten_folders_value == 0 else ''}>Yes</option>
                                        <option value="disable" ${'selected="selected"' if flatten_folders_value == 1 else ''}>No</option>
                                    </select><br>
                                    Group episodes by season folder (set to "No" to store in a single folder).
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="edit_paused">
                                <span class="component-title">Paused</span>
                                <span class="component-desc">
                                    <select id="edit_paused" name="paused" class="form-control form-control-inline input-sm">
                                        <option value="keep" ${'selected="selected"' if paused_value is None else ''}>&lt; Keep &gt;</option>
                                        <option value="enable" ${'selected="selected"' if paused_value == 1 else ''}>Yes</option>
                                        <option value="disable" ${'selected="selected"' if paused_value == 0 else ''}>No</option>
                                    </select><br>
                                    Pause these shows (Medusa will not download episodes).
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="edit_default_ep_status">
                                <span class="component-title">Default Episode Status</span>
                                <span class="component-desc">
                                    <select id="edit_default_ep_status" name="default_ep_status" class="form-control form-control-inline input-sm">
                                        <option value="keep">&lt; Keep &gt;</option>
                                        % for cur_status in [WANTED, SKIPPED, IGNORED]:
                                        <option value="${cur_status}" ${'selected="selected"' if cur_status == default_ep_status_value else ''}>${statusStrings[cur_status]}</option>
                                        % endfor
                                    </select><br>
                                    This will set the status for future episodes.
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="edit_scene">
                                <span class="component-title">Scene Numbering</span>
                                <span class="component-desc">
                                    <select id="edit_scene" name="scene" class="form-control form-control-inline input-sm">
                                        <option value="keep" ${'selected="selected"' if scene_value is None else ''}>&lt; Keep &gt;</option>
                                        <option value="enable" ${'selected="selected"' if scene_value == 1 else ''}>Yes</option>
                                        <option value="disable" ${'selected="selected"' if scene_value == 0 else ''}>No</option>
                                    </select><br>
                                    Search by scene numbering (set to "No" to search by indexer numbering).
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="edit_anime">
                                <span class="component-title">Anime</span>
                                <span class="component-desc">
                                    <select id="edit_anime" name="anime" class="form-control form-control-inline input-sm">
                                        <option value="keep" ${'selected="selected"' if anime_value is None else ''}>&lt; Keep &gt;</option>
                                        <option value="enable" ${'selected="selected"' if anime_value == 1 else ''}>Yes</option>
                                        <option value="disable" ${'selected="selected"' if anime_value == 0 else ''}>No</option>
                                    </select><br>
                                    Set if these shows are Anime and episodes are released as Show.265 rather than Show.S02E03
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="edit_sports">
                                <span class="component-title">Sports</span>
                                <span class="component-desc">
                                    <select id="edit_sports" name="sports" class="form-control form-control-inline input-sm">
                                        <option value="keep" ${'selected="selected"' if sports_value is None else ''}>&lt; Keep &gt;</option>
                                        <option value="enable" ${'selected="selected"' if sports_value == 1 else ''}>Yes</option>
                                        <option value="disable" ${'selected="selected"' if sports_value == 0 else ''}>No</option>
                                    </select><br>
                                    Set if these shows are sporting or MMA events released as Show.03.02.2010 rather than Show.S02E03.<br>
                                    <span style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</span>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="edit_air_by_date">
                                <span class="component-title">Air by date</span>
                                <span class="component-desc">
                                    <select id="edit_air_by_date" name="air_by_date" class="form-control form-control-inline input-sm">
                                        <option value="keep" ${'selected="selected"' if air_by_date_value is None else ''}>&lt; Keep &gt;</option>
                                        <option value="enable" ${'selected="selected"' if air_by_date_value == 1 else ''}>Yes</option>
                                        <option value="disable" ${'selected="selected"' if air_by_date_value == 0 else ''}>No</option>
                                    </select><br>
                                    Set if these shows are released as Show.03.02.2010 rather than Show.S02E03.<br>
                                    <span style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</span>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="edit_subtitles">
                                <span class="component-title">Subtitles</span>
                                <span class="component-desc">
                                    <select id="edit_subtitles" name="subtitles" class="form-control form-control-inline input-sm">
                                        <option value="keep" ${'selected="selected"' if subtitles_value is None else ''}>&lt; Keep &gt;</option>
                                        <option value="enable" ${'selected="selected"' if subtitles_value == 1 else ''}>Yes</option>
                                        <option value="disable" ${'selected="selected"' if subtitles_value == 0 else ''}>No</option>
                                    </select><br>
                                    Search for subtitles.
                                </span>
                            </label>
                        </div>
                        </fieldset>
                    </div>
                </div>
            </div>
            <input id="submit" type="submit" value="Save Changes" class="btn pull-left config_submitter button">
        </form>
    </div>
</div>
</%block>
