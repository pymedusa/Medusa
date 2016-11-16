<%inherit file="/layouts/main.mako"/>
<%block name="content">
<h1 class="header">Medusa Configuration</h1>
<div id="config-content">
    <table class="infoTable" cellspacing="1" border="0" cellpadding="0" width="100%">
        <tr v-if="release">
            <td><i class="icon16-config-application"></i> Medusa Info:</td>
            <td>
                Branch: <a v-bind:href="sourceUrl + '/tree/' + branch" v-on:click="anonRedirect">{{branch}}</a><br>
                Commit: <a v-bind:href="sourceUrl + '/commit/' + commitHash" v-on:click="anonRedirect">{{commitHash}}</a><br>
                Version: <a v-bind:href="sourceUrl + 'releases/tag/' + release" v-on:click="anonRedirect">{{release}}</a><br>
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
        <tr v-if="appArgs.length"><td><i class="icon16-config-arguments"></i> Arguments:</td><td><pre style="background-color: #222222;border-color: #222222;padding: 0;border: 0;margin: 0;">{{prettyPrintJSON(appArgs)}}</pre></td></tr>
        <tr v-if="webRoot"><td><i class="icon16-config-folder"></i> Web Root:</td><td>{{webRoot}}</td></tr>
        <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
        <tr class="infoTableSeperator"><td>&nbsp;</td><td>&nbsp;</td></tr>
        <tr><td><i class="icon16-config-web"></i> Website:</td><td><a v-bind:href="githubUrl" rel="noreferrer" v-on:click="anonRedirect">{{githubUrl}}</a></td></tr>
        <tr><td><i class="icon16-config-wiki"></i> Wiki:</td><td><a v-bind:href="wikiUrl" rel="noreferrer" v-on:click="anonRedirect">{{wikiUrl}}</a></td></tr>
        <tr><td><i class="icon16-config-github"></i> Source:</td><td><a v-bind:href="sourceUrl" rel="noreferrer" v-on:click="anonRedirect">{{sourceUrl}}</a></td></tr>
        <tr><td><i class="icon16-config-mirc"></i> IRC Chat:</td><td><a href="irc://irc.freenode.net/#pymedusa" rel="noreferrer"><i>#pymedusa</i> on <i>irc.freenode.net</i></a></td></tr>
    </table>
</div>
</%block>
<%block name="scripts">
<script src="js/lib/vue.js"></script>
<script src="js/lib/axios.min.js"></script>
<script src="js/lib/lodash.min.js"></script>
<script>
var app;
var startVue = function(){
    app = new Vue({
        el: '#config-content',
        data: MEDUSA.config,
        methods: {
            anonRedirect: function(e){
                e.preventDefault();
                window.open(MEDUSA.info.anonRedirect + e.target.href, '_blank');
            },
            prettyPrintJSON: function(x){
                return JSON.stringify(x, undefined, 4)
            }
        }
    });
    $('[v-cloak]').removeAttr('v-cloak');
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
