% if not (controller == "schedule") and not (action == "previewRename"):
<!-- BEGIN SUBMENU -->
    <div id="sub-menu-container" class="row shadow">
        <div id="sub-menu" class="submenu-default hidden-print col-md-12">
            <% first = True %>
            % for menuItem in submenu:
                % if 'requires' not in menuItem or menuItem['requires']:
                    <% icon_class = '' if 'icon' not in menuItem else ' ' + menuItem['icon'] %>
                      % if type(menuItem['path']) == dict:
                          ${("</span><span>", "")[bool(first)]}<b>${menuItem['title']}</b>
                          <%
                              first = False
                              inner_first = True
                          %>
                          % for cur_link in menuItem['path']:
                              ${("&middot; ", "")[bool(inner_first)]}<app-link class="inner" href="${menuItem['path'][cur_link]}">${cur_link}</app-link>
                              <% inner_first = False %>
                          % endfor
                      % else:
                          <app-link href="${menuItem['path']}" class="btn-medusa${('', ' confirm ' + menuItem.get('class', ''))['confirm' in menuItem]} top-5 bottom-5">${('', '<span class="pull-left ' + icon_class + '"></span> ')[bool(icon_class)]}${menuItem['title']}</app-link>
                          <% first = False %>
                      % endif
                % endif
            % endfor
            <% curShowSlug = show.identifier.slug if show is not UNDEFINED else '' %>
            <show-selector v-if="'${action}' === 'displayShow'" show-slug="${curShowSlug}"></show-selector>
        </div>
    </div> <!-- end of container -->
<!-- END sub-menu -->

<!-- MOBILE sub-menu -->
    <div class="btn-group">

  <ul class="dropdown-menu">
    <li><app-link href="#">Action</app-link></li>
    <li><app-link href="#">Another action</app-link></li>
    <li><app-link href="#">Something else here</app-link></li>
    <li role="separator" class="divider"></li>
    <li><app-link href="#">Separated link</app-link></li>
  </ul>
</div>
% endif
