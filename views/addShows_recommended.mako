<%inherit file="/layouts/main.mako"/>
<%!
    from medusa.helpers import anon_url
    from medusa import app
%>
<%block name="scripts">
    <script type="text/javascript" src="js/quality-chooser.js?${sbPID}"></script>
% if enable_anime_options:
    <script type="text/javascript" src="js/blackwhite.js?${sbPID}"></script>
% endif
</%block>
<%block name="content">
<div class="row">
    <div class="col-md-12">
    % if not header is UNDEFINED:
        <h1 class="header">${header}</h1>
    % else:
        <h1 class="title">${title}</h1>
    % endif
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
                            <p>Recommended shows will be added using your default options. Use this option if you want to change the options for that show.</p>
                        </span>
                    </label>
                </div>
                <div id="content_configure_show_options">
                    <div class="field-pair">
                        <label class="clearfix" for="configure_show_options">
                            <ul>
                                <li><a href="${base_url + 'addShows/' + realpage + '/'}#tabs-1">Manage Directories</a></li>
                                <li><a href="${base_url + 'addShows/' + realpage + '/'}#tabs-2">Customize Options</a></li>
                            </ul>
                            <div id="tabs-1" class="existingtabs">
                                <%include file="/inc_rootDirs.mako"/>
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
                <option value="original">Original</option>
                <option value="votes">Votes</option>
                <option value="rating">% Rating</option>
                <option value="rating_votes" selected="true" >% Rating > Votes</option>
            </select>
        </div>

        <div class="show-option">
            <span style="margin-left:12px">Sort Order:</span>
            <select id="showsortdirection" class="form-control form-control-inline input-sm">
                <option value="asc">Asc</option>
                <option value="desc" selected="true" >Desc</option>
            </select>
        </div>
    </div>
</div> <!-- row -->

<div id="recommended-shows-filters" class="row">
    <div id="popularShows" class="col-md-12">
        <div id="container">
        % if not recommended_shows:
            <div class="recommended_show" style="width:100%; margin-top:20px">
                <p class="red-text">Fetching of Recommender Data failed.
                <strong>Exception:</strong>
                <p>${exception}</p>
            </div>
        % else:

            % if not context.get('trakt_blacklist'):
                <% trakt_b = False %>
            % else:
                <% trakt_b = context.get('trakt_blacklist') %>
            % endif

            % if not context.get('removed_from_medusa'):
                <% removed_from_medusa = [] %>
            % else:
                <% removed_from_medusa = context.get('removed_from_medusa') %>
            % endif

            % for cur_result in recommended_shows:

                <% cur_rating = 0 %>
                <% cur_votes = 0 %>

                % if cur_result.rating:
                    <% cur_rating = cur_result.rating %>
                % endif

                % if cur_result.votes:
                    <% cur_votes = cur_result.votes %>
                % endif

                <div class="show-row" data-name="${cur_result.title}" data-rating="${cur_rating}" data-votes="${cur_votes}" data-anime="${cur_result.is_anime}">
                    <div class="recommended-container default-poster ${('', 'show-in-list')[cur_result.show_in_list or cur_result.indexer_id in removed_from_medusa]}">
                        <div class="recommended-image">
                            <a href="${anon_url(cur_result.image_href)}" target="_blank">
                                <img alt="" class="recommended-image" src="${cur_result.image_src}" height="273px" width="186px"/>
                            </a>
                        </div>
                        <div id="check-overlay"></div>

                        <div class="show-title">
                            ${cur_result.title}
                        </div>

                        <div class="clearfix show-attributes">
                            <p>${int(float(cur_rating)*10)}% <img src="images/heart.png">
                                % if cur_result.is_anime and cur_result.ids.get('aid'):
                                    <a class="anidb-url" href='${anon_url("https://anidb.net/a{0}".format(cur_result.ids["aid"]))}'>
                                        <img src="images/anidb_inline_refl.png" class="anidb-inline" alt=""/>
                                    </a>
                                % endif
                            </p>
                            <i>${cur_votes} votes</i>

                            <div class="recommendedShowTitleIcons">
                                % if cur_result.show_in_list:
                                    <button href="home/displayShow?show=${cur_result.indexer_id}" class="btn btn-xs">In List</button>
                                % else:
                                    <button class="btn btn-xs" data-isanime="1" data-indexer="TVDB"
                                    data-indexer-id="${cur_result.indexer_id}" data-show-name="${cur_result.title | u}"
                                    data-add-show>Add</button>
                                % endif
                                % if cur_result.indexer_id in removed_from_medusa:
                                    <button href="home/displayShow?show=${cur_result.indexer_id}" class="btn btn-xs">Watched</button>
                                % endif
                                % if trakt_b and not (cur_result.show_in_list or cur_result.indexer_id in removed_from_medusa):
                                    <button data-indexer-id="${cur_result.indexer_id}" class="btn btn-xs" data-blacklist-show>Blacklist</button>
                                % endif
                            </div>
                        </div>
                    </div>
                </div>
            % endfor
        % endif
        </div>
    </div>
</div>
</%block>
