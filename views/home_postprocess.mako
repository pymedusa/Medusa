<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
%>
<%block name="content">

<div class="row">
    <div class="col-md-12">
    % if not header is UNDEFINED:
        <h1 class="header">${header}</h1>
    % else:
        <h1 class="title">${title}</h1>
    % endif
    </div>
</div>
<div class="row">
    <div class="col-md-12">
        <form name="processForm" method="post" action="home/postprocess/processEpisode" style="line-height: 40px;">
        <table>
            <input type="hidden" id="proc_type" name="type" value="manual">
            <tr>
                <td style="padding-right:10px;">
                    <b>Enter the folder containing the episode:</b>
                </td>
                <td>
                    <input type="text" name="proc_dir" id="episodeDir" class="form-control form-control-inline input-sm input350" style="margin-right: 5px;"/>
                </td>
            </tr>
            <tr>
                <td>
                    <b>Process Method to be used:</b>
                </td>
                <td>
                    <select name="process_method" id="process_method" class="form-control form-control-inline input-sm" >
                    <% process_method_text = {'copy': "Copy", 'move': "Move", 'hardlink': "Hard Link", 'symlink' : "Symbolic Link"} %>
                    % for cur_action in ('copy', 'move', 'hardlink', 'symlink'):
                        <option value="${cur_action}" ${'selected="selected"' if app.PROCESS_METHOD == cur_action else ''}>${process_method_text[cur_action]}</option>
                    % endfor
                    </select>
                </td>
            </tr>
            <tr>
                <td>
                    <b>Force already Post Processed Dir/Files:</b>
                </td>
                <td>
                    <input id="force" name="force" type="checkbox">
                    <span style="line-height: 0; font-size: 12px;"><i>&nbsp;(Check this to post-process files that were already post-processed)</i></span>
                </td>
            </tr>
            <tr>
                <td>
                    <b>Mark Dir/Files as priority download:</b>
                </td>
                <td>
                    <input id="is_priority" name="is_priority" type="checkbox">
                    <span style="line-height: 0; font-size: 12px;"><i>&nbsp;(Check this to replace the file even if it exists at higher quality)</i></span>
                </td>
            </tr>
            <tr>
                <td>
                    <b>Delete files and folders:</b>
                </td>
                <td>
                    <input id="delete_on" name="delete_on" type="checkbox" ${'' if app.NO_DELETE else 'checked="checked"'}>
                    <span style="line-height: 0; font-size: 12px;"><i>&nbsp;(Check this to delete files and folders like auto processing)</i></span>
                </td>
            </tr>
            % if app.USE_FAILED_DOWNLOADS:
            <tr>
                <td>
                    <b>Mark download as failed:</b>
                </td>
                <td>
                    <input id="failed" name="failed" type="checkbox">
                    <span style="line-height: 0; font-size: 12px;"><i>&nbsp;(Check this to mark download as failed)</i></span>
                </td>
            </tr>
            % endif
            % if app.POSTPONE_IF_NO_SUBS:
            <tr>
                <td>
                    <b>Skip associated subtitles check*:</b>
                </td>
                <td>
                    <input id="ignore_subs" name="ignore_subs" type="checkbox">
                    <span style="line-height: 0; font-size: 12px;"><i>&nbsp;(Check this to post-process when no subtitles available)</i></span>
                </td>
            </tr>
            <tr>
                <td>
                </td>
                <td>
            <span style="line-height: 0; font-size: 12px;"><i>* Create a new folder in PP folder and move only the files you want to ignore subtitles for</i></span>
                </td>
            </tr>
            % endif
        </table>
            <input id="submit" class="btn" type="submit" value="Process" />
        </form>
    </div>
</div>
</%block>
