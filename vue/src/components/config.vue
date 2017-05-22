<template>
    <div>
        <h1 class="header">Medusa Configuration</h1>
        <div id="config-content">
            <!-- This is the config page, all config/* will load within the router-view below. -->
            <router-view></router-view>
        </div>
    </div>
</template>
<script>
export default {
    name: 'config'
};
</script>
