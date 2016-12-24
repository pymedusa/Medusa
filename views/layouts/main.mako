<%!
    from medusa import app
%>
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <meta name="robots" content="noindex, nofollow">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <!-- These values come from css/dark.css and css/light.css -->
        % if app.THEME_NAME == "dark":
        <meta name="theme-color" content="#15528F">
        % elif app.THEME_NAME == "light":
        <meta name="theme-color" content="#333333">
        % endif
        <title>Medusa - ${title}</title>
        <base href="${base_url}">
        <%block name="metas" />
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
        <style>
        [v-cloak] {
            display: none !important;
        }
        </style>
        <link rel="stylesheet" type="text/css" href="css/vender.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/browser.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/lib/jquery-ui-1.10.4.custom.min.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/lib/jquery.qtip-2.2.1.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/style.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/${app.THEME_NAME}.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/print.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/country-flags.css?${sbPID}"/>
        <%block name="css" />
    </head>
    <body ${('data-controller="' + controller + '" data-action="' + action + '" api-key="' + app.API_KEY +'"  api-root="api/v2/"', '')[title == 'Login']}>
        <div v-cloak id="vue-wrap" class="container-fluid">
            <%include file="/partials/header.mako"/>
            % if submenu:
            <%include file="/partials/submenu.mako"/>
            % endif
            <%include file="/partials/alerts.mako"/>
               <div id="content-row" class="row">
                    <div id="content-col" class="col-lg-10 col-lg-offset-1 col-md-10 col-md-offset-1 col-sm-12 col-xs-12">
                        <%block name="content" />
                    </div>
               </div><!-- /content -->
            <%include file="/partials/footer.mako" />
        </div>
        <script type="text/javascript" src="js/vender${('.min', '')[app.DEVELOPER]}.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/fix-broken-ie.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/jquery.cookiejar.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/jquery.form.min.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/jquery.json-2.2.min.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/jquery.selectboxes.min.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/formwizard.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/timeago.js?${sbPID}"></script>
        <script type="text/javascript" src="js/parsers.js?${sbPID}"></script>
        <script type="text/javascript" src="js/root-dirs.js?${sbPID}"></script>
        <script type="text/javascript" src="js/core.js?${sbPID}"></script>

        <script type="text/javascript" src="js/config/backup-restore.js?${sbPID}"></script>
        <script type="text/javascript" src="js/config/index.js?${sbPID}"></script>
        <script type="text/javascript" src="js/config/init.js?${sbPID}"></script>
        <script type="text/javascript" src="js/config/notifications.js?${sbPID}"></script>
        <script type="text/javascript" src="js/config/post-processing.js?${sbPID}"></script>
        <script type="text/javascript" src="js/config/search.js?${sbPID}"></script>
        <script type="text/javascript" src="js/config/subtitles.js?${sbPID}"></script>

        <script type="text/javascript" src="js/add-shows/add-existing-show.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/init.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/new-show.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/popular-shows.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/recommended-shows.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/trending-shows.js?${sbPID}"></script>

        <script type="text/javascript" src="js/schedule/index.js?${sbPID}"></script>

        <script type="text/javascript" src="js/common/init.js?${sbPID}"></script>

        <script type="text/javascript" src="js/home/display-show.js?${sbPID}"></script>
        <script type="text/javascript" src="js/home/edit-show.js?${sbPID}"></script>
        <script type="text/javascript" src="js/home/index.js?${sbPID}"></script>
        <script type="text/javascript" src="js/home/post-process.js?${sbPID}"></script>
        <script type="text/javascript" src="js/home/restart.js?${sbPID}"></script>
        <script type="text/javascript" src="js/home/snatch-selection.js?${sbPID}"></script>
        <script type="text/javascript" src="js/home/status.js?${sbPID}"></script>

        <script type="text/javascript" src="js/manage/backlog-overview.js?${sbPID}"></script>
        <script type="text/javascript" src="js/manage/episode-statuses.js?${sbPID}"></script>
        <script type="text/javascript" src="js/manage/failed-downloads.js?${sbPID}"></script>
        <script type="text/javascript" src="js/manage/index.js?${sbPID}"></script>
        <script type="text/javascript" src="js/manage/init.js?${sbPID}"></script>
        <script type="text/javascript" src="js/manage/mass-edit.js?${sbPID}"></script>
        <script type="text/javascript" src="js/manage/subtitle-missed.js?${sbPID}"></script>
        <script type="text/javascript" src="js/manage/subtitle-missed-post-process.js?${sbPID}"></script>
        <script type="text/javascript" src="js/history/index.js?${sbPID}"></script>

        <script type="text/javascript" src="js/errorlogs/viewlogs.js?${sbPID}"></script>

        <script type="text/javascript" src="js/lib/jquery.scrolltopcontrol-1.1.js?${sbPID}"></script>
        <script type="text/javascript" src="js/browser.js?${sbPID}"></script>
        <script type="text/javascript" src="js/ajax-notifications.js?${sbPID}"></script>
        <%block name="scripts" />
    </body>
</html>
