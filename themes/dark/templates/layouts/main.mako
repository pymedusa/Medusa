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
    <% attributes = 'data-controller="' + controller + '" data-action="' + action + '" api-key="' + app.API_KEY + '"' %>
    <body ${('', attributes)[bool(loggedIn)]} web-root="${app.WEB_ROOT}">
        <div v-cloak id="vue-wrap" class="container-fluid">

            <!-- These are placeholders used by the displayShow template. As they transform to full width divs, they need to be located outside the template. -->
            <div id="summaryBackground" class="shadow" style="display: none"></div>
            <div id="checkboxControlsBackground" class="shadow" style="display: none"></div>

            <app-header></app-header>
            % if submenu:
            <sub-menu></sub-menu>
            % endif
            <%include file="/partials/alerts.mako"/>
               <div id="content-row" class="row">
                    <div v-if="globalLoading" class="text-center ${'col-lg-10 col-lg-offset-1 col-md-10 col-md-offset-1' if not app.LAYOUT_WIDE else 'col-lg-12 col-md-12'} col-sm-12 col-xs-12">
                        <h3>Loading....</h3>
                        If this is taking too long,<br>
                        <i style="cursor: pointer;" @click="globalLoading = false;">click here</i> to show the page.
                    </div>
                    <component :is="pageComponent || 'div'" :style="globalLoading ? { opacity: '0 !important' } : undefined" id="content-col" class="${'col-lg-10 col-lg-offset-1 col-md-10 col-md-offset-1' if not app.LAYOUT_WIDE else 'col-lg-12 col-md-12'} col-sm-12 col-xs-12">
                        <%block name="content" />
                    </component>
               </div><!-- /content -->
            <%include file="/partials/footer.mako" />
            <scroll-buttons></scroll-buttons>
        </div>
        <%block name="load_main_app" />
        <script type="text/javascript" src="js/vender${('.min', '')[app.DEVELOPER]}.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/bootstrap-formhelpers.min.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/fix-broken-ie.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/formwizard.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/lazyload.js?${sbPID}"></script>
        <script type="text/javascript" src="js/lib/date_fns.min.js?${sbPID}"></script>

        <script type="text/javascript" src="js/parsers.js?${sbPID}"></script>

        ## This contains all the Webpack-imported modules
        <script type="text/javascript" src="js/vendors.js?${sbPID}"></script>

        <script type="text/javascript" src="js/index.js?${sbPID}"></script>

        <script type="text/javascript" src="js/config/index.js?${sbPID}"></script>
        <script type="text/javascript" src="js/config/init.js?${sbPID}"></script>
        <script type="text/javascript" src="js/config/notifications.js?${sbPID}"></script>

        <script type="text/javascript" src="js/add-shows/init.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/popular-shows.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/recommended-shows.js?${sbPID}"></script>
        <script type="text/javascript" src="js/add-shows/trending-shows.js?${sbPID}"></script>

        <script type="text/javascript" src="js/common/init.js?${sbPID}"></script>

        <script type="text/javascript" src="js/home/index.js?${sbPID}"></script>
        <script type="text/javascript" src="js/home/post-process.js?${sbPID}"></script>
        <script type="text/javascript" src="js/home/restart.js?${sbPID}"></script>
        <script type="text/javascript" src="js/home/snatch-selection.js?${sbPID}"></script>
        <script type="text/javascript" src="js/home/status.js?${sbPID}"></script>

        <script type="text/javascript" src="js/manage/failed-downloads.js?${sbPID}"></script>
        <script type="text/javascript" src="js/manage/index.js?${sbPID}"></script>
        <script type="text/javascript" src="js/manage/init.js?${sbPID}"></script>
        <script type="text/javascript" src="js/manage/subtitle-missed.js?${sbPID}"></script>

        <script type="text/javascript" src="js/browser.js?${sbPID}"></script>

        <script type="text/javascript" src="js/notifications.js?${sbPID}"></script>
        <script>
            // Used to get username to the app.js and header
            % if app.WEB_USERNAME and app.WEB_PASSWORD and '/login' not in full_url:
            window.username = ${json.dumps(app.WEB_USERNAME)};
            % else:
            window.username = '';
            % endif
        </script>
        <%include file="/vue-components/sub-menu.mako"/>
        <%include file="/vue-components/quality-chooser.mako"/>
        <script>
            // @TODO: Remove this before v1.0.0
            Vue.mixin({
                data() {
                    return {
                        globalLoading: true,
                        pageComponent: false
                    };
                },
                mounted() {
                    if (this.$root === this && !document.location.pathname.includes('/login')) {
                        const { store, username } = window;
                        /* This is used by the `app-header` component
                           to only show the logout button if a username is set */
                        store.dispatch('login', { username });
                        store.dispatch('getConfig').then(() => this.$emit('loaded'));
                    }

                    this.$once('loaded', () => {
                        this.globalLoading = false;
                    });
                },
                // Make auth and config accessible to all components
                computed: Vuex.mapState(['auth', 'config'])
            });

            window.routes = [];
            if ('${bool(app.DEVELOPER)}' === 'True') {
                Vue.config.devtools = true;
                Vue.config.performance = true;
            }
        </script>
        <script>
            if (!window.loadMainApp) {
                console.debug('Loading local Vue');
                Vue.use(Vuex);
                Vue.use(VueRouter);
                Vue.use(AsyncComputed);
                Vue.use(VueMeta);

                // Load x-template components
                window.components.forEach(component => {
                    console.log('Registering ' + component.name);
                    Vue.component(component.name, component);
                });

                // Global components
                Vue.use(ToggleButton);
                Vue.use(Snotify);
            }
        </script>
        <%block name="scripts" />
    </body>
</html>
