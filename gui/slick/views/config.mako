<%inherit file="/layouts/main.mako"/>
<%!
    import medusa as app
    from medusa import db
    from medusa.helpers import anon_url
    import sys
    import platform
%>
<%block name="content">
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif
<div id="config-content">
<table class="infoTable" cellspacing="1" border="0" cellpadding="0" width="100%">
    % if app_version:
    <tr><td class="infoTableHeader" style="vertical-align: top;"><i class="icon16-config-application"></i> Medusa Info:</td>
        <td class="infoTableCell">
        Branch: <a href="${anon_url('{0}/tree/{1}'.format(app.APPLICATION_URL, app.BRANCH)}">${app.BRANCH}</a><br>
        Commit: <a href="${anon_url('{0}/commit/{1}'.format(app.APPLICATION_URL, app.CUR_COMMIT_HASH)}">${app.CUR_COMMIT_HASH}</a><br>
        Version: <a href="${anon_url('{0}/releases/tag/{1}'.format(app.APPLICATION_URL, app_version)}">${app_version}</a><br>
        Database: ${cur_branch_major_db_version}.${cur_branch_minor_db_version}
        </td>
    </tr>
    % endif
    <tr><td class="infoTableHeader"><i class="icon16-config-python"></i> Python Version:</td><td class="infoTableCell">${sys.version[:120]}</td></tr>
    <tr><td class="infoTableHeader"><i class="icon16-config-ssl"></i> SSL Version:</td><td class="infoTableCell">${ssl_version}</td></tr>
    <tr><td class="infoTableHeader"><i class="icon16-config-os"></i> OS:</td><td class="infoTableCell">${platform.platform()}</td></tr>
    <tr><td class="infoTableHeader" style="vertical-align: top;"><i class="icon16-config-locale"></i> Locale:</td><td class="infoTableCell">${'.'.join([str(loc) for loc in sr_locale])}</td></tr>
    <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr class="infoTableSeperator"><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td class="infoTableHeader"><i class="icon16-config-user"></i> User:</td><td class="infoTableCell">${sr_user}</td></tr>
    <tr><td class="infoTableHeader"><i class="icon16-config-dir"></i> Program Folder:</td><td class="infoTableCell">${app.PROG_DIR}</td></tr>
    <tr><td class="infoTableHeader"><i class="icon16-config-config"></i> Config File:</td><td class="infoTableCell">${app.CONFIG_FILE}</td></tr>
    <tr><td class="infoTableHeader"><i class="icon16-config-db"></i> Database File:</td><td class="infoTableCell">${db.dbFilename()}</td></tr>
    <tr><td class="infoTableHeader"><i class="icon16-config-cache"></i> Cache Folder:</td><td class="infoTableCell">${app.CACHE_DIR}</td></tr>
    <tr><td class="infoTableHeader"><i class="icon16-config-log"></i> Log Folder:</td><td class="infoTableCell">${app.LOG_DIR}</td></tr>
    % if app.MY_ARGS:
    <tr><td class="infoTableHeader"><i class="icon16-config-arguments"></i> Arguments:</td><td class="infoTableCell">${app.MY_ARGS}</td></tr>
    % endif
    % if app.WEB_ROOT:
    <tr><td class="infoTableHeader"><i class="icon16-config-folder"></i> Web Root:</td><td class="infoTableCell">${app.WEB_ROOT}</td></tr>
    % endif
    <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr class="infoTableSeperator"><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td class="infoTableHeader"><i class="icon16-config-web"></i> Website:</td><td class="infoTableCell"><a href="${anon_url(app.GITHUB_IO_URL)}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false;">${app.GITHUB_IO_URL}</a></td></tr>
    <tr><td class="infoTableHeader"><i class="icon16-config-wiki"></i> Wiki:</td><td class="infoTableCell"><a href="${anon_url(app.WIKI_URL)}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false;">${app.WIKI_URL}</a></td></tr>
    <tr><td class="infoTableHeader"><i class="icon16-config-github"></i> Source:</td><td class="infoTableCell"><a href="${anon_url(app.APPLICATION_URL)}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false;">${app.APPLICATION_URL}</a></td></tr>
    <tr><td class="infoTableHeader"><i class="icon16-config-mirc"></i> IRC Chat:</td><td class="infoTableCell"><a href="irc://irc.freenode.net/#pymedusa" rel="noreferrer"><i>#pymedusa</i> on <i>irc.freenode.net</i></a></td></tr>
</table>
</div>
</%block>
