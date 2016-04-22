<%!
    import medusa as app
    from medusa.helpers import anon_url
%>
<div id="container">
<table id="addRootDirTable" class="defaultTable tablesorter">
    <thead>
        <tr>
            <th class="col-checkbox"><input type="checkbox" id="checkAll" checked=checked></th>
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
        show_id = curDir['dir']
        if curDir['existing_info']['indexer_id']:
            show_id = show_id + '|' + str(curDir['existing_info']['indexer_id']) + '|' + str(curDir['existing_info']['show_name'])
            indexer = curDir['existing_info']['indexer']
        indexer = 0
        if curDir['existing_info']['indexer_id']:
            indexer = curDir['existing_info']['indexer']
        elif app.INDEXER_DEFAULT > 0:
            indexer = app.INDEXER_DEFAULT
    %>
    <tr>
        <td class="col-checkbox"><input type="checkbox" id="${show_id}" class="dirCheck" checked=checked
        data-existing-indexer-id="${curDir['existing_info']['indexer_id']}" data-show-name="${curDir['existing_info']['show_name']}" 
        data-existing-indexer="${curDir['existing_info']['indexer']}" data-show-dir="${curDir['dir']}" data-allready-added="${curDir['added_already']}"></td>
        <td><label for="${show_id}">${curDir['display_dir']}</label></td>
        % if curDir['existing_info']['show_name'] and indexer > 0:
            <td><a href="${anon_url(app.indexerApi(indexer).config['show_url'], curDir['existing_info']['indexer_id'])}">${curDir['existing_info']['show_name']}</a></td>
        % else:
            <td>?</td>
        % endif
        <td align="center">
            <select name="indexer">
                % for curIndexer in app.indexerApi().indexers.iteritems():
                    <option value="${curIndexer[0]}" ${('', 'selected="selected"')[curIndexer[0] == indexer]}>${curIndexer[1]}</option>
                % endfor
            </select>
        </td>
    </tr>
% endfor
    </tbody>
</table>
</div>