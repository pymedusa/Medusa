<!-- BEGIN SUBMENU -->
    <div id="sub-menu-container" class="row">
	    <div id="SubMenu" class="hidden-print col-md-12">
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
	                      <a href="${menuItem['path']}" class="btn${('', ' confirm ' + menuItem.get('class', ''))['confirm' in menuItem]} top-5 bottom-5">${('', '<span class="pull-left ' + icon_class + '"></span> ')[bool(icon_class)]}${menuItem['title']}</a>
	                      <% first = False %>
	                  % endif
	            % endif
	        % endfor
	    </div>
    </div> <!-- end of container -->
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
