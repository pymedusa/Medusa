<%inherit file="/layouts/main.mako"/>
<%!
    import sickbeard
    import calendar
    from sickbeard import sbdatetime
    from sickbeard import network_timezones
    from sickrage.helper.common import pretty_file_size
    import re
%>
<%block name="metas">
<meta data-var="max_download_count" data-content="${max_download_count}">
</%block>
<%block name="content">
    <table style="width: 100%;" class="home-header">
        <tr>
            <td nowrap>
                % if not header is UNDEFINED:
                    <h1 class="header" style="margin: 0;">${header}</h1>
                % else:
                    <h1 class="title" style="margin: 0;">${title}</h1>
                % endif
            </td>

            <td align="right">
                <div>
                    % if sickbeard.HOME_LAYOUT != 'poster':
                        <span class="show-option">
                            <button id="popover" type="button" class="btn btn-inline">Select Columns <b class="caret"></b></button>
                        </span>

                        <span class="show-option">
                            <button type="button" class="resetsorting btn btn-inline">Clear Filter(s)</button>
                        </span>
                    % endif

                    % if sickbeard.HOME_LAYOUT == 'poster':
                        <span class="show-option"> Poster Size:
                            <div style="width: 100px; display: inline-block; margin-left: 7px;" id="posterSizeSlider"></div>
                        </span>

                        <span class="show-option">
                            <input id="filterShowName" class="form-control form-control-inline input-sm input200" type="search" placeholder="Filter Show Name">
                        </span>

                        <span class="show-option"> Sort By:
                            <select id="postersort" class="form-control form-control-inline input-sm">
                                <option value="name" data-sort="/setPosterSortBy/?sort=name" ${('', 'selected="selected"')[sickbeard.POSTER_SORTBY == 'name']}>Name</option>
                                <option value="date" data-sort="/setPosterSortBy/?sort=date" ${('', 'selected="selected"')[sickbeard.POSTER_SORTBY == 'date']}>Next Episode</option>
                                <option value="network" data-sort="/setPosterSortBy/?sort=network" ${('', 'selected="selected"')[sickbeard.POSTER_SORTBY == 'network']}>Network</option>
                                <option value="progress" data-sort="/setPosterSortBy/?sort=progress" ${('', 'selected="selected"')[sickbeard.POSTER_SORTBY == 'progress']}>Progress</option>
                            </select>
                        </span>

                        <span class="show-option"> Direction:
                            <select id="postersortdirection" class="form-control form-control-inline input-sm">
                                <option value="true" data-sort="/setPosterSortDir/?direction=1" ${('', 'selected="selected"')[sickbeard.POSTER_SORTDIR == 1]}>Ascending </option>
                                <option value="false" data-sort="/setPosterSortDir/?direction=0" ${('', 'selected="selected"')[sickbeard.POSTER_SORTDIR == 0]}>Descending</option>
                            </select>
                        </span>
                    % endif

                    <span class="show-option"> Layout:
                        <select name="layout" class="form-control form-control-inline input-sm" onchange="location = this.options[this.selectedIndex].value;">
                            <option value="/setHomeLayout/?layout=poster" ${('', 'selected="selected"')[sickbeard.HOME_LAYOUT == 'poster']}>Poster</option>
                            <option value="/setHomeLayout/?layout=small" ${('', 'selected="selected"')[sickbeard.HOME_LAYOUT == 'small']}>Small Poster</option>
                            <option value="/setHomeLayout/?layout=banner" ${('', 'selected="selected"')[sickbeard.HOME_LAYOUT == 'banner']}>Banner</option>
                            <option value="/setHomeLayout/?layout=simple" ${('', 'selected="selected"')[sickbeard.HOME_LAYOUT == 'simple']}>Simple</option>
                        </select>
                    </span>
                </div>
            </td>
        </tr>
    </table>
    <%include file="/partials/home/${sickbeard.HOME_LAYOUT}.mako"/>
</%block>
