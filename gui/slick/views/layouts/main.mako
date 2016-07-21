<%!
    from sickbeard import (
        ANIME_SPLIT_HOME,
        ANON_REDIRECT,
        COMING_EPS_LAYOUT,
        COMING_EPS_SORT,
        DATE_PRESET,
        FUZZY_DATING,
        HISTORY_LAYOUT,
        HOME_LAYOUT,
        POSTER_SORTBY,
        POSTER_SORTDIR,
        ROOT_DIRS,
        SORT_ARTICLE,
        THEME_NAME,
        TIME_PRESET,
        TRIM_ZERO,
        WEB_ROOT,
    )
%>
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex, nofollow">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
    <!-- These values come from css/dark.css and css/light.css -->
    % if THEME_NAME == "dark":
    <meta name="theme-color" content="#15528F">
    % elif THEME_NAME == "light":
    <meta name="theme-color" content="#333333">
    % endif
    <title>Medusa - ${title}</title>
    <base href="${WEB_ROOT}" />
    <!--[if lt IE 9]>
        <script src="https://oss.maxcdn.com/html5shiv/3.7.2/html5shiv.min.js"></script>
        <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>
    <![endif]-->
    <meta name="msapplication-TileColor" content="#FFFFFF">
    <meta name="msapplication-TileImage" content="/images/ico/favicon-144.png">
    <meta name="msapplication-config" content="/css/browserconfig.xml">
    <meta data-var="srRoot" data-content="">
    <meta data-var="themeSpinner" data-content="${'-dark' if THEME_NAME == 'dark' else ''}">
    <meta data-var="anonURL" data-content="${ANON_REDIRECT}">
    <meta data-var="ANIME_SPLIT_HOME" data-content="${ANIME_SPLIT_HOME}">
    <meta data-var="COMING_EPS_LAYOUT" data-content="${COMING_EPS_LAYOUT}">
    <meta data-var="COMING_EPS_SORT" data-content="${COMING_EPS_SORT}">
    <meta data-var="DATE_PRESET" data-content="${DATE_PRESET}">
    <meta data-var="FUZZY_DATING" data-content="${FUZZY_DATING}">
    <meta data-var="HISTORY_LAYOUT" data-content="${HISTORY_LAYOUT}">
    <meta data-var="HOME_LAYOUT" data-content="${HOME_LAYOUT}">
    <meta data-var="POSTER_SORTBY" data-content="${POSTER_SORTBY}">
    <meta data-var="POSTER_SORTDIR" data-content="${POSTER_SORTDIR}">
    <meta data-var="ROOT_DIRS" data-content="${ROOT_DIRS}">
    <meta data-var="SORT_ARTICLE" data-content="${SORT_ARTICLE}">
    <meta data-var="TIME_PRESET" data-content="${TIME_PRESET}">
    <meta data-var="TRIM_ZERO" data-content="${TRIM_ZERO}">
    <%block name="metas" />
    <link rel="shortcut icon" href="/images/ico/favicon.ico">
    <link rel="icon" sizes="16x16 32x32 64x64" href="/images/ico/favicon.ico">
    <link rel="icon" type="image/png" sizes="196x196" href="/images/ico/favicon-196.png">
    <link rel="icon" type="image/png" sizes="160x160" href="/images/ico/favicon-160.png">
    <link rel="icon" type="image/png" sizes="96x96" href="/images/ico/favicon-96.png">
    <link rel="icon" type="image/png" sizes="64x64" href="/images/ico/favicon-64.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/images/ico/favicon-32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/images/ico/favicon-16.png">
    <link rel="apple-touch-icon" sizes="152x152" href="/images/ico/favicon-152.png">
    <link rel="apple-touch-icon" sizes="144x144" href="/images/ico/favicon-144.png">
    <link rel="apple-touch-icon" sizes="120x120" href="/images/ico/favicon-120.png">
    <link rel="apple-touch-icon" sizes="114x114" href="/images/ico/favicon-114.png">
    <link rel="apple-touch-icon" sizes="76x76" href="/images/ico/favicon-76.png">
    <link rel="apple-touch-icon" sizes="72x72" href="/images/ico/favicon-72.png">
    <link rel="apple-touch-icon" href="/images/ico/favicon-57.png">
    <link rel="stylesheet" type="text/css" href="/css/vender.min.css?${sbPID}"/>
    <link rel="stylesheet" type="text/css" href="/css/browser.css?${sbPID}" />
    <link rel="stylesheet" type="text/css" href="/css/lib/jquery-ui-1.10.4.custom.min.css?${sbPID}" />
    <link rel="stylesheet" type="text/css" href="/css/lib/jquery.qtip-2.2.1.min.css?${sbPID}"/>
    <link rel="stylesheet" type="text/css" href="/css/style.css?${sbPID}"/>
    <link rel="stylesheet" type="text/css" href="/css/${THEME_NAME}.css?${sbPID}" />
    <link rel="stylesheet" type="text/css" href="/css/print.css?${sbPID}" />
    <link rel="stylesheet" type="text/css" href="/css/country-flags.css?${sbPID}"/>
    <%block name="css" />
</head>
<body data-controller="${controller}" data-action="${action}">
    <%include file="/partials/header.mako"/>
    % if submenu:
    <%include file="/partials/submenu.mako"/>
    % endif
    <%include file="/partials/alerts.mako"/>
    <div id="contentWrapper">
        <div id="content">
            <%block name="content" />
        </div><!-- /content -->
    </div><!-- /contentWrapper -->
    <%include file="/partials/footer.mako" />
<%block name="scripts" />

</body>

</html>
