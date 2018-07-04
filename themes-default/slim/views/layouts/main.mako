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
        <meta name="theme-color" content="#333333">
        % elif app.THEME_NAME == "light":
        <meta name="theme-color" content="#333333">
        % endif
        <title>Medusa${(' - ' + title) if title != 'FixME' else ''}</title>
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
        <link rel="stylesheet" type="text/css" href="css/vender.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/bootstrap-formhelpers.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/browser.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/lib/jquery-ui-1.10.4.custom.min.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/lib/jquery.qtip-2.2.1.min.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/style.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/themed.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/print.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/country-flags.css?${sbPID}"/>
        <link rel="stylesheet" type="text/css" href="css/lib/vue-snotify-material.css?${sbPID}"/>
        <%block name="css" />
    </head>
    <body ${('data-controller="' + controller + '" data-action="' + action + '" api-key="' + app.API_KEY +'"  api-root="' + app.WEB_ROOT + '/api/v2/"', '')[title == 'Login']}>
        <div v-cloak id="vue-wrap" class="container-fluid">

            <!-- These are placeholders used by the displayShow template. As they transform to full width divs, they need to be located outside the template. -->
            <div id="summaryBackground" class="shadow" style="display: none"></div>
            <div id="checkboxControlsBackground" class="shadow" style="display: none"></div>

            <%include file="/partials/header.mako"/>
            % if submenu:
            <%include file="/partials/submenu.mako"/>
            % endif
            <%include file="/partials/alerts.mako"/>
               <div id="content-row" class="row">
                    <div id="content-col" class="${'col-lg-10 col-lg-offset-1 col-md-10 col-md-offset-1' if not app.LAYOUT_WIDE else 'col-lg-12 col-md-12'} col-sm-12 col-xs-12">
                        <%block name="content" />
                    </div>
               </div><!-- /content -->
            <%include file="/partials/footer.mako" />
        </div>
        <script type="text/javascript" src="js/vender${('.min', '')[app.DEVELOPER]}.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/bootstrap-formhelpers.min.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/fix-broken-ie.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/formwizard.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/axios.min.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/lazyload.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/date_fns.min.js?${sbPID}"></script>

        <script type="text/javascript" src="js/parsers.js?${sbPID}"></script>
        <script type="text/javascript" src="js/api.js?${sbPID}"></script>
        <script type="text/javascript" src="js/core.js?${sbPID}"></script>

        <script type="text/javascript" src="js/config/index.js?${sbPID}"></script>
        <script type="text/javascript" src="js/config/init.js?${sbPID}"></script>
        <script type="text/javascript" src="js/config/notifications.js?${sbPID}"></script>

        <script type="text/javascript" src="js/add-shows/init.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/popular-shows.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/recommended-shows.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/trending-shows.js?${sbPID}"></script>

        <script type="text/javascript" src="js/common/init.js?${sbPID}"></script>

        <script type="text/javascript" src="js/home/display-show.js?${sbPID}"></script>
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
        <script type="text/javascript" src="js/manage/subtitle-missed.js?${sbPID}"></script>
        <script type="text/javascript" src="js/manage/subtitle-missed-post-process.js?${sbPID}"></script>
        <script type="text/javascript" src="js/manage/manage-searches.js?${sbPID}"></script>

        <script type="text/javascript" src="js/browser.js?${sbPID}"></script>

        <%
            ## Add Vue component x-templates here
            ## @NOTE: These will be usable on all pages
        %>
        <script src="js/lib/vue.js"></script>
        <script src="js/lib/http-vue-loader.js"></script>
        <script src="js/lib/vue-async-computed@3.3.0.js"></script>
        <script src="js/lib/vue-in-viewport-mixin.min.js"></script>
        <script src="js/lib/vue-router.min.js"></script>
        <script src="js/lib/vue-meta.min.js"></script>
        <script src="js/lib/vue-snotify.min.js"></script>
        <script src="js/lib/vue-js-toggle-button.js"></script>
        <script src="js/lib/puex.js"></script>
        <script src="js/lib/vue-native-websocket-2.0.7.js"></script>
        <script src="js/notifications.js"></script>
        <script src="js/store.js"></script>
        <%include file="/vue-components/app-link.mako"/>
        <%include file="/vue-components/asset.mako"/>
        <%include file="/vue-components/file-browser.mako"/>
        <%include file="/vue-components/plot-info.mako"/>
        <%include file="/vue-components/quality-chooser.mako"/>
        <%include file="/vue-components/language-select.mako"/>
        <%include file="/vue-components/root-dirs.mako"/>
        <%include file="/vue-components/backstretch.mako"/>
        <script>
            // @TODO: Move all Vue.use to new file
            Vue.use(window['vue-js-toggle-button'].default);

            Vue.mixin({
                created() {
                    if (this.$root === this) {
                        this.$options.sockets.onmessage = messageEvent => {
                            const { store } = window;
                            const message = JSON.parse(messageEvent.data);
                            const { data, event } = message;

                            // Show the notification to the user
                            if (event === 'notification') {
                                const { body, hash, type, title } = data;
                                displayNotification(type, title, body, hash);
                            } else if (event === 'configUpdated') {
                                store.dispatch('updateConfig', data);
                            } else {
                                displayNotification('info', event, data);
                            }
                        };
                    }
                }
            });

            // @TODO: Remove this before v1.0.0
            Vue.mixin({
                mounted() {
                    if (this.$root === this && !document.location.pathname.endsWith('/login/')) {
                        // We wait 1000ms to allow the mutations to show in vue dev-tools
                        // Please see https://github.com/egoist/puex/issues/8
                        setTimeout(() => {
                            const { store } = window;
                            store.dispatch('login');
                            store.dispatch('getConfig');
                        }, 1000);
                    }
                },
                // Make auth and config accessible to all components
                computed: store.mapState(['auth', 'config'])
            })
            window.routes = [];
            if ('${bool(app.DEVELOPER)}' === 'True') {
                Vue.config.devtools = true;
                Vue.config.performance = true;
            }
        </script>
        <%block name="scripts" />
        <script src="js/router.js"></script>
        <script>
            if (!window.app) {
                console.info('Loading Vue with router since window.app is missing.');
                window.app = new Vue({
                    el: '#vue-wrap',
                    router: window.router
                });
            } else {
                console.info('Loading local Vue since we found a window.app');
            }
        </script>
    </body>
</html>
