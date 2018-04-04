<div id="showSelector" class="hidden-print">
    <div class="form-inline">
            <div>
                <div class="select-show-group pull-left top-5 bottom-5">
                    <select id="select-show" class="form-control input-sm-custom show-selector">
                        % for cur_show_list in sortedShowLists:
                            <% cur_show_type = cur_show_list[0] %>
                            <% cur_show_list = cur_show_list[1] %>
                            % if len(sortedShowLists) > 1:
                                <optgroup label="${cur_show_type}">
                            % endif
                                % for cur_show in cur_show_list:
                                <option data-indexer-name="${cur_show.indexer_name}" data-series-id="${cur_show.series_id}" value="${cur_show.series_id}" ${'selected="selected"' if cur_show == show else ''}>${cur_show.name}</option>
                                % endfor
                            % if len(sortedShowLists) > 1:
                                </optgroup>
                            % endif
                        % endfor
                    </select>
                </div> <!-- end of select-show-group -->
            </div>
    </div>
</div> <!-- end of container -->
