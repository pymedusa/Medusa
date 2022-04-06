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
        <link rel="stylesheet" type="text/css" href="css/print.css?${sbPID}" />
        <link rel="stylesheet" type="text/css" href="css/country-flags.css?${sbPID}"/>
        <%block name="css" />
    </head>

<body web-root="${app.WEB_ROOT}" developer="${app.DEVELOPER}">
    <div id="app-wrapper" class="container-fluid"></div>

    ## These contain all the Webpack-imported modules
    ## When adding/removing JS files, don't forget to update `apiBuilder.mako`
    <script type="text/javascript" src="js/vendors.js?${sbPID}"></script>
    <script type="text/javascript" src="js/vendors~date-fns.js?${sbPID}"></script>
    <script type="text/javascript" src="js/medusa-runtime.js?${sbPID}"></script>

    <script type="text/javascript" src="js/index.js?${sbPID}"></script>

    <script type="text/javascript" src="js/vender${('.min', '')[app.DEVELOPER]}.js?${sbPID}"></script>

    <!-- bfhlanguages used in language-select.vue -->
    <script type="text/javascript" src="js/lib/bootstrap-formhelpers.min.js?${sbPID}"></script>

    <!-- Used by components root-dirs.vue -->
    <script type="text/javascript" src="js/browser.js?${sbPID}"></script>

    <!-- Used by store/index -->
    <script type="text/javascript" src="js/notifications.js?${sbPID}"></script>

    <script src="js/app.js?${sbPID}"></script>
</body>
</html>
