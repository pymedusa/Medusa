<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import classes, logger
%>
<%block name="scripts">
<script>
const { mapState } = window.Vuex;

window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    // @TODO: Replace with Object spread (`...mapState`)
    computed: Object.assign(mapState({
        loggingLevels: state => state.config.general.logs.loggingLevels
    }), {
        header() {
            const { loggingLevels, $route } = this;
            if (Number($route.query.level) === loggingLevels.warning) {
                return 'Warning Logs';
            }
            return 'Error Logs';
        }
    })
});
</script>
</%block>
<%block name="css">
<style>
pre {
    overflow: auto;
    word-wrap: normal;
    white-space: pre;
}
</style>
</%block>
<%block name="content">

<%
    from mako.filters import html_escape
    if logLevel == logger.WARNING:
        errors = classes.WarningViewer.errors
    else:
        errors = classes.ErrorViewer.errors
%>

<div class="row">
    <div class="col-md-12 wide">
        <h1 class="header">{{ header }}</h1>
    </div>
</div>

<div class="row">
<div class="col-md-12">
<pre v-pre>
% if errors:
${'\n'.join([html_escape(logline) for logline in errors[:500]])}
% else:
There are no events to display.
% endif
</pre>
</div>
</div>
</%block>
