<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    import calendar
    from medusa import sbdatetime
    from medusa import network_timezones
    from medusa.helper.common import pretty_file_size
    from random import choice
    import re
%>
<%block name="scripts">
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        store,
        metaInfo: {
            title: 'Home'
        },
        data() {
            return {
                header: 'Show List'
            };
        },
        computed: Object.assign({
            layout: {
                get() {
                    const { config } = this;
                    return config.layout.home;
                },
                set(layout) {
                    const { $store } = this;
                    const page = 'home';
                    $store.dispatch('setLayout', { page, layout });
                }
            }
        }),
        mounted() {
        }
    });
};
</script>
</%block>
<%block name="metas">
<meta data-var="max_download_count" data-content="${max_download_count}">
</%block>
<%block name="content">
<%
    # pick a random series to show as background
    random_show = choice(app.showList) if app.showList else None
%>
<input type="hidden" id="background-series-slug" value="${getattr(random_show, 'slug', '')}" />

<div class="row">
    <div class="col-lg-9 col-md-${'12' if(app.HOME_LAYOUT == 'poster') else '9'} col-sm-${'12' if(app.HOME_LAYOUT == 'poster') else '8'} col-xs-12 pull-right">
        <div class="pull-right">
            % if app.HOME_LAYOUT == 'poster':
                <div class="show-option pull-right">
                    <input id="filterShowName" class="form-control form-control-inline input-sm input200" type="search" placeholder="Filter Show Name">
                </div>
                <div class="show-option pull-right"> Direction:
                    <select id="postersortdirection" class="form-control form-control-inline input-sm">
                            <option value="true" data-sort="setPosterSortDir/?direction=1" ${'selected="selected" ' if app.POSTER_SORTDIR==1 else ''}>Ascending</option>
                            <option value="false" data-sort="setPosterSortDir/?direction=0" ${'selected="selected" ' if app.POSTER_SORTDIR==0 else ''}>Descending</option>
                    </select>
                </div>
                <div class="show-option pull-right"> Sort By:
                  <select id="postersort" class="form-control form-control-inline input-sm">
                        <option value="name" data-sort="setPosterSortBy/?sort=name" ${'selected="selected" ' if app.POSTER_SORTBY=='name' else ''}>Name</option>
                        <option value="date" data-sort="setPosterSortBy/?sort=date"    ${'selected="selected" ' if app.POSTER_SORTBY=='date' else ''}>Next Episode</option>
                        <option value="network" data-sort="setPosterSortBy/?sort=network" ${'selected="selected" ' if app.POSTER_SORTBY=='network' else ''}>Network</option>
                        <option value="progress" data-sort="setPosterSortBy/?sort=progress" ${'selected="selected"' if app.POSTER_SORTBY=='progress' else ''}>Progress</option>
                        <option value="indexer" data-sort="setPosterSortBy/?sort=indexer" ${'selected="selected" ' if app.POSTER_SORTBY=='indexer' else ''}>Indexer</option>
                  </select>
                </div>
                <div class="show-option pull-right">
                    Poster Size:
                    <div style="width: 100px; display: inline-block; margin-left: 7px;" id="posterSizeSlider"></div>
                </div>
            % endif
        </div>
    </div>
</div> <!-- row !-->

<div class="row">
    <div class="col-md-12">
        <h1 class="header pull-left" style="margin: 0;">{{header}}</h1>
    </div>
</div>

<br>

<div class="row">
    <div class="col-md-12">
        <div class="pull-left" id="showRoot" style="display: none;">
            <select name="showRootDir" id="showRootDir"
                class="form-control form-control-inline input-sm">
            </select>
        </div>
        <div class="show-option pull-right">
            % if app.HOME_LAYOUT != 'poster':
                <span class="show-option">
                    <button id="popover" type="button" class="btn-medusa btn-inline">
                        Select Columns <b class="caret"></b>
                    </button>
                </span> <span class="show-option">
                    <button type="button" class="resetsorting btn-medusa btn-inline">Clear
                        Filter(s)</button>
                </span>&nbsp;
            % endif
            Layout: <select v-model="layout" name="layout" class="form-control form-control-inline input-sm show-layout">
                <option value="poster">Poster</option>
                <option value="small">Small Poster</option>
                <option value="banner">Banner</option>
                <option value="simple">Simple</option>
            </select>
        </div>
    </div>
</div><!-- end row -->

<div class="row">
    <div class="col-md-12">
        % if app.ANIME_SPLIT_HOME and app.ANIME_SPLIT_HOME_IN_TABS:
        <!-- Split in tabs -->
        <div id="showTabs">
            <!-- Nav tabs -->
            <ul>
                % for cur_show_list in show_lists:
                    <li><app-link href="home/#${cur_show_list[0].lower()}TabContent" id="${cur_show_list[0].lower()}Tab">${cur_show_list[0]}</app-link></li>
                % endfor
            </ul>
            <!-- Tab panes -->
            <div id="showTabPanes">
                <%include file="/partials/home/${app.HOME_LAYOUT}.mako"/>
            </div><!-- #showTabPanes -->
        </div> <!-- #showTabs -->
        % else:
        <%include file="/partials/home/${app.HOME_LAYOUT}.mako"/>
        % endif
    </div>
</div>
</%block>
