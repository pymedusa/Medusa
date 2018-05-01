<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa.indexers.indexer_api import indexerApi
%>
<%block name="scripts">
<script type="text/javascript" src="js/add-show-options.js?${sbPID}"></script>
<script type="text/javascript" src="js/blackwhite.js?${sbPID}"></script>
<script src="js/lib/Frisbee.min.js"></script>
<script src="js/lib/vue-frisbee.min.js"></script>
<script src="js/vue-submit-form.js"></script>
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'New Show'
        },
        data() {
            return {
                header: 'New Show'
            };
        },
        methods: {
            vueSubmitForm
        }
    });
};
</script>
</%block>
<%block name="content">
<h1 class="header">{{header}}</h1>
<div class="newShowPortal">
    <div id="config-components">
        <ul><li><app-link href="#core-component-group1">Add New Show</app-link></li></ul>
        <div id="core-component-group1" class="tab-pane active component-group">
            <div id="displayText"></div>
            <br>
            <form id="addShowForm" method="post" action="addShows/addNewShow" redirect="/" accept-charset="utf-8">
                <fieldset class="sectionwrap">
                    <legend class="legendStep">Find a show on selected indexer(s)</legend>
                    <div class="stepDiv">
                        <input type="hidden" id="indexer_timeout" value="${app.INDEXER_TIMEOUT}" />
                        % if use_provided_info:
                            Show retrieved from existing metadata: <app-link href="${indexerApi(provided_indexer).config['show_url']}${provided_indexer_id}">${provided_indexer_name}</app-link>
                            <input type="hidden" id="indexer_lang" name="indexer_lang" value="en" />
                            <input type="hidden" id="whichSeries" name="whichSeries" value="${provided_indexer_id}" />
                            <input type="hidden" id="providedIndexer" name="providedIndexer" value="${provided_indexer}" />
                            <input type="hidden" id="providedName" value="${provided_indexer_name}" />
                        % else:
                            <input type="text" id="nameToSearch" value="${default_show_name}" class="form-control form-control-inline input-sm input350"/>
                            &nbsp;&nbsp;
                            <select name="indexer_lang" id="indexerLangSelect" class="form-control form-control-inline input-sm bfh-languages" data-blank="false" data-language="${app.INDEXER_DEFAULT_LANGUAGE}" data-available="${','.join(indexerApi().config['valid_languages'])}">
                            </select><b>*</b>
                            &nbsp;
                            <select name="providedIndexer" id="providedIndexer" class="form-control form-control-inline input-sm">
                                <option value="0" ${'' if provided_indexer else 'selected="selected"'}>All Indexers</option>
                                % for indexer in indexers:
                                    <option value="${indexer}" ${'selected="selected"' if provided_indexer == indexer else ''}>
                                        ${indexers[indexer]}
                                    </option>
                                % endfor
                            </select>
                            &nbsp;
                            <input class="btn-medusa btn-inline" type="button" id="searchName" value="Search" />
                            <br><br>
                            <b>*</b> This will only affect the language of the retrieved metadata file contents and episode filenames.<br>
                            This <b>DOES NOT</b> allow Medusa to download non-english TV episodes!<br><br>
                            <div id="searchResults" style="height: 100%;"><br></div>
                        % endif
                    </div>
                </fieldset>
                <fieldset class="sectionwrap">
                    <legend class="legendStep">Pick the parent folder</legend>
                    <div class="stepDiv">
                        % if provided_show_dir:
                            Pre-chosen Destination Folder: <b>${provided_show_dir}</b> <br>
                            <input type="hidden" id="fullShowPath" name="fullShowPath" value="${provided_show_dir}" /><br>
                        % else:
                            <%include file="/inc_rootDirs.mako"/>
                        % endif
                    </div>
                </fieldset>
                <fieldset class="sectionwrap">
                    <legend class="legendStep">Customize options</legend>
                    <div class="stepDiv">
                        <%include file="/inc_addShowOptions.mako"/>
                    </div>
                </fieldset>
                % for curNextDir in other_shows:
                <input type="hidden" name="other_shows" value="${curNextDir}" />
                % endfor
                <input type="hidden" name="skipShow" id="skipShow" value="" />
            </form>
            <br>
            <div style="width: 100%; text-align: center;">
                <input @click.prevent="vueSubmitForm('addShowForm')" id="addShowButton" class="btn-medusa" type="button" value="Add Show" disabled="disabled" />
                % if provided_show_dir:
                <input class="btn-medusa" type="button" id="skipShowButton" value="Skip Show" />
                % endif
            </div>
        </div>
    </div>
</div>
</%block>
