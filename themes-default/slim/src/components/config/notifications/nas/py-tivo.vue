<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-pytivo" title="pyTivo"></span>
            <h3><app-link href="http://pytivo.sourceforge.net/wiki/index.php/PyTivo">pyTivo</app-link></h3>
            <p>pyTivo is both an HMO and GoBack server. This notifier will load the completed downloads to your Tivo.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_pytivo" :explanations="['Send Plex Home Theater notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-pytivo">
                    <config-textbox v-model="host" label="pyTivo IP:Port" id="pytivo_host" :explanations="['host running pyTivo (eg. 192.168.1.1:9032)']" @change="save()"/>
                    <config-textbox v-model="shareName" label="pyTivo share name" id="pytivo_name" :explanations="['(Messages \& Settings > Account \& System Information > System Information > DVR name)']" @change="save()"/>
                    <config-textbox v-model="name" label="Tivo name" id="pytivo_tivo_name" :explanations="['value used in pyTivo Web Configuration to name the share.']" @change="save()"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'py-tivo',
    data: () => ({
        enabled: null,
        host: null,
        name: null,
        shareName: null
    }),
    methods: {
        save() {
            this.$emit('update', this.$data);
        },
        test() {
        }
    }
}
</script>

<style>

</style>
