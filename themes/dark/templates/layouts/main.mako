<%!
    import json

    from medusa import app
%>
<!DOCTYPE html>
<html>

<head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex, nofollow">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#333333">
    <title>Medusa${(' - ' + title) if title and title != 'FixME' else ''}</title>
    <base href="${base_url}">
    <%block name="metas" />
        <link rel="shortcut icon" href="images/ico/favicon.ico?v=2">
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

        ## Webpack-imported CSS files
        <link rel="stylesheet" type="text/css" href="css/vendors.css?${sbPID}"/>

        <link rel="stylesheet" type="text/css" href="css/vender.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/bootstrap-formhelpers.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/browser.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/lib/jquery-ui-1.10.4.custom.min.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/lib/jquery.qtip-2.2.1.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/style.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/themed.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/themed.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/print.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/country-flags.css?${sbPID}"/>
        <%block name="css" />
    </head>
    <% attributes = 'data-controller="' + controller + '" data-action="' + action + '" api-key="' + app.API_KEY + '"' %>

<body ${('', attributes)[bool(loggedIn)]} web-root="${app.WEB_ROOT}">
    <div id="vue-wrap" class="container-fluid">
        <load-progress-bar v-if="showsLoading" v-bind="{display: showsLoading.display, current: showsLoading.current, total: showsLoading.total}"></load-progress-bar>

        <div v-if="globalLoading" class="text-center">
            <h3>Loading&hellip;</h3>
            If this is taking too long,<br>
            <i style="cursor: pointer;" @click="globalLoading = false;">click here</i> to show the page.
        </div>

        <div v-cloak :style="globalLoading ? { opacity: '0 !important' } : undefined">
            <app-header></app-header>
            <sub-menu></sub-menu>

            <%include file="/partials/alerts.mako"/>

            <div id="content-row" class="row">
                <component :is="pageComponent || 'div'" id="content-col" class="${'col-lg-10 col-lg-offset-1 col-md-10 col-md-offset-1' if not app.LAYOUT_WIDE else 'col-lg-12 col-md-12'} col-sm-12 col-xs-12">
                    <%block name="content" />
                </component>
            </div><!-- /content -->

            <app-footer v-if="$store.state.auth.isAuthenticated"></app-footer>
            <scroll-buttons></scroll-buttons>

          </div><!-- /globalLoading wrapper -->

        </div>
        <%block name="load_main_app" />

        ## These contain all the Webpack-imported modules
        ## When adding/removing JS files, don't forget to update `apiBuilder.mako`
        <script type="text/javascript" src="js/vendors.js?${sbPID}"></script>
        <script type="text/javascript" src="js/vendors~date-fns.js?${sbPID}"></script>
        <script type="text/javascript" src="js/medusa-runtime.js?${sbPID}"></script>

        <script type="text/javascript" src="js/index.js?${sbPID}"></script>

        <script type="text/javascript" src="js/vender${('.min', '')[app.DEVELOPER]}.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/bootstrap-formhelpers.min.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/formwizard.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/lazyload.js?${sbPID}"></script>

        <script type="text/javascript" src="js/parsers.js?${sbPID}"></script>

        <script type="text/javascript" src="js/config/init.js?${sbPID}"></script>

        <script type="text/javascript" src="js/add-shows/init.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/popular-shows.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/recommended-shows.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/trending-shows.js?${sbPID}"></script>

        <script type="text/javascript" src="js/common/init.js?${sbPID}"></script>

        <script type="text/javascript" src="js/browser.js?${sbPID}"></script>

        <script type="text/javascript" src="js/notifications.js?${sbPID}"></script>

        <!-- Moved to main, as I can't add it to display-show.vue, because vue templates don't allow script tags. -->
        <!-- <script type="text/javascript" src="js/ajax-episode-search.js?${sbPID}"></script> -->
        <!-- <script type="text/javascript" src="js/ajax-episode-subtitles.js?${sbPID}"></script> -->
        <script>
            // Used to get username to the app.js and header
            % if app.WEB_USERNAME and app.WEB_PASSWORD and '/login' not in full_url:
            window.username = ${json.dumps(app.WEB_USERNAME)};
            % else:
            window.username = '';
            % endif

            // [Temporary] Used by the QualityChooser component on some pages
            % if show is not UNDEFINED:
                window.qualityChooserInitialQuality = ${int(show.quality)};
            % endif

            if ('${bool(app.DEVELOPER)}' === 'True') {
                Vue.config.devtools = true;
                Vue.config.performance = true;
            }
        </script>
        ## Include Vue components using x-templates here
        <script>
            // @TODO: Remove this before v1.0.0
            if (!window.loadMainApp && window.globalVueShim) {
                window.globalVueShim();
            }
        </script>
        <%block name="scripts" />
    </body>
</html>
