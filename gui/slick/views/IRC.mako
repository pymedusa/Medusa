<%inherit file="/layouts/main.mako"/>
<%block name="content">
<%
from sickbeard import GIT_USERNAME
username = ("MedusaUI|?", GIT_USERNAME)[bool(GIT_USERNAME)]
%>
<iframe id="extFrame" src="https://kiwiirc.com/client/irc.freenode.net/?nick=${username}&theme=basic#pymedusa" width="100%" height="500" frameBorder="0" style="border: 1px rgb(0, 0, 0) solid;"></iframe>
</%block>
