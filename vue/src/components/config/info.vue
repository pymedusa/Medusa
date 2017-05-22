<template>
    <table class="infoTable" cellspacing="1" border="0" cellpadding="0" width="100%">
        <tr v-if="config.release">
            <td><i class="icon16-config-application"></i> Medusa Info:</td>
            <td>
                Branch: <a v-bind:href="config.sourceUrl + '/tree/' + config.branch" v-on:click="anonRedirect">{{config.branch}}</a><br>
                Commit: <a v-bind:href="config.sourceUrl + '/commit/' + config.commitHash" v-on:click="anonRedirect">{{config.commitHash}}</a><br>
                Version: <a v-bind:href="config.sourceUrl + '/releases/tag/' + config.release" v-on:click="anonRedirect">{{config.release}}</a><br>
                Database: {{config.databaseVersion.major}}.{{config.databaseVersion.minor}}
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
        <tr><td><i class="icon16-config-db"></i> Database File:</td><td>{{config.dbFilename}}</td></tr>
        <tr><td><i class="icon16-config-cache"></i> Cache Folder:</td><td>{{config.cacheDir}}</td></tr>
        <tr><td><i class="icon16-config-log"></i> Log Folder:</td><td>{{config.logDir}}</td></tr>
        <tr v-if="config.appArgs.length"><td><i class="icon16-config-arguments"></i> Arguments:</td><td><pre>{{prettyPrintJSON(config.appArgs)}}</pre></td></tr>
        <tr v-if="config.webRoot"><td><i class="icon16-config-folder"></i> Web Root:</td><td>{{config.webRoot}}</td></tr>
        <tr><td>&nbsp;</td><td>&nbsp;</td></tr>
        <tr class="infoTableSeperator"><td>&nbsp;</td><td>&nbsp;</td></tr>
        <tr><td><i class="icon16-config-web"></i> Website:</td><td><a v-bind:href="config.githubUrl" rel="noreferrer" v-on:click="anonRedirect">{{config.githubUrl}}</a></td></tr>
        <tr><td><i class="icon16-config-wiki"></i> Wiki:</td><td><a v-bind:href="config.wikiUrl" rel="noreferrer" v-on:click="anonRedirect">{{config.wikiUrl}}</a></td></tr>
        <tr><td><i class="icon16-config-github"></i> Source:</td><td><a v-bind:href="config.sourceUrl" rel="noreferrer" v-on:click="anonRedirect">{{config.sourceUrl}}</a></td></tr>
        <tr><td><i class="icon16-config-mirc"></i> IRC Chat:</td><td><a href="irc://irc.freenode.net/#pymedusa" rel="noreferrer"><i>#pymedusa</i> on <i>irc.freenode.net</i></a></td></tr>
    </table>
</template>

<script>
import {mapGetters} from 'vuex';

export default {
    name: 'info',
    computed: {
        ...mapGetters([
            'config'
        ])
    },
    methods: {
        anonRedirect(event) {
            const vm = this;
            event.preventDefault();
            window.open(vm.config.anonRedirect + event.target.href, '_blank');
        },
        prettyPrintJSON(x) {
            return JSON.stringify(x, undefined, 4);
        }
    }
};
</script>

<style>
.infoTable tr td:first-child {
  vertical-align: top;
}
</style>
