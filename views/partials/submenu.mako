<!-- BEGIN SUBMENU -->
    <div id="SubMenu" class="hidden-print btn-group btn-group-justified pull-right full-width" role="group">
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
                          ${("&middot; ", "")[bool(inner_first)]}<a class="inner" href="${menuItem['path'][cur_link]}">${cur_link}</a>
                          <% inner_first = False %>
                      % endfor
                  % else:
                      <a href="${menuItem['path']}" class="btn-block btn${('', ' confirm ' + menuItem.get('class', ''))['confirm' in menuItem]} top-5 bottom-5">${('', '<span class="pull-left ' + icon_class + '"></span> ')[bool(icon_class)]}${menuItem['title']}</a>
                      <% first = False %>
                  % endif
            % endif
        % endfor
    </div>
<!-- END SUBMENU -->

<!-- MOBILE SUBMENU -->
    <div class="btn-group">
  
  <ul class="dropdown-menu">
    <li><a href="#">Action</a></li>
    <li><a href="#">Another action</a></li>
    <li><a href="#">Something else here</a></li>
    <li role="separator" class="divider"></li>
    <li><a href="#">Separated link</a></li>
  </ul>
</div>

    <div id="submenu-mobile" class="hidden-print btn-group mobile">
        <% first = True %>
        <button type="button" class="btn btn-default dropdown-toggle pull-right" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
            Submenu <span class="caret"></span>
        </button>
        <ul class="dropdown-menu dropdown-menu-custom pull-right" style="margin-top: 28px;">
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
                          ${("&middot; ", "")[bool(inner_first)]}<li><a href="${menuItem['path'][cur_link]}">${cur_link}</a></li>
                          <% inner_first = False %>
                      % endfor
                  % else:
                      <li><a href="${menuItem['path']}" class="${('', ' confirm ' + menuItem.get('class', ''))['confirm' in menuItem]}">${('', '<div class="img-align"><span class="' + icon_class + '"></span></div>')[bool(icon_class)]}${menuItem['title']}</a></li>
                      <% first = False %>
                  % endif
            % endif
        % endfor
        </ul>
    </div>
