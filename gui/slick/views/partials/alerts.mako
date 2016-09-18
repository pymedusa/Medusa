<%!
    import medusa as sickbeard
%>
<!-- BEGIN ALERTS -->
% if sickbeard.BRANCH and sickbeard.BRANCH != 'master' and not sickbeard.DEVELOPER and loggedIn:
<div class="alert alert-danger upgrade-notification hidden-print" role="alert">
    <span>You're using the ${sickbeard.BRANCH} branch. Please use 'master' unless specifically asked</span>
</div>
% endif
% if sickbeard.NEWEST_VERSION_STRING and loggedIn:
<div class="alert alert-success upgrade-notification hidden-print" role="alert">
    <span>${sickbeard.NEWEST_VERSION_STRING}</span>
</div>
% endif
<!-- END ALERTS -->
