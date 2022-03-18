<template>
    <div v-if="system.branch !== null" id="alerts">
        <!-- BEGIN ALERTS -->
        <div v-if="system.branch !== 'master' && !developer" class="text-center">
            <div class="alert alert-danger upgrade-notification hidden-print" role="alert">
                <span>You're using the {{system.branch}} branch. Please use 'master' unless specifically asked</span>
            </div>
        </div>

        <div v-if="system.newestVersionMessage" class="text-center">
            <div class="alert alert-success upgrade-notification hidden-print" role="alert">
                <span v-html="system.newestVersionMessage" />
            </div>
        </div>
    </div>
</template>

<script>
import { mapState } from 'vuex';
export default {
    name: 'alerts',
    computed: {
        ...mapState({
            system: state => state.config.system,
            developer: state => state.config.general.developer
        })
    }
};
</script>

<style>
</style>
