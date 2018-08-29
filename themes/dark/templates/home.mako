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
<%block name="metas">
<meta data-var="max_download_count" data-content="${max_download_count}">
</%block>
<%block name="scripts">
<script type="text/x-template" id="home-template">
<%
    # pick a random series to show as background
    random_show = choice(app.showList) if app.showList else None
%>
<div>
    <input type="hidden" id="background-series-slug" value="${getattr(random_show, 'slug', '')}" />

    <div class="row" v-if="layout === 'poster'">
        <div class="col-lg-9 col-md-12 col-sm-12 col-xs-12 pull-right">
            <div class="pull-right">
                <div class="show-option pull-right">
                    <input id="filterShowName" class="form-control form-control-inline input-sm input200" type="search" placeholder="Filter Show Name">
                </div>
                <div class="show-option pull-right"> Direction:
                    <select :value.number="config.posterSortdir" id="postersortdirection" class="form-control form-control-inline input-sm">
                        <option :value="1" data-sort="setPosterSortDir/?direction=1">Ascending</option>
                        <option :value="0" data-sort="setPosterSortDir/?direction=0">Descending</option>
                    </select>
                </div>
                <div class="show-option pull-right"> Sort By:
                <select :value="config.posterSortby" id="postersort" class="form-control form-control-inline input-sm">
                    <option value="name" data-sort="setPosterSortBy/?sort=name">Name</option>
                    <option value="date" data-sort="setPosterSortBy/?sort=date">Next Episode</option>
                    <option value="network" data-sort="setPosterSortBy/?sort=network">Network</option>
                    <option value="progress" data-sort="setPosterSortBy/?sort=progress">Progress</option>
                    <option value="indexer" data-sort="setPosterSortBy/?sort=indexer">Indexer</option>
                </select>
                </div>
                <div class="show-option pull-right">
                    Poster Size:
                    <div style="width: 100px; display: inline-block; margin-left: 7px;" id="posterSizeSlider"></div>
                </div>
            </div>
        </div>
    </div> <!-- row !-->

    <div class="row">
        <div class="col-md-12">
            <h1 class="header pull-left" style="margin: 0;">{{ $route.meta.header }}</h1>
        </div>
    </div>

    <br>

    <div class="row">
        <div class="col-md-12">
            <div class="pull-left" id="showRoot" style="display: none;">
                <select name="showRootDir" id="showRootDir" class="form-control form-control-inline input-sm"></select>
            </div>
            <div class="show-option pull-right">
                <template v-if="layout !== 'poster'">
                    <span class="show-option">
                        <button id="popover" type="button" class="btn-medusa btn-inline">
                            Select Columns <b class="caret"></b>
                        </button>
                    </span> <span class="show-option">
                        <button type="button" class="resetsorting btn-medusa btn-inline">Clear
                            Filter(s)</button>
                    </span>&nbsp;
                </template>
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
            <!-- Split in tabs -->
            <div id="showTabs" v-if="config.animeSplitHome && config.animeSplitHomeInTabs">
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
            <template v-else>
                <%include file="/partials/home/${app.HOME_LAYOUT}.mako"/>
            </template>
        </div>
    </div>
</div>
</script>
<script>
window.app = new Vue({
    el: '#vue-wrap',
    store,
    router,
    data() {
        return {
            // This loads home.vue
            pageComponent: 'home'
        }
    }
});
</script>
</%block>
