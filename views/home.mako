<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    import calendar
    from medusa import sbdatetime
    from medusa import network_timezones
    from medusa.helper.common import pretty_file_size
    from random import choice
    import re

    if app.ROOT_DIRS:
        backend_pieces = app.ROOT_DIRS.split('|')
        backend_default = 'rd-' + backend_pieces[0]
        backend_dirs = backend_pieces[1:]
    else:
        backend_default = ''
        backend_dirs = []
%>
<%block name="metas">
<meta data-var="max_download_count" data-content="${max_download_count}">
</%block>
<%block name="content">
<input type="hidden" id="showID" value="${choice(app.showList).indexerid if app.showList else ''}" />
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
                            <option value="false" data-sort="setPosterSortDir/?direction=0"
                                ${'selected="selected" ' if app.POSTER_SORTDIR==0 else ''}>Descending</option>
                    </select>
                </div>
                <div class="show-option pull-right"> Sort By:
                  <select id="postersort" class="form-control form-control-inline input-sm">
                        <option value="name" data-sort="setPosterSortBy/?sort=name" ${'selected="selected" ' if app.POSTER_SORTBY=='name' else ''}>Name</option>
                        <option value="date" data-sort="setPosterSortBy/?sort=date"    ${'selected="selected" ' if app.POSTER_SORTBY=='date' else ''}>Next Episode</option>
                        <option value="network" data-sort="setPosterSortBy/?sort=network" ${'selected="selected" ' if app.POSTER_SORTBY=='network' else ''}>Network</option>
                        <option value="progress" data-sort="setPosterSortBy/?sort=progress" ${'selected="selected"' if app.POSTER_SORTBY=='progress' else ''}>Progress</option>
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
        % if not header is UNDEFINED:
        <h1 class="header pull-left" style="margin: 0;">${header}</h1>
        % else:
        <h1 class="title pull-left" style="margin: 0;">${title}</h1>
        % endif
    </div>
</div>

<br>

<div class="row">
    <div class="col-md-12">
        <div class="pull-left">
            <select name="showRootDir" id="showRootDir"
                class="form-control form-control-inline input-sm">
                <option value="-1" ${'selected="selected"' if app.SHOWS_ROOT =='-1' else ''}>All Folders</option>
                % for index, cur_dir in enumerate(backend_dirs):
                    <option value="${index}" ${'selected="selected"' if app.SHOWS_ROOT == index else ''}>${cur_dir}</option>
                % endfor
            </select>
        </div>
        <div class="show-option pull-right">
            % if app.HOME_LAYOUT != 'poster':
                <span class="show-option">
                    <button id="popover" type="button" class="btn btn-inline">
                        Select Columns <b class="caret"></b>
                    </button>
                </span> <span class="show-option">
                    <button type="button" class="resetsorting btn btn-inline">Clear
                        Filter(s)</button>
                </span>&nbsp;
            % endif
            Layout: <select name="layout"
                class="form-control form-control-inline input-sm show-layout">
                <option value="poster" ${'selected="selected"' if app.HOME_LAYOUT=='poster' else ''}>Poster</option>
                <option value="small" ${'selected="selected"' if app.HOME_LAYOUT=='small' else ''}>Small Poster</option>
                <option value="banner" ${'selected="selected"' if app.HOME_LAYOUT=='banner' else ''}>Banner</option>
                <option value="simple" ${'selected="selected"' if app.HOME_LAYOUT=='simple' else ''}>Simple</option>
            </select>
        </div>
    </div>
</div><!-- end row -->

<div class="row">
    <div class="col-md-12">
       <%include file="/partials/home/${app.HOME_LAYOUT}.mako"/>
    </div>
</div>
</%block>
