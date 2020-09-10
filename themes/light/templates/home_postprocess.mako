<%inherit file="/layouts/main.mako"/>
<%!
    import pkgutil
    from medusa import app
%>
<%block name="scripts">
<script type="text/x-template" id="manual-post-process-template">
<div>
    <div class="row">
        <div class="col-md-12">
            <h1 class="header">{{ $route.meta.header }}</h1>
        </div>
    </div>
    <div class="row">
        <div class="col-md-8 col-md-offset-2">
            <form name="processForm" class="lineH-40" method="post" action="home/postprocess/processEpisode">
            <table id="process" class="col-md-12">
                <input type="hidden" id="proc_type" name="type" value="manual">
                <tr>
                    <td>
                        <b>Enter the folder containing the episode:</b>
                    </td>
                    <td>
                        <input type="text" name="proc_dir" id="episodeDir" class="form-control form-control-inline input-sm"/>
                    </td>
                </tr>
                <tr>
                    <td>
                        <b>Process Method to be used:</b>
                    </td>
                    <td>
                        <select name="process_method" id="process_method" class="form-control form-control-inline input-sm" >
                        % if pkgutil.find_loader('reflink') is not None:
                            <% process_method_text = {'copy': "Copy", 'move': "Move", 'hardlink': "Hard Link", 'symlink' : "Symbolic Link", 'reflink': "Reference Link", 'keeplink' : "Keep Link" } %>
                            % for cur_action in ('copy', 'move', 'hardlink', 'symlink', 'reflink', 'keeplink'):
                                <option value="${cur_action}" ${'selected="selected"' if app.PROCESS_METHOD == cur_action else ''}>${process_method_text[cur_action]}</option>
                            % endfor
                        % else:
                            <% process_method_text = {'copy': "Copy", 'move': "Move", 'hardlink': "Hard Link", 'symlink' : "Symbolic Link", 'keeplink' : "Keep Link"} %>
                            % for cur_action in ('copy', 'move', 'hardlink', 'symlink', 'keeplink'):
                                <option value="${cur_action}" ${'selected="selected"' if app.PROCESS_METHOD == cur_action else ''}>${process_method_text[cur_action]}</option>
                            % endfor
                        % endif
                        </select>
                    </td>
                </tr>
                <tr>
                    <td>
                        <b>Force already Post-Processed Dir/Files:</b>
                    </td>
                    <td>
                        <input id="force" name="force" type="checkbox">
                        <span class="smallhelp"><i>&nbsp;(Check this to post-process files that were already post-processed)</i></span>
                    </td>
                </tr>
                <tr>
                    <td>
                        <b>Mark Dir/Files as priority download:</b>
                    </td>
                    <td>
                        <input id="is_priority" name="is_priority" type="checkbox">
                        <span class="smallhelp"><i>&nbsp;(Check this to replace the file even if it exists at higher quality)</i></span>
                    </td>
                </tr>
                <tr>
                    <td>
                        <b>Delete files and folders:</b>
                    </td>
                    <td>
                        <input id="delete_on" name="delete_on" type="checkbox" ${'' if app.NO_DELETE else 'checked="checked"'}>
                        <span class="smallhelp"><i>&nbsp;(Check this to delete files and folders like auto processing)</i></span>
                    </td>
                </tr>
                % if app.USE_FAILED_DOWNLOADS:
                <tr>
                    <td>
                        <b>Mark download as failed:</b>
                    </td>
                    <td>
                        <input id="failed" name="failed" type="checkbox">
                        <span class="smallhelp"><i>&nbsp;(Check this to mark download as failed)</i></span>
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
                        <span class="smallhelp"><i>&nbsp;(Check this to post-process when no subtitles available)</i></span>
                    </td>
                </tr>
                <tr>
                    <td>
                    </td>
                    <td>
                <span class="smallhelp"><i>* Create a new folder in PP folder and move only the files you want to ignore subtitles for</i></span>
                    </td>
                </tr>
                % endif
            </table>
                <input id="submit" class="btn-medusa" type="submit" value="Process" />
            </form>
        </div>
    </div>
</div>
</script>
<script>
window.app = {};
window.app = new Vue({
    el: '#vue-wrap',
    store,
    router,
    data() {
        return {
            // This loads manual-post-process.vue
            pageComponent: 'manual-post-process'
        }
    }
});
</script>
</%block>
