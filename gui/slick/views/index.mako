<%!
    import sickbeard
%>
<%
    srRoot = sickbeard.WEB_ROOT
%>
<!DOCTYPE html>
<html lang="en" ng-app="sickrage">
    <head>
        <meta charset="utf-8">
        <meta name="robots" content="noindex, nofollow">
        <meta name="referrer" content="no-referrer" />
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">

        <!-- These values come from css/dark.css and css/light.css -->
        % if sickbeard.THEME_NAME == "dark":
        <meta name="theme-color" content="#15528F">
        % elif sickbeard.THEME_NAME == "light":
        <meta name="theme-color" content="#333333">
        % endif

        <title>Medusa - ${title}</title>

        <base href="${("/", srRoot)[srRoot is not ""]}" target="_blank">

        <!--[if lt IE 9]>
            <script src="https://oss.maxcdn.com/html5shiv/3.7.2/html5shiv.min.js"></script>
            <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>
        <![endif]-->
        <meta name="msapplication-TileColor" content="#FFFFFF">
        <meta name="msapplication-TileImage" content="images/ico/favicon-144.png">
        <meta name="msapplication-config" content="css/browserconfig.xml">

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

        <link rel="shortcut icon" href="images/ico/favicon.ico">
        <link rel="icon" sizes="16x16 32x32 64x64" href="images/ico/favicon.ico">
        <link rel="icon" type="image/png" sizes="196x196" href="images/ico/favicon-196.png">
        <link rel="icon" type="image/png" sizes="160x160" href="images/ico/favicon-160.png">
        <link rel="icon" type="image/png" sizes="96x96" href="images/ico/favicon-96.png">
        <link rel="icon" type="image/png" sizes="64x64" href="images/ico/favicon-64.png">
        <link rel="icon" type="image/png" sizes="32x32" href="images/ico/favicon-32.png">
        <link rel="icon" type="image/png" sizes="16x16" href="images/ico/favicon-16.png">
        <link rel="apple-touch-icon" sizes="152x152" href="images/ico/favicon-152.png">
        <link rel="apple-touch-icon" sizes="144x144" href="images/ico/favicon-144.png">
        <link rel="apple-touch-icon" sizes="120x120" href="images/ico/favicon-120.png">
        <link rel="apple-touch-icon" sizes="114x114" href="images/ico/favicon-114.png">
        <link rel="apple-touch-icon" sizes="76x76" href="images/ico/favicon-76.png">
        <link rel="apple-touch-icon" sizes="72x72" href="images/ico/favicon-72.png">
        <link rel="apple-touch-icon" href="images/ico/favicon-57.png">

        <link rel="stylesheet" type="text/css" href="css/vender.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/browser.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/lib/jquery-ui-1.10.4.custom.min.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/lib/jquery.qtip-2.2.1.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/style.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/${sickbeard.THEME_NAME}.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/print.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/country-flags.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/app.css?${sbPID}"/>
        <style>
            [ng\:cloak], [ng-cloak], [data-ng-cloak], [x-ng-cloak], .ng-cloak, .x-ng-cloak {
                display: none !important;
            }
        </style>
    </head>
    <body ng-controller="rootController" ng-cloak>
        <header header ng-cloak></header>

        <div id="SubMenu" class="hidden-print" ng-cloak></div>

        <div ng-if="pleaseSwitchBranches" class="alert alert-danger upgrade-notification hidden-print" role="alert" ng-cloak>
            <span>You're using the {{currentBranch}} branch. Please use 'master' unless specifically asked.</span>
        </div>

        <div ng-if="pleaseUpdate" class="alert alert-success upgrade-notification hidden-print" role="alert" ng-cloak>
            <span>{{updateVersion}}</span>
        </div>

        <div id="content" ui-view ng-cloak></div>

        <footer footer ng-cloak></footer>
        <script type="text/javascript" src="js/vender.min.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/jquery.cookiejar.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/jquery.form.min.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/jquery.json-2.2.min.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/jquery.selectboxes.min.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/formwizard.js?${sbPID}"></script>
        <script type="text/javascript" src="js/parsers.js?${sbPID}"></script>
        <script type="text/javascript" src="js/rootDirs.js?${sbPID}"></script>
        <script type="text/javascript" src="js/core.${('', 'min')[sickbeard.DEVELOPER]}js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/jquery.scrolltopcontrol-1.1.js?${sbPID}"></script>
        <script type="text/javascript" src="js/browser.js?${sbPID}"></script>
        <script type="text/javascript" src="js/ajaxNotifications.js?${sbPID}"></script>

        <!-- <script type="text/javascript" src="js/dependencies/angular.min.js"></script> -->
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/angular.js/1.4.8/angular.js"></script>
        <script type="text/javascript" src="js/dependencies/angular-sanitize.min.js"></script>
        <script type="text/javascript" src="js/dependencies/angular-ui-router.min.js"></script>
        <script type="text/javascript" src="js/dependencies/angular-animate.min.js"></script>
        <script type="text/javascript" src="js/dependencies/angular-aria.min.js"></script>
        <script type="text/javascript" src="js/dependencies/angular-material.min.js"></script>
        <script type="text/javascript" src="js/dependencies/angular-messages.min.js"></script>
        <script type="text/javascript" src="js/dependencies/angular-resource.min.js"></script>
        <script type="text/javascript" src="js/app.js"></script>
    </body>
</html>
