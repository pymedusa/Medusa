Manual search for:<br>
    <app-link href="home/displayShow?indexername=${show.indexer_name}&showid=${show.show_id}" class="snatchTitle">${show.name}</app-link> / Season ${season}
        % if manual_search_type != 'season':
            Episode ${episode}
        % endif
    </app-link>
