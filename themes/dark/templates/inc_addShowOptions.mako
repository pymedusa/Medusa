<%
    from medusa import app
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import Quality, qualityPresets, qualityPresetStrings, statusStrings
    from medusa import subtitles
%>
        <div class="field-pair alt">
            <label for="customQuality" class="clearfix">
                <span class="component-title">Preferred Quality</span>
                <span class="component-desc">
                    <% allowed_qualities, preferred_qualities = Quality.split_quality(app.QUALITY_DEFAULT) %>
                    <%include file="/inc_qualityChooser.mako"/>
                </span>
            </label>
        </div>
        % if app.USE_SUBTITLES:
        <br><div class="field-pair">
            <label for="subtitles" class="clearfix">
                <span class="component-title">Subtitles</span>
                <span class="component-desc">
                     <input type="checkbox" name="subtitles" id="subtitles" ${'checked="checked"' if app.SUBTITLES_DEFAULT else ''} />
                    <p>Download subtitles for this show?</p>
                </span>
            </label>
        </div>
        % endif
        <div class="field-pair">
            <label for="statusSelect">
                <span class="component-title">Status for previously aired episodes</span>
                <span class="component-desc">
                    <select name="defaultStatus" id="statusSelect" class="form-control form-control-inline input-sm">
                    % for cur_status in [SKIPPED, WANTED, IGNORED]:
                        <option value="${cur_status}" ${'selected="selected"' if app.STATUS_DEFAULT == cur_status else ''}>${statusStrings[cur_status]}</option>
                    % endfor
                    </select>
                </span>
            </label>
        </div>
        <div class="field-pair">
            <label for="statusSelectAfter">
                <span class="component-title">Status for all future episodes</span>
                <span class="component-desc">
                    <select name="defaultStatusAfter" id="statusSelectAfter" class="form-control form-control-inline input-sm">
                    % for cur_status in [SKIPPED, WANTED, IGNORED]:
                        <option value="${cur_status}" ${'selected="selected"' if app.STATUS_DEFAULT_AFTER == cur_status else ''}>${statusStrings[cur_status]}</option>
                    % endfor
                    </select>
                </span>
            </label>
        </div>
        <div class="field-pair alt">
            <label for="flatten_folders" class="clearfix">
                <span class="component-title">Flatten Folders</span>
                <span class="component-desc">
                    <input class="cb" type="checkbox" name="flatten_folders" id="flatten_folders" ${'checked="checked"' if app.FLATTEN_FOLDERS_DEFAULT else ''}/>
                    <p>Disregard sub-folders?</p>
                </span>
            </label>
        </div>
% if enable_anime_options:
        <div class="field-pair alt">
            <label for="anime" class="clearfix">
                <span class="component-title">Anime</span>
                <span class="component-desc">
                    <input type="checkbox" name="anime" id="anime" ${'checked="checked"' if app.ANIME_DEFAULT else ''} />
                    <p>Is this show an Anime?<p>
                </span>
            </label>
        </div>
% endif
        <div class="field-pair alt">
            <label for="scene" class="clearfix">
                <span class="component-title">Scene Numbering</span>
                <span class="component-desc">
                    <input type="checkbox" name="scene" id="scene" ${'checked="checked"' if app.SCENE_DEFAULT else ''} />
                    <p>Is this show scene numbered?</p>
                </span>
            </label>
        </div>
        <br>
        <div class="field-pair alt">
            <label for="saveDefaultsButton" class="nocheck clearfix">
                <span class="component-title"><input class="btn btn-inline" type="button" id="saveDefaultsButton" value="Save Defaults" disabled="disabled" /></span>
                <span class="component-desc">
                    <p>Use current values as the defaults</p>
                </span>
            </label>
        </div><br>
% if enable_anime_options:
    <% import medusa.black_and_white_list %>
    <%include file="/inc_blackwhitelist.mako"/>
% else:
        <input type="hidden" name="anime" id="anime" value="0" />
% endif
