<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        data() {
            return {};
        }
    });
};
</script>
</%block>
<%block name="content">
<%
from medusa import app
username = ("MedusaUI|?", app.GIT_USERNAME)[bool(app.GIT_USERNAME)]
%>
<iframe id="extFrame" src="https://kiwiirc.com/client/irc.freenode.net/?nick=${username}&theme=basic#pymedusa" width="100%" height="500" frameBorder="0" style="border: 1px rgb(0, 0, 0) solid;"></iframe>
</%block>
