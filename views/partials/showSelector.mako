<div id="showSelector" class="hidden-print col-md-4 col-sm-12 col-xs-12 pull-md-left" style="margin-left:-21px">
    <div class="form-inline">
            <div>
                <div class="select-show-group pull-left top-5 bottom-5">
                    <select id="select-show" class="form-control input-sm-custom" style="height:25px;padding:1px">
                        % for cur_show_list in sortedShowLists:
                            <% cur_show_type = cur_show_list[0] %>
                            <% cur_show_list = cur_show_list[1] %>
                            % if len(sortedShowLists) > 1:
                                <optgroup label="${cur_show_type}">
                            % endif
                                % for cur_show in cur_show_list:
                                <option value="${cur_show.indexerid}" ${'selected="selected"' if cur_show == show else ''}>${cur_show.name}</option>
                                % endfor
                            % if len(sortedShowLists) > 1:
                                </optgroup>
                            % endif
                        % endfor
                    </select>
                </div> <!-- end of select-show-group -->
                <div class="container-navShow">
                    <div class="navShow"><img style="height:14px" id="prevShow" src="images/prev.png" alt="&lt;&lt;" title="Prev Show" /></div>
                    <div class="navShow"><img style="height:14px" id="nextShow" src="images/next.png" alt="&gt;&gt;" title="Next Show" /></div>
                </div>  <!-- end of container-navShow -->
            </div>
    </div>
</div> <!-- end of container -->
