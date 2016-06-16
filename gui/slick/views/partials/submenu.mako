<!-- BEGIN SUBMENU -->
<div id="SubMenu" class="hidden-print">
    <span>
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
                      ${("&middot; ", "")[bool(inner_first)]}<a class="inner" href="/${menuItem['path'][cur_link]}">${cur_link}</a>
                      <% inner_first = False %>
                  % endfor
              % else:
                  <a href="/${menuItem['path']}" class="btn${('', ' confirm ' + menuItem.get('class', ''))['confirm' in menuItem]}">${('', '<span class="pull-left ' + icon_class + '"></span> ')[bool(icon_class)]}${menuItem['title']}</a>
                  <% first = False %>
              % endif
        % endif
    % endfor
    </span>
</div>
<!-- END SUBMENU -->
