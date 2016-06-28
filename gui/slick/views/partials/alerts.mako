<%!
    from sickbeard import BRANCH, DEVELOPER, NEWEST_VERSION_STRING
%>
<!-- BEGIN ALERTS -->
% if BRANCH and BRANCH != 'master' and not DEVELOPER and loggedIn:
<div class="alert alert-danger upgrade-notification hidden-print" role="alert">
    <span>You're using the ${BRANCH} branch. Please use 'master' unless specifically asked</span>
</div>
% endif
% if NEWEST_VERSION_STRING and loggedIn:
<div class="alert alert-success upgrade-notification hidden-print" role="alert">
    <span>${NEWEST_VERSION_STRING}</span>
</div>
% endif
<!-- END ALERTS -->
