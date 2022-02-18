<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
    <script src="js/app.js?${sbPID}"></script>
</%block>
<%block name="load_main_app">
    <script>
        window.loadMainApp = true;
    </script>
</%block>
<%block name="content">
<!-- Load App.vue -->
<app></app>
</%block>
