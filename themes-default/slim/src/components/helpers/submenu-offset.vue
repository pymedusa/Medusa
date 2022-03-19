<template>
    <div v-if="$route.meta.subMenu" class="submenu-offset" />
</template>

<script>
export default {
    name: 'submenu-offset'
};
</script>

<style scoped>
    .submenu-offset {
        margin-top: 45px;
    }
</style>
