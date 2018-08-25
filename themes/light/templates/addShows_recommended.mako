<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
% if enable_anime_options:
    <script type="text/javascript" src="js/blackwhite.js?${sbPID}"></script>
% endif
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    data() {
        return {
            rootDirs: []
        };
    }
});
</script>
</%block>
<%block name="content">
<div class="row">
    <div class="col-md-12">
        <h1 class="header">{{ $route.meta.header }}</h1>
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
                                <li><app-link href="addShows/${realpage + '/'}#tabs-1">Manage Directories</app-link></li>
                                <li><app-link href="addShows/${realpage + '/'}#tabs-2">Customize Options</app-link></li>
                            </ul>
                            <div id="tabs-1" class="existingtabs">
                                <root-dirs @update="rootDirs = $event"></root-dirs>
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

            % for cur_show in recommended_shows:

                <% cur_rating = 0 %>
                <% cur_votes = 0 %>

                % if cur_show.rating:
                    <% cur_rating = cur_show.rating %>
                % endif

                % if cur_show.votes:
                    <% cur_votes = cur_show.votes %>
                % endif

                <div class="show-row" data-name="${cur_show.title}" data-rating="${cur_rating}" data-votes="${cur_votes}" data-anime="${cur_show.is_anime}">
                    <div class="recommended-container default-poster ${('', 'show-in-list')[cur_show.show_in_list or cur_show.mapped_series_id in removed_from_medusa]}">
                        <div class="recommended-image">
                            <app-link href="${cur_show.image_href}">
                                <img alt="" class="recommended-image" src="images/poster.png" data-original="${cur_show.image_src}" height="273px" width="186px"/>
                            </app-link>
                        </div>
                        <div id="check-overlay"></div>

                        <div class="show-title">
                            ${cur_show.title}
                        </div>

                        <div class="clearfix show-attributes">
                            <p>${int(float(cur_rating)*10)}% <img src="images/heart.png">
                                % if cur_show.is_anime and cur_show.ids.get('aid'):
                                    <app-link class="anidb-url" href="https://anidb.net/a${cur_show.ids['aid']}">
                                        <img src="images/anidb_inline_refl.png" class="anidb-inline" alt=""/>
                                    </app-link>
                                % endif
                            </p>
                            <i>${cur_votes} votes</i>

                            <div class="recommendedShowTitleIcons">
                                % if cur_show.show_in_list:
                                    <button class="btn-medusa btn-xs"><app-link href="home/displayShow?indexername=${cur_show.mapped_indexer_name}&seriesid=${cur_show.mapped_series_id}">In List</app-link></button>
                                % else:
                                    <button class="btn-medusa btn-xs" data-isanime="1" data-indexer="${cur_show.mapped_indexer_name}"
                                    data-indexer-id="${cur_show.mapped_series_id}" data-show-name="${cur_show.title | u}"
                                    data-add-show>Add</button>
                                % endif
                                % if cur_show.mapped_series_id in removed_from_medusa:
                                    <button class="btn-medusa btn-xs"><app-link href="home/displayShow?indexername=${cur_show.mapped_indexer_name}&seriesid=${cur_show.mapped_series_id}">Watched</app-link></button>
                                % endif
                                % if trakt_b and not (cur_show.show_in_list or cur_show.mapped_series_id in removed_from_medusa):
                                    <button data-indexer-id="${cur_show.mapped_series_id}" class="btn-medusa btn-xs" data-blacklist-show>Blacklist</button>
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
