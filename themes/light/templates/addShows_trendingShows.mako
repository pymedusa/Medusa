<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
%>
<%block name="scripts">
% if enable_anime_options:
    <script type="text/javascript" src="js/blackwhite.js?${sbPID}"></script>
% endif
<script>
const { mapState } = window.Vuex;

window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    data() {
        return {
            rootDirs: []
        };
    },
    // TODO: Replace with Object spread (`...mapState`)
    computed: Object.assign(mapState({
        config: state => state.config.general // Used by `inc_addShowOptions.mako`
    }))
});
</script>
</%block>
<%block name="content">
<div class="row">
    <div class="col-md-12">
        <h1 class="header">${header}</h1>
    </div>
</div>

<div id="recommended-shows-options" class="row">
    <div class="col-md-12">
    <div id="tabs">
        <fieldset class="component-group-list">
            <div class="field-pair">
                <label class="clearfix" for="content_configure_show_options">
                    <span class="component-title">Configure Show Options</span>
                    <span class="component-desc">
                        <input type="checkbox" class="enabler" name="configure_show_options" id="configure_show_options" />
                        <p>Recommended shows will be added using your default options. Use this if you want to change the options for that show.</p>
                    </span>
                </label>
            </div>
            <div id="content_configure_show_options">
                <div class="field-pair">
                    <label class="clearfix" for="configure_show_options">
                        <ul>
                            <li><app-link id="trakt-tab-1" href="addShows/${realpage + '/'}?traktList=${traktList}#tabs-1">Manage Directories</app-link></li>
                            <li><app-link id="trakt-tab-2" href="addShows/${realpage + '/'}?traktList=${traktList}#tabs-2">Customize Options</app-link></li>
                        </ul>
                        <div id="tabs-1" class="existingtabs">
                            <root-dirs @update="rootDirs = $event"></root-dirs>
                            <br/>
                        </div>
                        <div id="tabs-2" class="existingtabs">
                            <%include file="/inc_addShowOptions.mako"/>
                        </div>
                    </label>
                </div>
            </div>
        </fieldset>
    </div>  <!-- tabs-->

    <div class="show-option">
        <span>Sort By:</span>
        <select id="showsort" class="form-control form-control-inline input-sm">
            <option value="name">Name</option>
            <option value="original" selected="selected">Original</option>
            <option value="votes">Votes</option>
            <option value="rating">% Rating</option>
            <option value="rating_votes">% Rating > Votes</option>
        </select>
        <span style="margin-left:12px;">Sort Order:</span>
    </div>
    <div class="show-option">
        <select id="showsortdirection" class="form-control form-control-inline input-sm">
            <option value="asc" selected="selected">Asc</option>
            <option value="desc">Desc</option>
        </select>
    </div>
    <div class="show-option">
        <span style="margin-left:12px;">Select Trakt List:</span>
        <select id="traktlistselection" class="form-control form-control-inline input-sm">
            <option value="anticipated" ${' selected="selected"' if traktList == "anticipated" else ''}>Most Anticipated</option>
            <option value="newshow" ${'selected="selected"' if traktList == "newshow" else ''}>New Shows</option>
            <option value="newseason" ${'selected="selected"' if traktList == "newseason" else ''}>Season Premieres</option>
            <option value="trending" ${'selected="selected"' if traktList == "trending" else ''}>Trending</option>
            <option value="popular" ${'selected="selected"' if traktList == "popular" else ''}>Popular</option>
            <option value="watched" ${'selected="selected"' if traktList == "watched" else '' }>Most Watched</option>
            <option value="played" ${'selected="selected"' if traktList == "played" else '' }>Most Played</option>
            <option value="collected" ${'selected="selected"' if traktList == "collected" else ''}>Most Collected</option>
    % if app.TRAKT_ACCESS_TOKEN:
            <option value="recommended"  ${'selected="selected"' if traktList == "recommended" else ''}>Recommended</option>
    % endif
        </select>
    </div>
</div> <!-- col -->
</div> <!-- row -->

<div id="trendingShows"></div>

% if traktList:
    <input type="hidden" name="traktList" id="traktList" value="${traktList}" />
% endif
</%block>
