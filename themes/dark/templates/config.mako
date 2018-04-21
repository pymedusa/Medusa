<%inherit file="/layouts/main.mako"/>
<%block name="content">
<h1 class="header">Medusa Configuration</h1>
<div id="config-content">
    <table class="infoTable" cellspacing="1" border="0" cellpadding="0" width="100%">
        <tr v-if="release">
            <td><i class="icon16-config-application"></i> Medusa Info:</td>
            <td>
                Branch: <app-link :href="sourceUrl + '/tree/' + branch">{{branch}}</app-link><br>
                Commit: <app-link :href="sourceUrl + '/commit/' + commitHash">{{commitHash}}</app-link><br>
                Version: <app-link :href="sourceUrl + '/releases/tag/' + release">{{release}}</app-link><br>
                Database: {{databaseVersion.major}}.{{databaseVersion.minor}}
            </td>
        </tr>
        <tr><td><i class="icon16-config-python"></i> Python Version:</td><td>{{pythonVersion}}</td></tr>
        <tr><td><i class="icon16-config-ssl"></i> SSL Version:</td><td>{{sslVersion}}</td></tr>
        <tr><td><i class="icon16-config-os"></i> OS:</td><td>{{os}}</td></tr>
        <tr><td><i class="icon16-config-locale"></i> Locale:</td><td>{{locale}}</td></tr>
        <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
        <tr class="infoTableSeperator"><td>&nbsp;</td><td>&nbsp;</td></tr>
        <tr><td><i class="icon16-config-user"></i> User:</td><td>{{localUser}}</td></tr>
        <tr><td><i class="icon16-config-dir"></i> Program Folder:</td><td>{{programDir}}</td></tr>
        <tr><td><i class="icon16-config-config"></i> Config File:</td><td>{{configFile}}</td></tr>
        <tr><td><i class="icon16-config-db"></i> Database File:</td><td>{{dbFilename}}</td></tr>
        <tr><td><i class="icon16-config-cache"></i> Cache Folder:</td><td>{{cacheDir}}</td></tr>
        <tr><td><i class="icon16-config-log"></i> Log Folder:</td><td>{{logDir}}</td></tr>
        <tr v-if="appArgs.length"><td><i class="icon16-config-arguments"></i> Arguments:</td><td><pre>{{prettyPrintJSON(appArgs)}}</pre></td></tr>
        <tr v-if="webRoot"><td><i class="icon16-config-folder"></i> Web Root:</td><td>{{webRoot}}</td></tr>
        <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
        <tr class="infoTableSeperator"><td>&nbsp;</td><td>&nbsp;</td></tr>
        <tr><td><i class="icon16-config-web"></i> Website:</td><td><app-link :href="githubUrl">{{githubUrl}}</app-link></td></tr>
        <tr><td><i class="icon16-config-wiki"></i> Wiki:</td><td><app-link :href="wikiUrl">{{wikiUrl}}</app-link></td></tr>
        <tr><td><i class="icon16-config-github"></i> Source:</td><td><app-link :href="sourceUrl">{{sourceUrl}}</app-link></td></tr>
        <tr><td><i class="icon16-config-mirc"></i> IRC Chat:</td><td><app-link href="irc://irc.freenode.net/#pymedusa" rel="noreferrer"><i>#pymedusa</i> on <i>irc.freenode.net</i></app-link></td></tr>
    </table>
</div>
</%block>
<%block name="scripts">
<script>
var app;
var startVue = function(){
    app = new Vue({
        el: '#vue-wrap',
        data: MEDUSA.config,
        methods: {
            prettyPrintJSON: function(x){
                return JSON.stringify(x, undefined, 4)
            }
        }
    });
};
</script>
</%block>
<%block name="css">
<style>
.infoTable tr td:first-child {
  vertical-align: top;
}
</style>
</%block>
