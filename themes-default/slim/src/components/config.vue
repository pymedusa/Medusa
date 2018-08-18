<template>
    <div id="config-content">
        <table class="infoTable" cellspacing="1" border="0" cellpadding="0" width="100%">
            <tr>
                <td><i class="icon16-config-application"></i> Medusa Info:</td>
                <td>
                    Branch:
                    <span v-if="config.branch"><app-link :href="config.sourceUrl + '/tree/' + config.branch">{{config.branch}}</app-link></span>
                    <span v-else>Unknown</span>
                    <br>
                    Commit:
                    <span v-if="config.commitHash"><app-link :href="config.sourceUrl + '/commit/' + config.commitHash">{{config.commitHash}}</app-link></span>
                    <span v-else>Unknown</span>
                    <br>
                    Version:
                    <span v-if="config.release"><app-link :href="config.sourceUrl + '/releases/tag/' + config.release">{{config.release}}</app-link></span>
                    <span v-else>Unknown</span>
                    <br>
                    Database:
                    <span v-if="config.databaseVersion">{{config.databaseVersion.major}}.{{config.databaseVersion.minor}}</span>
                    <span v-else>Unknown</span>
                </td>
            </tr>
            <tr><td><i class="icon16-config-python"></i> Python Version:</td><td>{{config.pythonVersion}}</td></tr>
            <tr><td><i class="icon16-config-ssl"></i> SSL Version:</td><td>{{config.sslVersion}}</td></tr>
            <tr><td><i class="icon16-config-os"></i> OS:</td><td>{{config.os}}</td></tr>
            <tr><td><i class="icon16-config-locale"></i> Locale:</td><td>{{config.locale}}</td></tr>
            <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
            <tr class="infoTableSeperator"><td>&nbsp;</td><td>&nbsp;</td></tr>
            <tr><td><i class="icon16-config-user"></i> User:</td><td>{{config.localUser}}</td></tr>
            <tr><td><i class="icon16-config-dir"></i> Program Folder:</td><td>{{config.programDir}}</td></tr>
            <tr><td><i class="icon16-config-config"></i> Config File:</td><td>{{config.configFile}}</td></tr>
            <tr><td><i class="icon16-config-db"></i> Database File:</td><td>{{config.dbPath}}</td></tr>
            <tr><td><i class="icon16-config-cache"></i> Cache Folder:</td><td>{{config.cacheDir}}</td></tr>
            <tr><td><i class="icon16-config-log"></i> Log Folder:</td><td>{{config.logDir}}</td></tr>
            <tr v-if="config.appArgs"><td><i class="icon16-config-arguments"></i> Arguments:</td><td><pre>{{prettyPrintJSON(config.appArgs)}}</pre></td></tr>
            <tr v-if="config.webRoot"><td><i class="icon16-config-folder"></i> Web Root:</td><td>{{config.webRoot}}</td></tr>
            <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
            <tr class="infoTableSeperator"><td>&nbsp;</td><td>&nbsp;</td></tr>
            <tr><td><i class="icon16-config-web"></i> Website:</td><td><app-link :href="config.githubUrl">{{config.githubUrl}}</app-link></td></tr>
            <tr><td><i class="icon16-config-wiki"></i> Wiki:</td><td><app-link :href="config.wikiUrl">{{config.wikiUrl}}</app-link></td></tr>
            <tr><td><i class="icon16-config-github"></i> Source:</td><td><app-link :href="config.sourceUrl">{{config.sourceUrl}}</app-link></td></tr>
            <tr><td><i class="icon16-config-mirc"></i> IRC Chat:</td><td><app-link href="irc://irc.freenode.net/#pymedusa"><i>#pymedusa</i> on <i>irc.freenode.net</i></app-link></td></tr>
        </table>
    </div>
</template>
<script>
import AppLink from './app-link.vue';

module.exports = {
    name: 'config',
    components: {
        AppLink
    },
    computed: {
        config() {
            return this.$store.state.config;
        }
    },
    methods: {
        prettyPrintJSON: str => JSON.stringify(str, undefined, 4)
    }
};
</script>
<style>
.infoTable tr td:first-child {
    vertical-align: top;
}
</style>
