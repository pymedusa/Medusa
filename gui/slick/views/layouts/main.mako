<%!
    import datetime
    import re
    import sickbeard
    from sickrage.helper.common import pretty_file_size
    from sickrage.show.Show import Show
    from time import time

    # resource module is unix only
    has_resource_module = True
    try:
        import resource
    except ImportError:
        has_resource_module = False
%>
<%
    srRoot = sickbeard.WEB_ROOT
%>
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <meta name="robots" content="noindex, nofollow">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">

        <!-- These values come from css/dark.css and css/light.css -->
        % if sickbeard.THEME_NAME == "dark":
        <meta name="theme-color" content="#15528F">
        % elif sickbeard.THEME_NAME == "light":
        <meta name="theme-color" content="#333333">
        % endif

        <title>Medusa - ${title}</title>

        <!--[if lt IE 9]>
            <script src="https://oss.maxcdn.com/html5shiv/3.7.2/html5shiv.min.js"></script>
            <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>
        <![endif]-->
        <meta name="msapplication-TileColor" content="#FFFFFF">
        <meta name="msapplication-TileImage" content="${srRoot}/images/ico/favicon-144.png">
        <meta name="msapplication-config" content="${srRoot}/css/browserconfig.xml">

        <meta data-var="srRoot" data-content="${srRoot}">
        <meta data-var="themeSpinner" data-content="${('', '-dark')[sickbeard.THEME_NAME == 'dark']}">
        <meta data-var="anonURL" data-content="${sickbeard.ANON_REDIRECT}">

        <meta data-var="sickbeard.ANIME_SPLIT_HOME" data-content="${sickbeard.ANIME_SPLIT_HOME}">
        <meta data-var="sickbeard.COMING_EPS_LAYOUT" data-content="${sickbeard.COMING_EPS_LAYOUT}">
        <meta data-var="sickbeard.COMING_EPS_SORT" data-content="${sickbeard.COMING_EPS_SORT}">
        <meta data-var="sickbeard.DATE_PRESET" data-content="${sickbeard.DATE_PRESET}">
        <meta data-var="sickbeard.FUZZY_DATING" data-content="${sickbeard.FUZZY_DATING}">
        <meta data-var="sickbeard.HISTORY_LAYOUT" data-content="${sickbeard.HISTORY_LAYOUT}">
        <meta data-var="sickbeard.HOME_LAYOUT" data-content="${sickbeard.HOME_LAYOUT}">
        <meta data-var="sickbeard.POSTER_SORTBY" data-content="${sickbeard.POSTER_SORTBY}">
        <meta data-var="sickbeard.POSTER_SORTDIR" data-content="${sickbeard.POSTER_SORTDIR}">
        <meta data-var="sickbeard.ROOT_DIRS" data-content="${sickbeard.ROOT_DIRS}">
        <meta data-var="sickbeard.SORT_ARTICLE" data-content="${sickbeard.SORT_ARTICLE}">
        <meta data-var="sickbeard.TIME_PRESET" data-content="${sickbeard.TIME_PRESET}">
        <meta data-var="sickbeard.TRIM_ZERO" data-content="${sickbeard.TRIM_ZERO}">
        <meta data-var="sickbeard.FANART_BACKGROUND" data-content="${sickbeard.FANART_BACKGROUND}">
        <meta data-var="sickbeard.FANART_BACKGROUND_OPACITY" data-content="${sickbeard.FANART_BACKGROUND_OPACITY}">
        <%block name="metas" />

        <link rel="shortcut icon" href="${srRoot}/images/ico/favicon.ico">
        <link rel="icon" sizes="16x16 32x32 64x64" href="${srRoot}/images/ico/favicon.ico">
        <link rel="icon" type="image/png" sizes="196x196" href="${srRoot}/images/ico/favicon-196.png">
        <link rel="icon" type="image/png" sizes="160x160" href="${srRoot}/images/ico/favicon-160.png">
        <link rel="icon" type="image/png" sizes="96x96" href="${srRoot}/images/ico/favicon-96.png">
        <link rel="icon" type="image/png" sizes="64x64" href="${srRoot}/images/ico/favicon-64.png">
        <link rel="icon" type="image/png" sizes="32x32" href="${srRoot}/images/ico/favicon-32.png">
        <link rel="icon" type="image/png" sizes="16x16" href="${srRoot}/images/ico/favicon-16.png">
        <link rel="apple-touch-icon" sizes="152x152" href="${srRoot}/images/ico/favicon-152.png">
        <link rel="apple-touch-icon" sizes="144x144" href="${srRoot}/images/ico/favicon-144.png">
        <link rel="apple-touch-icon" sizes="120x120" href="${srRoot}/images/ico/favicon-120.png">
        <link rel="apple-touch-icon" sizes="114x114" href="${srRoot}/images/ico/favicon-114.png">
        <link rel="apple-touch-icon" sizes="76x76" href="${srRoot}/images/ico/favicon-76.png">
        <link rel="apple-touch-icon" sizes="72x72" href="${srRoot}/images/ico/favicon-72.png">
        <link rel="apple-touch-icon" href="${srRoot}/images/ico/favicon-57.png">

        <link rel="stylesheet" type="text/css" href="${srRoot}/css/vender.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="${srRoot}/css/browser.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="${srRoot}/css/lib/jquery-ui-1.10.4.custom.min.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="${srRoot}/css/lib/jquery.qtip-2.2.1.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="${srRoot}/css/style.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="${srRoot}/css/${sickbeard.THEME_NAME}.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="${srRoot}/css/print.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="${srRoot}/css/country-flags.css?${sbPID}"/>
        <%block name="css" />
    </head>
    <body data-controller="${controller}" data-action="${action}">
        <%include file="/partials/header.mako"/>
        % if submenu:
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
                              ${("&middot; ", "")[bool(inner_first)]}<a class="inner" href="${srRoot}/${menuItem['path'][cur_link]}">${cur_link}</a>
                              <% inner_first = False %>
                          % endfor
                      % else:
                          <a href="${srRoot}/${menuItem['path']}" class="btn${('', ' confirm ' + menuItem.get('class', ''))['confirm' in menuItem]}">${('', '<span class="pull-left ' + icon_class + '"></span> ')[bool(icon_class)]}${menuItem['title']}</a>
                          <% first = False %>
                      % endif
                % endif
            % endfor
            </span>
        </div>
        % endif
        % if sickbeard.BRANCH and sickbeard.BRANCH != 'master' and not sickbeard.DEVELOPER and loggedIn:
        <div class="alert alert-danger upgrade-notification hidden-print" role="alert">
            <span>You're using the ${sickbeard.BRANCH} branch. Please use 'master' unless specifically asked</span>
        </div>
        % endif

        % if sickbeard.NEWEST_VERSION_STRING and loggedIn:
        <div class="alert alert-success upgrade-notification hidden-print" role="alert">
            <span>${sickbeard.NEWEST_VERSION_STRING}</span>
        </div>
        % endif

        <div id="contentWrapper">
            <div id="content">
                <%block name="content" />
            </div> <!-- /content -->
        </div> <!-- /contentWrapper -->
        <%include file="/partials/footer.mako" />
        <%block name="scripts" />
    </body>
</html>
