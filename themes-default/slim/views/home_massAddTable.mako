<%!
    from medusa import app
    from medusa.indexers.indexer_api import indexerApi
%>
<table id="addRootDirTable" class="defaultTable tablesorter">
    <thead>
        <tr>
            <th class="col-checkbox"><input type="checkbox" id="checkAll" checked="checked"></th>
            <th>Directory</th>
            <th width="20%">Show Name (tvshow.nfo)</th>
            <th width="20%">Indexer</th>
        </tr>
    </thead>
    <tbody>
% for curDir in dirList:
    <%
        if curDir['added_already']:
            continue
        show_dir = curDir['dir']
        series_id = show_dir
        indexer_id = 0
        if curDir['existing_info'][0]:
            series_id = show_dir + '|' + str(curDir['existing_info'][0]) + '|' + str(curDir['existing_info'][1])
            indexer_id = curDir['existing_info'][2]
    %>
    <tr>
        <td class="col-checkbox"><input type="checkbox" id="${series_id}" data-indexer="${indexer_id}" data-indexer-id="${series_id}"
            data-show-dir="${show_dir}" data-show-name="${curDir['existing_info'][1]}" class="showDirCheck" checked="checked"></td>
        <td><label for="${series_id}">${curDir['display_dir']}</label></td>
        % if curDir['existing_info'][1] and indexer_id > 0:
            <td><app-link href="${indexerApi(indexer_id).config['show_url']}${curDir['existing_info'][0]}">${curDir['existing_info'][1]}</app-link></td>
        % else:
            <td>?</td>
        % endif
        <td align="center">
            <select name="indexer">
                % for curIndexer in indexerApi().indexers.items():
                    <option value="${curIndexer[0]}" ${'selected="selected"' if curIndexer[0] == indexer_id or curIndexer[0] == app.INDEXER_DEFAULT else ''} >${curIndexer[1]}</option>
                % endfor
            </select>
        </td>
    </tr>
% endfor
    </tbody>
</table>
