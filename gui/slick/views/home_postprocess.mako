<%inherit file="/layouts/main.mako"/>
<%!
    import sickbeard
%>
<%block name="content">
<div id="content800">
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif

<div id="postProcess">
    <form name="processForm" method="post" action="processEpisode" style="line-height: 40px;">
    <table>
        <input type="hidden" id="type" name="type" value="manual">
        <tr>
            <td style="padding-right:10px;">
                <b>Enter the folder containing the episode:</b>
            </td>
            <td>
                <input type="text" name="proc_dir" id="episodeDir" class="form-control form-control-inline input-sm input350" autocapitalize="off" />
            </td>
        </tr>
        <tr>
            <td>
                <b>Process Method to be used:</b>
            </td>
            <td>
                <select name="process_method" id="process_method" class="form-control form-control-inline input-sm" >
                <% process_method_text = {'copy': "Copy", 'move': "Move", 'hardlink': "Hard Link", 'symlink' : "Symbolic Link"} %>
                % for curAction in ('copy', 'move', 'hardlink', 'symlink'):
                    <option value="${curAction}" ${'selected="selected"' if sickbeard.PROCESS_METHOD == curAction else ''}>${process_method_text[curAction]}</option>
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
                <input id="delete_on" name="delete_on" type="checkbox">
                <span style="line-height: 0; font-size: 12px;"><i>&nbsp;(Check this to delete files and folders like auto processing)</i></span>
            </td>
        </tr>
        % if sickbeard.USE_FAILED_DOWNLOADS:
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
        % if sickbeard.POSTPONE_IF_NO_SUBS:
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
</%block>
