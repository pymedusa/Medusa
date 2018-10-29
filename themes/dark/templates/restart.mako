<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
%>
<%block name="scripts">
<script>
const { mapState } = window.Vuex;

window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    data() {
        return {
            status: '',
            defaultPage: '${sbDefaultPage}',
            currentPid: '${sbPID}'
        };
    },
    // @TODO: Replace with Object spread (`...mapState`)
    computed: Object.assign(mapState(['config']), {
        restartState() {
            const { status } = this;
            if (status !== 'restarted') {
                return 'loading';
            }
            if (status === 'restarted') {
                return 'yes';
            }
            if (status === 'failed') {
                return 'no';
            }
        }
    }),
    mounted() {
        const { defaultPage, currentPid } = this;
        const { apiRoute } = window;
        const checkIsAlive = setInterval(() => {
            // @TODO: Move to API
            apiRoute.get('home/is_alive/').then(({ data }) => {
                const { pid } = data;
                if (!pid) {
                    // If it's still initializing then just wait and try again
                    this.status = 'initializing';
                } else if (!currentPid || currentPid === pid) {
                    this.status = 'shutting_down';
                    this.currentPid = pid;
                } else {
                    clearInterval(checkIsAlive);
                    this.status = 'restarted';
                    setTimeout(() => {
                        window.location = defaultPage + '/';
                    }, 5000);
                }
            });
        }, 1000);
    }
});
</script>
</%block>
<%block name="css">
<style>
.upgrade-notification {
    display: none;
}
</style>
</%block>
<%block name="content">
<h2>{{ $route.meta.header }}</h2>
<div>
    <div id="shut_down_message">
        Waiting for Medusa to shut down:
        <state-switch :theme="config.themeName" :state="status === 'shutting_down' ? 'loading' : 'yes'"></state-switch>
    </div>
    <div id="restart_message" v-if="status === 'initializing' || status === 'restarted'">
        Waiting for Medusa to start again:
        <state-switch v-if="restartState" :theme="config.themeName" :state="restartState"></state-switch>
    </div>
    <div id="refresh_message" v-if="status === 'restarted'">
        Loading the default page: <state-switch :theme="config.themeName" state="loading"></state-switch>
    </div>
    <div id="restart_fail_message" v-if="status === 'failed'">
        Error: The restart has timed out, perhaps something prevented Medusa from starting again?
    </div>
</div>
</%block>
