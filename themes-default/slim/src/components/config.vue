<template>
    <div id="config-content">
        <table class="infoTable" cellspacing="1" border="0" cellpadding="0" width="100%">
            <tr>
                <td><i class="icon16-config-application" /> Medusa Info:</td>
                <td>
                    Branch:
                    <span v-if="system.branch"><app-link :href="`${config.sourceUrl}/tree/${system.branch}`">{{system.branch}}</app-link></span>
                    <span v-else>Unknown</span>
                    <br>
                    Commit:
                    <span v-if="system.commitHash"><app-link :href="`${config.sourceUrl}/commit/${system.commitHash}`">{{system.commitHash}}</app-link></span>
                    <span v-else>Unknown</span>
                    <br>
                    Version:
                    <span v-if="system.release"><app-link :href="`${config.sourceUrl}/releases/tag/v${system.release}`">{{system.release}}</app-link></span>
                    <span v-else>Unknown</span>
                    <br>
                    Database:
                    <span v-if="system.databaseVersion">{{system.databaseVersion.major}}.{{system.databaseVersion.minor}}</span>
                    <span v-else>Unknown</span>
                </td>
            </tr>
            <tr><td><i class="icon16-config-python" /> Python Version:</td><td>{{system.pythonVersion}}</td></tr>
            <tr><td><i class="icon16-config-ssl" /> SSL Version:</td><td>{{system.sslVersion}}</td></tr>
            <tr><td><i class="icon16-config-os" /> OS:</td><td>{{system.os}}</td></tr>
            <tr><td><i class="icon16-config-locale" /> Locale:</td><td>{{system.locale}}</td></tr>
            <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
            <tr class="infoTableSeperator"><td>&nbsp;</td><td>&nbsp;</td></tr>
            <tr><td><i class="icon16-config-user" /> User:</td><td>{{system.localUser}}</td></tr>
            <tr><td><i class="icon16-config-dir" /> Program Folder:</td><td>{{system.programDir}}</td></tr>
            <tr><td><i class="icon16-config-config" /> Config File:</td><td>{{system.configFile}}</td></tr>
            <tr><td><i class="icon16-config-db" /> Database File:</td><td>{{system.dbPath}}</td></tr>
            <tr><td><i class="icon16-config-cache" /> Cache Folder:</td><td>{{system.cacheDir}}</td></tr>
            <tr><td><i class="icon16-config-log" /> Log Folder:</td><td>{{system.logDir}}</td></tr>
            <tr v-if="system.appArgs"><td><i class="icon16-config-arguments" /> Arguments:</td><td><pre>{{system.appArgs.join(' ')}}</pre></td></tr>
            <tr v-if="system.webRoot"><td><i class="icon16-config-dir" /> Web Root:</td><td>{{system.webRoot}}</td></tr>
            <tr v-if="system.runsInDocker"><td><i class="icon16-config-docker" /> Runs in Docker:</td><td>Yes</td></tr>
            <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
            <tr class="infoTableSeperator"><td>&nbsp;</td><td>&nbsp;</td></tr>
            <tr><td><i class="icon16-config-web" /> Website:</td><td><app-link :href="config.git.url">{{config.git.url}}</app-link></td></tr>
            <tr><td><i class="icon16-config-wiki" /> Wiki:</td><td><app-link :href="config.wikiUrl">{{config.wikiUrl}}</app-link></td></tr>
            <tr><td><i class="icon16-config-github" /> Source:</td><td><app-link :href="config.sourceUrl">{{config.sourceUrl}}</app-link></td></tr>
            <tr><td><i class="icon16-config-mirc" /> IRC Chat:</td><td><app-link href="irc://irc.freenode.net/#pymedusa"><i>#pymedusa</i> on <i>irc.freenode.net</i></app-link></td></tr>
        </table>
    </div>
</template>
<script>
import { mapState } from 'vuex';
import { AppLink } from './helpers';

export default {
    name: 'config',
    components: {
        AppLink
    },
    computed: mapState({
        config: state => state.config.general,
        system: state => state.config.system
    })
};
</script>
<style scoped>
.infoTable tr td:first-child {
    vertical-align: top;
}

pre {
    padding: 5px;
}
</style>
