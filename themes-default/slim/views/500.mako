<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    metaInfo: {
        title: '500'
    },
    data() {
        return {
            header: 'Mako Error'
        };
    }
});
</script>
</%block>
<%block name="content">
<h1 class="header">{{header}}</h1>
<p>
A mako error has occurred.<br>
If this happened during an update a simple page refresh may be the solution.<br>
Mako errors that happen during updates may be a one-time error if there were significant ui changes.<br>
</p>
<hr>
<app-link href="#mako-error" class="btn-medusa btn-default" data-toggle="collapse">Show/Hide Error</app-link>
<div id="mako-error" class="collapse">
<br>
<div class="align-center">
<pre>
<% filename, lineno, function, line = backtrace.traceback[-1] %>
File ${filename|h}:${lineno|h}, in ${function|h}:
% if line:
${line|h}
% endif
${str(backtrace.error.__class__.__name__)|h}: ${backtrace.error|h}
</pre>
</div>
</div>
</%block>
