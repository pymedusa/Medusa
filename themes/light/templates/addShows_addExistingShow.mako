<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
%>
<%block name="scripts">
<script type="text/javascript" src="js/quality-chooser.js?${sbPID}"></script>
<script type="text/javascript" src="js/add-show-options.js?${sbPID}"></script>
<script>
let app;
const startVue = () => {
    app = new Vue({
        el: '#vue-wrap',
        data() {
            return {};
        }
    });
};
</script>
</%block>
<%block name="content">
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif
<div id="newShowPortal">
    <div id="config-components">
        <ul><li><app-link href="#core-component-group1">Add Existing Show</app-link></li></ul>
        <div id="core-component-group1" class="tab-pane active component-group">
            <form id="addShowForm" method="post" action="addShows/addExistingShows" accept-charset="utf-8">
                <div id="tabs">
                    <ul>
                        <li><app-link href="addShows/existingShows/#tabs-1">Manage Directories</app-link></li>
                        <li><app-link href="addShows/existingShows/#tabs-2">Customize Options</app-link></li>
                    </ul>
                    <div id="tabs-1" class="existingtabs">
                        <%include file="/inc_rootDirs.mako"/>
                    </div>
                    <div id="tabs-2" class="existingtabs">
                        <%include file="/inc_addShowOptions.mako"/>
                    </div>
                </div>
                <br>
                <p>Medusa can add existing shows, using the current options, by using locally stored NFO/XML metadata to eliminate user interaction.
                If you would rather have Medusa prompt you to customize each show, then use the checkbox below.</p>
                <p><input type="checkbox" name="promptForSettings" id="promptForSettings" /> <label for="promptForSettings">Prompt me to set settings for each show</label></p>
                <hr>
                <p><b>Displaying folders within these directories which aren't already added to Medusa:</b></p>
                <ul id="rootDirStaticList"><li></li></ul>
                <br>
                <div id="tableDiv"></div>
                <br>
                <br>
                <input class="btn" type="button" value="Submit" id="submitShowDirs" />
            </form>
        </div>
    </div>
</div>
</%block>
